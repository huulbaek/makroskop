"""Fiscal multipliers from the solved scenarios, next to DREAM's published ones.

    uv run python multipliers.py [--shocks-dir PATH] [--out PATH]

Multiplier in year t = ΔBNP_t / Δ(instrument cost)_t, both nominal (mia. kr.), for the
permanent unfinanced scenarios; year 1 = the shock year (2030). This is the definition
DREAM uses in "Finanspolitiske multiplikatorer i MAKRO" (December 2021), whose year-1 and
year-2 numbers for the permanent unfinanced shocks are the reference column. Rows without a
solved GDX are written with `ours: null` so the page can show them as pending.
"""
from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

import gams.transfer as gt
import gamspy_base

REFERENCE = {
    "source": "DREAM: Finanspolitiske multiplikatorer i MAKRO (december 2021), tabel 3.1 og 3.2, "
              "permanent ufinansieret stød",
    "url": "https://dreamgruppen.dk/media/9752/finanspolitiske_multiplikatorer_i_makro.pdf",
    "modelDa": "MAKRO (beta-version, 2021), stødår 2026",
}

SHOCK_YEAR = 2030

# (scenario id, label, instrument-cost series, sign, DREAM year-1, DREAM year-2, note)
ROWS = [
    ("Bundskat_ufin", "Bundskat", ("vtBund", "tot"), -1.0, 0.69, 0.69,
     "Skattestigning her, skattelettelse hos DREAM; multiplikatoren er fortegnsvendt, så tallene er sammenlignelige."),
    ("Offentlig_varekoeb_ufin", "Offentligt materialekøb", ("vR", "off"), 1.0, 0.73, 0.62, None),
    ("Offentlig_Beskaeftigelse_ufin", "Offentlig beskæftigelse", ("vLoensum", "off"), 1.0, 0.80, 0.48,
     "DREAM endogeniserer offentligt forbrug og holder materialekøb fast i dette stød; MAKROskop hæver kun timerne."),
    ("Offentlige_investeringer_ufin", "Offentlige investeringer", ("vI_s", ("iTot", "off")), 1.0, 0.77, 0.68, None),
    ("Offentligt_forbrug_ufin", "Offentligt forbrug (alle input)", ("vG", "gTot"), 1.0, None, None,
     "Ingen DREAM-reference for det samlede stød; vist for fuldstændighed."),
]


def series(container: gt.Container, name: str, key, year: int) -> float:
    df = container.data[name].records
    keys = [c for c in df.columns if c not in ("level", "marginal", "lower", "upper", "scale")]
    sel = df[df[keys[-1]].astype(str) == str(year)]
    if isinstance(key, tuple):
        for col, val in zip(keys[:-1], key):
            sel = sel[sel[col] == val]
    elif key is not None:
        sel = sel[sel[keys[0]] == key]
    if len(sel) != 1:
        raise KeyError(f"{name}{key} {year}: {len(sel)} records")
    return float(sel["level"].iloc[0])


def multiplier(ref: gt.Container, run: gt.Container, cost, sign: float, year: int) -> tuple[float, float]:
    d_gdp = series(run, "vBNP", None, year) - series(ref, "vBNP", None, year)
    d_cost = series(run, cost[0], cost[1], year) - series(ref, cost[0], cost[1], year)
    return sign * d_gdp / d_cost, 100.0 * d_cost / series(ref, "vBNP", None, year)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shocks-dir", type=Path, default=Path(__file__).parent / "shock_gdx")
    parser.add_argument("--out", type=Path,
                        default=Path(__file__).parent.parent / "app" / "static" / "data" / "multipliers.json")
    args = parser.parse_args()
    ref = gt.Container(str(args.shocks_dir / "_reference.gdx"), system_directory=gamspy_base.directory)
    rows = []
    for scenario, label, cost, sign, dream1, dream2, note in ROWS:
        path = args.shocks_dir / f"{scenario}.gdx"
        ours = None
        if path.exists():
            run = gt.Container(str(path), system_directory=gamspy_base.directory)
            y1, impulse = multiplier(ref, run, cost, sign, SHOCK_YEAR)
            y2, _ = multiplier(ref, run, cost, sign, SHOCK_YEAR + 1)
            ours = {"year1": round(y1, 2), "year2": round(y2, 2), "impulsePctGdp": round(impulse, 3)}
            print(f"{label:32s} år 1 {y1:5.2f}  år 2 {y2:5.2f}  (impuls {impulse:.2f} pct. af BNP)"
                  + (f"   DREAM {dream1:.2f} / {dream2:.2f}" if dream1 is not None else ""))
        else:
            print(f"{label:32s} afventer {path.name}")
        rows.append({"id": scenario, "labelDa": label, "costSeries": f"{cost[0]}[{cost[1]}]",
                     "ours": ours, "dream": {"year1": dream1, "year2": dream2}, "noteDa": note})
    out = {"generated": datetime.date.today().isoformat(), "shockYear": SHOCK_YEAR,
           "definitionDa": "Multiplikator = ændring i nominelt BNP / ændring i instrumentets nominelle "
                           "udgift (eller provenu) i samme år, permanent ufinansieret stød.",
           "reference": REFERENCE, "rows": rows}
    args.out.write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
