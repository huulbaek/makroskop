"""DREAM's "Shock Reactions in MAKRO" (May 2025) next to MAKROskop's unfinanced 2030 scenarios.

    uv run python dream_comparison.py [--readings PATH] [--shocks-dir PATH] [--json-dir PATH] [--out PATH]

DREAM normalises fiscal and foreign-demand shocks to 1 pct. of GDP and plots employment in
1,000 persons, exports and consumption in pct.-points of GDP; MAKROskop shocks the raw instrument
and stores pct. deviations. `convert` maps ours onto DREAM's units and shock size — a linear
rescaling (MAKRO is near-linear for these shock sizes, see CLAUDE.md "makro-linearity") using the
2030 levels of _reference.gdx. DREAM's values were read off the note's figures
(etl/dream_may2025.json, about +-10 % of the plotted range).
"""

from __future__ import annotations

import argparse
import datetime
import json
from dataclasses import dataclass
from pathlib import Path

SHOCK_YEAR = 2030
COLUMNS = [2030, 2031, 2032, 2033, 2035, 2040, 2050, 2080]  # the years DREAM's figures were read at

# (MAKROskop series key, Danish label, DREAM's unit) — table row order
SERIES = [
    ("nL", "Beskæftigelse", "1.000 personer"),
    ("qBNP", "BNP", "pct."),
    ("qX", "Eksport", "pct. af BNP"),
    ("qC", "Privat forbrug", "pct. af BNP"),
    ("vhW", "Timeløn", "pct."),
]
READING_KEY = {"qX": "qX_gdp", "qC": "qC_gdp"}  # dream_may2025.json names GDP-share series *_gdp

# (shock id in dream_may2025.json / catalog, Danish note or None)
SHOCKS = [
    ("Eksportmarkedsvaekst", None),
    ("Offentlig_varekoeb", None),
    ("Offentlig_Beskaeftigelse",
     "DREAM endogeniserer offentligt forbrug og holder materialekøb fast i dette stød; MAKROskop hæver kun timerne."),
    ("Rente", "Samme stød i begge: ECB-renten +1 pct.-point, permanent."),
    ("Importpris", "Samme stød i begge: importpriserne +1 pct., permanent."),
    ("Arbejdsudbud_beskaeftigelse",
     "Begge fastlåser den strukturelle beskæftigelse 1 pct. højere og frigiver deltagelses-ulempen (exo/endo-bytte)."),
]


@dataclass(frozen=True)
class RefLevels:
    """2030 reference levels behind the unit conversions."""

    employment_thousands: float  # nL(tot), 1,000 persons
    export_share: float  # vX(xTot) / vBNP
    consumption_share: float  # vC(cTot) / vBNP


def convert(key: str, pct_deviation: float, scale: float, ref: RefLevels) -> float:
    """A MAKROskop pct. deviation in DREAM's unit at DREAM's shock size (`scale` x ours)."""
    if key == "nL":
        return pct_deviation / 100.0 * ref.employment_thousands * scale
    if key == "qX":
        return pct_deviation * ref.export_share * scale
    if key == "qC":
        return pct_deviation * ref.consumption_share * scale
    if key in ("qBNP", "vhW"):
        return pct_deviation * scale
    raise KeyError(f"no DREAM unit defined for series {key}")


def row_values(key: str, readings: dict[str, float], ours: list[float | None], years: list[int],
               scale: float, ref: RefLevels, columns: list[int]) -> dict:
    """One table row: DREAM's reading and our converted value per column year (None when missing)."""
    dream = {str(year): readings.get(str(year)) for year in columns}
    scaled: dict[str, float | None] = {}
    for year in columns:
        index = years.index(year) if year in years else -1
        value = ours[index] if index >= 0 else None
        rounded = None if value is None else round(convert(key, value, scale, ref), 2)
        scaled[str(year)] = 0.0 if rounded == 0 else rounded  # no "-0.0" in the table
    return {"series": key, "dream": dream, "ours": scaled}


def size_note(scale: float, exact: bool) -> tuple[float, str]:
    """(factor applied to our deviations, Danish caption) — 1.0 when the run itself has DREAM's size."""
    if exact:
        return 1.0, "Løst i DREAMs stødstørrelse (1 pct. af BNP), ingen opskalering."
    if abs(scale - 1.0) < 1e-9:
        return 1.0, "Samme stødstørrelse i begge modeller."
    scale_da = f"{scale:.2f}".replace(".", ",")
    return scale, (f"DREAMs stød er 1 pct. af BNP, svarende til {scale_da} × MAKROskops stød; "
                   f"MAKROskops tal er skaleret lineært op med den faktor.")


def dream_size_deviations(gdx_path: Path, reference_gdx: Path) -> dict[str, list[float | None]]:
    """Pct. deviations of a run solved at DREAM's shock size, via extract.py's own machinery."""
    from extract import extract_detrended, extract_shock, open_gdx

    return extract_shock(gdx_path, extract_detrended(open_gdx(reference_gdx)))["deviations"]


def reference_levels(reference_gdx: Path) -> RefLevels:
    from multipliers import series
    import gams.transfer as gt
    import gamspy_base

    ref = gt.Container(str(reference_gdx), system_directory=gamspy_base.directory)
    gdp = series(ref, "vBNP", None, SHOCK_YEAR)
    return RefLevels(employment_thousands=series(ref, "nL", "tot", SHOCK_YEAR),
                     export_share=series(ref, "vX", "xTot", SHOCK_YEAR) / gdp,
                     consumption_share=series(ref, "vC", "cTot", SHOCK_YEAR) / gdp)


def main() -> None:
    from catalog import SHOCKS as CATALOG

    here = Path(__file__).parent
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--readings", type=Path, default=here / "dream_may2025.json")
    parser.add_argument("--shocks-dir", type=Path, default=here / "shock_gdx")
    parser.add_argument("--json-dir", type=Path, default=here.parent / "app" / "static" / "data")
    parser.add_argument("--dream-size-dir", type=Path, default=here / "shock_gdx_dreamsize",
                        help="runs solved at DREAM's 1-pct-of-GDP size (cloud/run_extra_2030.sh); used instead of scaling")
    parser.add_argument("--out", type=Path, default=here.parent / "app" / "static" / "data" / "dream_comparison.json")
    args = parser.parse_args()

    readings = json.loads(args.readings.read_text(encoding="utf-8"))
    meta = json.loads((args.json_dir / "meta.json").read_text(encoding="utf-8"))
    years = list(range(meta["yearStart"], meta["yearEnd"] + 1))
    ref = reference_levels(args.shocks_dir / "_reference.gdx")
    labels = {shock.name: shock.label_da for shock in CATALOG}
    print(f"reference 2030: nL {ref.employment_thousands:.1f} k, vX/vBNP {ref.export_share:.4f}, "
          f"vC/vBNP {ref.consumption_share:.4f}")

    shocks = []
    for shock_id, note in SHOCKS:
        scenario = f"{shock_id}_ufin"
        path = args.json_dir / "shocks" / f"{scenario}.json"
        if not path.exists():
            print(f"{scenario}: missing, skipped")
            continue
        deviations = json.loads(path.read_text(encoding="utf-8"))["deviations"]
        exact_path = args.dream_size_dir / f"{shock_id}.gdx"
        exact = exact_path.exists()
        if exact:
            deviations = dream_size_deviations(exact_path, args.shocks_dir / "_reference.gdx")
        scale, scale_note = size_note(float(readings["dreamShockOverOurs"][shock_id]), exact)
        rows = [row_values(key, readings["readings"][shock_id].get(READING_KEY.get(key, key), {}),
                           deviations[key], years, scale, ref, COLUMNS)
                for key, _, _ in SERIES if READING_KEY.get(key, key) in readings["readings"][shock_id]]
        shocks.append({"id": shock_id, "labelDa": labels[shock_id], "scenario": scenario, "solvedAtDreamSize": exact,
                       "scale": round(scale, 3), "scaleNoteDa": scale_note, "noteDa": note, "rows": rows})
        first = rows[0]
        print(f"{labels[shock_id]:32s} x{scale:5.2f}  {first['series']} 2030: DREAM {first['dream']['2030']}  ours {first['ours']['2030']}")

    out = {
        "generated": datetime.date.today().isoformat(),
        "shockYear": SHOCK_YEAR,
        "columns": COLUMNS,
        "reference": {
            "source": "DREAM: Shock Reactions in MAKRO (maj 2025), Høegh, Partsch og Bonde",
            "url": "https://dreamgruppen.dk/Media/638833322447461188/shock_reactions_in_makro_may_2025.pdf",
            "modelDa": "MAKRO, december 2024-versionen",
            "methodDa": "aflæst fra notatets figurer med en usikkerhed på omkring ±10 pct. af det viste interval",
        },
        "series": [{"key": key, "labelDa": label, "unitDa": unit} for key, label, unit in SERIES],
        "shocks": shocks,
    }
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
