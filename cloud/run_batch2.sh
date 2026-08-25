#!/bin/bash
# Scenario batch 2: eight shocks, sequential, checkpointed. Run detached on the box:
#   nohup bash cloud/run_batch2.sh > batch2.log 2>&1 &
# Safe to relaunch after any kill — every scenario resumes from its last converged stage.
set -uo pipefail
cd "$(dirname "$0")/../etl"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1
export FREESOLVER_BACKEND=umfpack,superlu
export OPENBLAS_NUM_THREADS=16 OMP_NUM_THREADS=16   # threading experiment; harmless if ignored

run() {
  local out="$1"; shift
  echo "=============================================================="
  echo "SCENARIO $out"
  echo "=============================================================="
  uv run python freesolver.py solve-export --from-year 2029 "$@" --out "shock_gdx/$out" \
    || echo "FAILED: $out (continuing with the rest)"
}

run Bundskat_ufin.gdx                        --shock-name tBund      --shock-years 2030-2129 --shock-delta 0.01
run AM_bidrag_ufin.gdx                       --shock-name tAMbidrag  --shock-years 2030-2129 --shock-delta 0.01
run Selskabsskat_ufin.gdx                    --shock-name tSelskab   --shock-years 2030-2129 --shock-delta 0.01
run Ejendomsvaerdiskat_ufin.gdx              --shock-name tEjd       --shock-years 2030-2129 --shock-factor 1.10
run Offentligt_forbrug_ufin.gdx              --shock-name uG         --shock-years 2030-2129 --shock-factor 1.01
run Skattepligtig_indkomstoverforsel_ufin.gdx --shock-name uvOvfSats --shock-years 2030-2129 --shock-factor 1.01
run Eksportmarkedsvaekst_ufin.gdx            --shock-name uXMarked   --shock-years 2030-2129 --shock-factor 1.01
run Befolkning_ufin.gdx                      --shock-name nPop       --shock-years 2030-2129 --shock-factor 1.01

echo "BATCH DONE — fetch with:"
echo "  scp 'root@<box>:makroskop-cloud/etl/shock_gdx/*.gdx' etl/shock_gdx/"
