"""Compare two solution GDX files variable by variable (solver A/B testing).

    uv run python compare_gdx.py A.gdx B.gdx [--top 8]

Prints the distribution of relative level differences over every record of every
variable/parameter present in both files (|a-b| / max(|a|, |b|, 1e-6)) and the worst
symbols. Two solves of the same scenario to tolerance 1e-9 should agree to ~1e-9.
"""

import argparse
from pathlib import Path

import numpy as np


def levels(path: Path) -> dict[str, np.ndarray]:
    import gams.transfer as gt
    import gamspy_base

    container = gt.Container(str(path), system_directory=gamspy_base.directory)
    out: dict[str, np.ndarray] = {}
    for name, symbol in container.data.items():
        records = symbol.records
        if records is None or "level" not in records.columns and "value" not in records.columns:
            continue
        column = "level" if "level" in records.columns else "value"
        out[name] = records[column].to_numpy(dtype=float)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("a", type=Path)
    parser.add_argument("b", type=Path)
    parser.add_argument("--top", type=int, default=8)
    args = parser.parse_args()
    a, b = levels(args.a), levels(args.b)
    common = [name for name in a if name in b and a[name].shape == b[name].shape and a[name].size]
    worst = []
    all_rel = []
    for name in common:
        rel = np.abs(a[name] - b[name]) / np.maximum(np.maximum(np.abs(a[name]), np.abs(b[name])), 1e-6)
        rel = rel[np.isfinite(rel)]
        if rel.size == 0:
            continue
        all_rel.append(rel)
        worst.append((float(rel.max()), name))
    every = np.concatenate(all_rel)
    print(f"{len(common)} symbols, {every.size:,} records compared")
    print(f"relative difference: median {np.median(every):.1e}, 99.9 % {np.quantile(every, 0.999):.1e}, max {every.max():.1e}")
    for value, name in sorted(worst, reverse=True)[: args.top]:
        print(f"  {name:24s} max rel diff {value:.1e}")


if __name__ == "__main__":
    main()
