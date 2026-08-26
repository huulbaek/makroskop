#!/bin/bash
# Scenario batch 2: eight shocks, sequential, checkpointed. Run detached on the box:
#   nohup bash cloud/run_batch2.sh > batch2.log 2>&1 &
# Safe to relaunch after any kill — every scenario resumes from its last converged stage.
set -uo pipefail
cd "$(dirname "$0")/../etl"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1
# NB: no FREESOLVER_BACKEND override (and no OPENBLAS/OMP_NUM_THREADS). Keeping pardiso first in
# the chain makes pypardiso load MKL, which UMFPACK's BLAS then runs on in parallel; with the
# override the process ran single-threaded on kvxopt's serial OpenBLAS: 1400–2700 s per
# factorization (batch2.log, 2026-08-25) versus 330–680 s (run6.log) on the same box.
# Shared box: if memory runs out, the kernel should kill the (resumable) solver, not Dokploy.
echo 1000 > /proc/self/oom_score_adj 2>/dev/null || true

run() {
  local out="$1"; shift
  if [ -f "shock_gdx/$out" ]; then echo "SKIP $out (already exported)"; return; fi
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
# DREAM's Offentligt_forbrug scales the public sector's exogenous inputs (not uG, which is only the nest share)
run Offentligt_forbrug_ufin.gdx              --shock-name "qR(off,*),qE(off,*),hL(off,*),qI_s(!iTot,off,*)" --shock-years 2030-2129 --shock-factor 1.01
# taxable transfer types only (DREAM: not ubeskat[ovf])
run Skattepligtig_indkomstoverforsel_ufin.gdx --shock-name "uvOvfSats(!boernyd|boligyd|iskatpl|groen|lumpsumovf,*)" --shock-years 2030-2129 --shock-factor 1.01
run Eksportmarkedsvaekst_ufin.gdx            --shock-name uXMarked   --shock-years 2030-2129 --shock-factor 1.01
run Befolkning_ufin.gdx                      --shock-name nPop       --shock-years 2030-2129 --shock-factor 1.01

echo "BATCH DONE — fetch with:"
echo "  scp 'root@<box>:makroskop-cloud/etl/shock_gdx/*.gdx' etl/shock_gdx/"
