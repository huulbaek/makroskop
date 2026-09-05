#!/bin/bash
# Re-run of every published scenario with --from-year 2030 (makroskop-uh2: batches 2-4 were solved
# with 2029 as a free anticipation year). Run detached on the box:
#   setsid nohup bash cloud/run_all_2030.sh > rerun2030.log 2>&1 < /dev/null &
# Strictly sequential — one full-horizon factorization peaks at ~53 of the box's 62 GB — and
# idempotent: each batch skips scenarios whose GDX already exists and resumes killed ones from
# their last converged continuation stage, so relaunching this script continues where it stopped.
# Park the old results first (mv etl/shock_gdx etl/shock_gdx_2029 && mkdir etl/shock_gdx).
set -uo pipefail
cd "$(dirname "$0")/.."
for batch in run_batch2.sh run_batch3.sh run_batch4.sh; do
  echo "=== $(date -Is) START cloud/$batch ==="
  bash "cloud/$batch"
  echo "=== $(date -Is) END cloud/$batch (exit $?) ==="
done
echo "=== $(date -Is) ALL BATCHES DONE: $(ls etl/shock_gdx/*.gdx 2>/dev/null | wc -l) GDX files ==="
