#!/bin/bash
# Run LOCALLY: bundles everything the cloud box needs into makroskop-cloud.tar.gz (~190MB).
# Usage: cloud/pack.sh [path-to-MAKRO-repo]   (default: ~/vserver/MAKRO)
set -euo pipefail

MAKRO="${1:-$HOME/vserver/MAKRO}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
STAGE="$(mktemp -d)/makroskop-cloud"
mkdir -p "$STAGE/etl/shock_gdx" "$STAGE/data" "$STAGE/cloud"

cp "$ROOT"/etl/*.py "$ROOT"/etl/pyproject.toml "$ROOT"/etl/uv.lock "$STAGE/etl/"
cp "$ROOT"/cloud/setup.sh "$ROOT"/cloud/run.sh "$ROOT"/cloud/run_batch2.sh "$ROOT"/cloud/run_batch3.sh "$ROOT"/cloud/run_batch4.sh "$ROOT"/cloud/relaunch_after_stage.sh "$STAGE/cloud/"
cp "$MAKRO/Model/deep_dynamic_calibration.zip" "$STAGE/data/"
cp "$MAKRO/Model/Gdx/baseline.gdx" "$STAGE/data/"

tar -czf "$ROOT/makroskop-cloud.tar.gz" -C "$(dirname "$STAGE")" makroskop-cloud
rm -rf "$(dirname "$STAGE")"
echo "wrote $ROOT/makroskop-cloud.tar.gz ($(du -h "$ROOT/makroskop-cloud.tar.gz" | cut -f1))"
echo
echo "Next:  scp makroskop-cloud.tar.gz root@<box>:  &&  ssh root@<box>"
echo "Then:  tar xzf makroskop-cloud.tar.gz && cd makroskop-cloud && bash cloud/setup.sh"
