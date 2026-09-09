#!/bin/bash
# Extra full-horizon runs after the 2030 re-run (makroskop-m1i, DREAM-size comparison):
#   setsid nohup bash cloud/run_extra_2030.sh > extra2030.log 2>&1 < /dev/null &
# 1. Moms_ned: a real VAT cut (tMoms -0.5 pct.-point) instead of mirroring the increase.
# 2. DREAM-size runs of the three shocks DREAM normalises to 1 pct. of GDP, written to
#    etl/shock_gdx_dreamsize/ (NOT scanned by extract.py) for etl/dream_comparison.py, so the
#    comparison with "Shock Reactions in MAKRO" needs no linear upscaling. Factors from
#    etl/dream_may2025.json dreamShockOverOurs: uXMarked x1.261, qR(off) x11.785, hL(off) x6.553 of our +1 %.
# Sequential (one factorization peaks at ~53 of 62 GB), idempotent, resumable from checkpoints.
set -uo pipefail
cd "$(dirname "$0")/../etl"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1
echo 1000 > /proc/self/oom_score_adj 2>/dev/null || true
mkdir -p shock_gdx_dreamsize

run() {
  local out="$1"; shift
  if [ -f "$out" ]; then echo "SKIP $out (already exported)"; return; fi
  echo "=============================================================="
  echo "SCENARIO $out"
  echo "=============================================================="
  uv run python freesolver.py solve-export --from-year 2030 "$@" --out "$out" \
    || echo "FAILED: $out (continuing with the rest)"
}

run shock_gdx/Moms_ned_ufin.gdx            --shock-name "tMoms_y,tMoms_m" --shock-years 2030-2129 --shock-delta -0.005
run shock_gdx/Moms_ned_perm.gdx            --shock-name "tMoms_y,tMoms_m" --shock-years 2030-2129 --shock-delta -0.005 --closure tax-reaction
run shock_gdx_dreamsize/Eksportmarkedsvaekst.gdx      --shock-name uXMarked   --shock-years 2030-2129 --shock-factor 1.01261
run shock_gdx_dreamsize/Offentlig_varekoeb.gdx        --shock-name "qR(off,*)" --shock-years 2030-2129 --shock-factor 1.11785
run shock_gdx_dreamsize/Offentlig_Beskaeftigelse.gdx  --shock-name "hL(off,*)" --shock-years 2030-2129 --shock-factor 1.06553
echo "=== $(date -Is) EXTRA RUNS DONE ==="
