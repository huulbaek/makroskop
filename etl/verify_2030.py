"""Acceptance check for the --from-year 2030 re-run (makroskop-uh2).

    uv run python verify_2030.py [--shocks-dir shock_gdx] [--json-dir ../app/static/data/shocks]

1. every scenario GDX carries the solver stamp `from_year=2030` (DREAM's shock_year: 2030 is
   the first solved year, 2029 stays at the reference like DREAM's fixed t0);
2. every exported shock JSON has exactly-zero deviations in 2029 for every series and a
   nonzero deviation somewhere from 2030 on (a 2029 response means an anticipated shock).
Exit status 1 with one line per offending file when either check fails.
"""

import argparse
import json
import sys
from pathlib import Path

SHOCK_YEAR = 2030


def gdx_from_year(path: Path) -> str:
    import gams.transfer as gt
    import gamspy_base

    container = gt.Container(system_directory=gamspy_base.directory)
    container.read(str(path), symbols=["makroskop_meta"])
    records = container.data["makroskop_meta"].records if "makroskop_meta" in container.data else None
    if records is None:
        return "(unstamped)"
    stamp = {str(row.iloc[0]): str(row.iloc[1]) for _, row in records.iterrows()}
    return stamp.get("from_year", "(no from_year)")


def leaf_series(node) -> list[list]:
    """Deviation lists inside a (possibly sector-nested) series entry."""
    if isinstance(node, list):
        return [node]
    if isinstance(node, dict):
        return [leaf for child in node.values() for leaf in leaf_series(child)]
    return []


def check_json(path: Path, years: list[int]) -> str | None:
    data = json.loads(path.read_text())
    if data.get("synthetic"):
        return None
    pre = years.index(SHOCK_YEAR - 1)
    anticipated, moved = [], False
    for name, node in data["deviations"].items():
        for values in leaf_series(node):
            if values[pre] not in (None, 0, 0.0):
                anticipated.append(f"{name}[{SHOCK_YEAR - 1}]={values[pre]}")
            if any(v not in (None, 0, 0.0) for v in values[pre + 1:]):
                moved = True
    if anticipated:
        return f"{path.name}: {len(anticipated)} series move in {SHOCK_YEAR - 1} (e.g. {', '.join(anticipated[:3])})"
    if not moved:
        return f"{path.name}: no deviation at all from {SHOCK_YEAR} on"
    return None


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--shocks-dir", type=Path, default=Path(__file__).parent / "shock_gdx")
    parser.add_argument("--json-dir", type=Path, default=Path(__file__).parent.parent / "app/static/data/shocks")
    args = parser.parse_args()

    failures: list[str] = []
    gdx_files = sorted(p for p in args.shocks_dir.glob("*.gdx") if not p.name.startswith("_"))
    for path in gdx_files:
        stamp = gdx_from_year(path)
        if stamp != str(SHOCK_YEAR):
            failures.append(f"{path.name}: from_year={stamp}")
    print(f"GDX: {len(gdx_files)} scenario files, {len(gdx_files) - len(failures)} stamped from_year={SHOCK_YEAR}")

    meta_path = args.json_dir.parent / "meta.json"
    json_files = sorted(p for p in args.json_dir.glob("*.json") if not p.name.startswith("_"))
    if json_files and meta_path.exists():
        meta = json.loads(meta_path.read_text())
        years = list(range(meta["yearStart"], meta["yearEnd"] + 1))
        json_failures = [msg for path in json_files if (msg := check_json(path, years))]
        print(f"JSON: {len(json_files)} shock files, {len(json_files) - len(json_failures)} with zero {SHOCK_YEAR - 1} deviations")
        failures += json_failures
    else:
        print(f"JSON: skipped ({args.json_dir} or {meta_path} missing)")

    for line in failures:
        print("  FAIL", line)
    print("OK" if not failures else f"{len(failures)} failures")
    sys.exit(1 if failures else 0)


if __name__ == "__main__":
    main()
