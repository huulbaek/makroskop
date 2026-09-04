#!/bin/bash
# Run ON THE BOX after setup.sh. The full-horizon run plan, cheapest-risk first.
# Each step prints timings; results land in etl/shock_gdx/*.gdx — copy them back with:
#   scp 'root@<box>:makroskop-cloud/etl/shock_gdx/*.gdx' etl/shock_gdx/
set -euo pipefail
cd "$(dirname "$0")/../etl"
export PATH="$HOME/.local/bin:$PATH"
export PYTHONUNBUFFERED=1

echo "=============================================================="
echo "STEP 1  Full-horizon factorization + Newton recovery test"
echo "        (2,197,277 equations; measures memory + time per iteration)"
echo "=============================================================="
uv run python freesolver.py newton --from-year 2022 --perturb 1e-4 --max-iter 6

echo "=============================================================="
echo "STEP 2  Export the unshocked reference (deviations are measured against this)"
echo "=============================================================="
uv run python freesolver.py export-baseline --out shock_gdx/_reference.gdx

echo "=============================================================="
echo "STEP 3  First real scenario: permanent ECB-rate shock +100bp from 2030"
echo "        (--from-year 2030 = DREAM shock_year; 2029 stays at the reference as t0)"
echo "        (continuation solver; output feeds MAKROskop directly)"
echo "=============================================================="
uv run python freesolver.py solve-export \
  --from-year 2030 \
  --shock-name rRenteECB --shock-years 2030-2129 --shock-delta 0.01 \
  --out shock_gdx/Rente_ufin.gdx

echo "=============================================================="
echo "STEP 4  Second scenario: Brent oil price +10 pct. from 2030, permanent"
echo "=============================================================="
uv run python freesolver.py solve-export \
  --from-year 2030 \
  --shock-name pOlieBrent --shock-years 2030-2129 --shock-factor 1.10 \
  --out shock_gdx/Oliepris_ufin.gdx

echo "=============================================================="
echo "DONE — copy etl/shock_gdx/*.gdx back to the laptop and run:"
echo "  cd etl && uv run python extract.py --shocks-dir shock_gdx"
echo "  cd ../app && bun run build     (scenarios appear in MAKROskop)"
echo "=============================================================="
