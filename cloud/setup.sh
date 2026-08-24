#!/bin/bash
# Run ON THE BOX (Ubuntu 22.04/24.04 x86_64, 64GB+ RAM) from the unpacked bundle root.
# Installs uv + deps, extracts the model, verifies the parser to machine precision.
set -euo pipefail
cd "$(dirname "$0")/.."

command -v unzip >/dev/null || (apt-get update -qq && apt-get install -y -qq unzip)
command -v uv >/dev/null || (curl -LsSf https://astral.sh/uv/install.sh | sh && export PATH="$HOME/.local/bin:$PATH")
export PATH="$HOME/.local/bin:$PATH"

cd etl
uv sync --frozen
# MKL Pardiso: x86-only, big speedup for the factorizations; fine if it fails elsewhere
uv pip install pypardiso && echo "pypardiso installed (MKL Pardiso backend active)" || echo "pypardiso unavailable — SuperLU fallback"

mkdir -p cache/convert
unzip -o -q ../data/deep_dynamic_calibration.zip -d cache/convert
echo "parsing the scalar system (~1 min) ..."
uv run python freesolver.py parse
echo "verifying residuals at the solution point ..."
uv run python freesolver.py check
echo
echo "Setup done. Now run:  bash cloud/run.sh"
