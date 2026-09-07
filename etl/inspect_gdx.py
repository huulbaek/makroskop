"""Inspect the structure of MAKRO's baseline.gdx and sets.gdx.

One-off exploration script: prints symbol inventory, dimensions, and year
coverage for the headline variables used by DREAM's own plotting pipeline.
"""

from pathlib import Path

import gams.transfer as gt
import gamspy_base

MAKRO_ROOT = Path(__file__).resolve().parent.parent.parent / "MAKRO"

HEADLINE_VARIABLES = [
    "qBNP", "vBNP", "qG", "qBVT", "sqBVT", "nL", "snL", "qC", "qXy", "qM",
    "qI_s", "qIbErhverv", "pBVT", "vhW_DA", "pBolig", "vPrimSaldo", "vSaldo",
    "rHBI", "tLukning", "nBruttoLedig", "nBruttoArbsty", "pC", "rRente",
    "pOlie", "pM", "vLoensum", "qK", "pL", "vOff13Net", "tBund",
]


def describe_container(label: str, path: Path) -> gt.Container:
    container = gt.Container(str(path), system_directory=gamspy_base.directory)
    counts: dict[str, int] = {}
    for symbol in container.data.values():
        counts[type(symbol).__name__] = counts.get(type(symbol).__name__, 0) + 1
    print(f"=== {label}: {path.name} ===")
    print(f"symbols: {len(container.data)}  by type: {counts}")
    return container


def main() -> None:
    sets = describe_container("SETS", MAKRO_ROOT / "Model/Gdx/sets.gdx")
    for name, symbol in list(sets.data.items())[:80]:
        if isinstance(symbol, gt.Set):
            elements = list(symbol.records[symbol.records.columns[0]]) if symbol.records is not None else []
            preview = elements if len(elements) <= 12 else elements[:12] + ["..."]
            print(f"  set {name} [{len(elements)}]: {preview}")

    baseline = describe_container("BASELINE", MAKRO_ROOT / "Model/Gdx/baseline.gdx")
    print("\n--- headline variables ---")
    for name in HEADLINE_VARIABLES:
        if name not in baseline.data:
            print(f"  {name}: MISSING")
            continue
        symbol = baseline.data[name]
        records = symbol.records
        n_records = 0 if records is None else len(records)
        print(f"  {name}: dims={symbol.dimension} domain={symbol.domain_names} records={n_records}")
        if records is not None and n_records > 0:
            print(f"    columns={list(records.columns)}")
            print(f"    sample={records.iloc[0].to_dict()}")

    time_columns = baseline.data["qBNP"].records
    if time_columns is not None:
        years = sorted(time_columns["t"].unique(), key=int)
        print(f"\nqBNP year coverage: {years[0]}..{years[-1]} ({len(years)} years)")


if __name__ == "__main__":
    main()
