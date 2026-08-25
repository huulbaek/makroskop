#!/bin/bash
# Scenario batch 3: temporary variants of the shocks already solved permanently.
#   _midl = AR profile (0.9^dt, the Finance Ministry multiplier standard), _blip = shock year only.
# Both are UNFINANCED here (no tax reaction) — the definition panel says so.
# Every run exports its continuation stages (free nonlinearity data). Run detached on the box:
#   nohup bash cloud/run_batch3.sh > batch3.log 2>&1 &
# Idempotent and resumable like batch 2.
set -uo pipefail
cd "$(dirname "$0")/../etl"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1
export FREESOLVER_BACKEND=umfpack,superlu
export OPENBLAS_NUM_THREADS=16 OMP_NUM_THREADS=16
echo 1000 > /proc/self/oom_score_adj 2>/dev/null || true

run() {
  local out="$1"; shift
  if [ -f "shock_gdx/$out" ]; then echo "SKIP $out (already exported)"; return; fi
  echo "=============================================================="
  echo "SCENARIO $out"
  echo "=============================================================="
  uv run python freesolver.py solve-export --from-year 2029 --export-stages "$@" --out "shock_gdx/$out" \
    || echo "FAILED: $out (continuing with the rest)"
}

# Rente first: the flagship, and the one whose permanent variant is already validated.
run Rente_midl.gdx              --shock-name rRenteECB --shock-years 2030-2129 --shock-delta 0.01 --shock-profile ar
run Rente_blip.gdx              --shock-name rRenteECB --shock-years 2030-2129 --shock-delta 0.01 --shock-profile blip
run Bundskat_midl.gdx           --shock-name tBund     --shock-years 2030-2129 --shock-delta 0.01 --shock-profile ar
run Offentligt_forbrug_midl.gdx --shock-name uG        --shock-years 2030-2129 --shock-factor 1.01 --shock-profile ar
run Offentligt_forbrug_blip.gdx --shock-name uG        --shock-years 2030-2129 --shock-factor 1.01 --shock-profile blip

# Foreign-price shocks (bundles): the price shock that actually bites in this configuration.
run Udenlandske_priser_ufin.gdx         --shock-name pM,pXUdl --shock-years 2030-2129 --shock-factor 1.01
run Importpris_ufin.gdx                 --shock-name pM       --shock-years 2030-2129 --shock-factor 1.01
run Eksportkonkurrerende_priser_ufin.gdx --shock-name pXUdl   --shock-years 2030-2129 --shock-factor 1.01

echo "BATCH 3 DONE — fetch with:"
echo "  scp 'root@<box>:makroskop-cloud/etl/shock_gdx/*.gdx' etl/shock_gdx/"
