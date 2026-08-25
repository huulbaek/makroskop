"""How linear is MAKRO's response to a shock?

Compares the continuation stages that `freesolver.py solve-export --export-stages`
writes (`<name>_sNNN.gdx`, NNN = share of the shock in permille) with the final
solution `<name>.gdx`. If the model were linear, the deviation at share s would be
exactly s times the deviation at share 1. The report shows how far it is from that,
per catalog series — which tells us whether scaling a solved scenario in the app
(e.g. showing +50 bp as half of +100 bp) is honest.

Usage:  uv run python nonlinearity.py Rente_ufin [--shocks-dir shock_gdx] [--from 2030 --to 2100]
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from extract import extract_detrended, open_gdx


def deviations(solved: dict[str, dict[int, float]], reference: dict[str, dict[int, float]],
               years: range) -> dict[str, dict[int, float]]:
    """Deviation from the reference in the ETL's display units (pct or pct-point)."""
    out: dict[str, dict[int, float]] = {}
    for key, series in solved.items():
        base = reference.get(key)
        if not base:
            continue
        out[key] = {}
        for year in years:
            if year not in series or year not in base:
                continue
            if _is_pct(key):
                if base[year] != 0:
                    out[key][year] = (series[year] / base[year] - 1) * 100
            else:
                out[key][year] = (series[year] - base[year]) * 100
    return out


def _is_pct(key: str) -> bool:
    from catalog import RATIOS, SERIES
    if any(key == ratio[0] for ratio in RATIOS):
        return False
    for sdef in SERIES:
        if sdef.key == key:
            return sdef.dev_mode == "pct"
    return True  # sector series


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="scenario file stem, e.g. Rente_ufin")
    parser.add_argument("--shocks-dir", type=Path, default=Path(__file__).parent / "shock_gdx")
    parser.add_argument("--from", dest="year_from", type=int, default=2030)
    parser.add_argument("--to", dest="year_to", type=int, default=2100)
    args = parser.parse_args()

    years = range(args.year_from, args.year_to + 1)
    reference = extract_detrended(open_gdx(args.shocks_dir / "_reference.gdx"))
    final = deviations(extract_detrended(open_gdx(args.shocks_dir / f"{args.name}.gdx")), reference, years)

    stage_files = sorted(args.shocks_dir.glob(f"{args.name}_s[0-9][0-9][0-9].gdx"))
    if not stage_files:
        raise SystemExit(f"no stage files {args.name}_sNNN.gdx in {args.shocks_dir} "
                         "(solve with --export-stages)")

    print(f"{args.name}: final solution vs {len(stage_files)} continuation stages, {years.start}-{years.stop - 1}")
    print(f"{'share':>7}  {'series':>14}  {'max |dev|':>10}  {'linear err':>11}  {'worst year':>10}")
    for stage_file in stage_files:
        share = int(re.search(r"_s(\d{3})\.gdx$", stage_file.name).group(1)) / 1000
        stage = deviations(extract_detrended(open_gdx(stage_file)), reference, years)
        rows = []
        for key, series in final.items():
            if key not in stage:
                continue
            scale = max(abs(v) for v in series.values()) if series else 0.0
            if scale < 1e-6:
                continue  # series does not respond to the shock
            worst_year, worst = None, 0.0
            for year, value in series.items():
                if year not in stage[key]:
                    continue
                err = abs(stage[key][year] - share * value) / scale  # relative to the final response size
                if err > worst:
                    worst_year, worst = year, err
            rows.append((worst, key, scale, worst_year))
        rows.sort(reverse=True)
        headline = [r for r in rows if r[1] in ("qBNP", "nL", "pBolig", "saldo2bnp", "qC", "qI")]
        median = sorted(r[0] for r in rows)[len(rows) // 2] if rows else float("nan")
        print(f"--- share {share:.3f}: median linear error {median:.1%} of the final response "
              f"across {len(rows)} responding series; worst:")
        for worst, key, scale, year in rows[:3] + headline:
            print(f"{share:7.3f}  {key:>14}  {scale:10.3g}  {worst:10.1%}  {year!s:>10}")


if __name__ == "__main__":
    main()
