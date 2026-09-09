"""Extract MAKRO baseline (and any solved shock GDX files) to JSON for the web explorer.

Usage:
    uv run python extract.py [--makro-root PATH] [--out PATH] [--shocks-dir PATH] [--demo]

Reads `Model/Gdx/baseline.gdx` from the MAKRO repo and writes:
    out/meta.json         catalog of series, sectors, shocks, model version
    out/baseline.json     actual-level series (detrended model units re-trended
                          with MAKRO's fvt/fqt/fpt factors)
    out/shocks/<name>.json  deviation-from-baseline series per solved shock GDX

Shock GDX files are produced by MAKRO's Analysis/Standard_shocks pipeline
(requires a GAMS license) and dropped into --shocks-dir; this script only
reads them.
"""

import argparse
import hashlib
import json
import math
import subprocess
import zipfile
from pathlib import Path

import gams.transfer as gt
import gamspy_base

from catalog import (
    DISPLAY_SCALE, RATIOS, SECTOR_SERIES_TEMPLATES, SECTORS, SERIES, SHOCKS, VARIATIONS, SeriesDef,
    shock_definition,
)

YEAR_START = 1985
YEAR_END = 2100
YEARS = list(range(YEAR_START, YEAR_END + 1))
MODEL_HORIZON_END = 2129  # the solver re-solves the model through this year; the app displays to YEAR_END


def open_gdx(path: Path) -> gt.Container:
    return gt.Container(str(path), system_directory=gamspy_base.directory)


def sig_round(value: float, digits: int = 6) -> float:
    if value == 0 or not math.isfinite(value):
        return value
    return round(value, digits - 1 - int(math.floor(math.log10(abs(value)))))


def read_records(container: gt.Container, sdef: SeriesDef) -> dict[int, float]:
    """Read one time series (detrended model units) as {year: value}."""
    if sdef.gdx_name not in container.data:
        return {}
    records = container.data[sdef.gdx_name].records
    if records is None:
        return {}
    domain_columns = list(records.columns[: -5])  # last 5 cols: level/marginal/lower/upper/scale
    mask = None
    for column, element in zip(domain_columns, sdef.selector):
        column_mask = records[column].str.lower() == element.lower()
        mask = column_mask if mask is None else (mask & column_mask)
    selected = records if mask is None else records[mask]
    result: dict[int, float] = {}
    for _, row in selected.iterrows():
        value = row["level"]
        if math.isfinite(value):
            result[int(row["t"])] = value
    return result


def read_trend_factors(container: gt.Container) -> dict[str, dict[int, float]]:
    factors: dict[str, dict[int, float]] = {}
    for name in ["fvt", "fqt", "fpt"]:
        records = container.data[name].records
        factors[name] = {int(row["t"]): row["value"] for _, row in records.iterrows()}
    return factors


def to_column(values: dict[int, float]) -> list[float | None]:
    return [sig_round(values[year]) if year in values else None for year in YEARS]


def apply_trend(values: dict[int, float], trend: str | None, factors: dict[str, dict[int, float]]) -> dict[int, float]:
    if trend is None:
        return values
    factor = factors[trend]
    return {year: value * factor[year] for year, value in values.items() if year in factor}


def all_series_defs() -> list[SeriesDef]:
    defs = list(SERIES)
    for gdx_name, label_da, label_en, unit, trend in SECTOR_SERIES_TEMPLATES:
        for sector in SECTORS:
            defs.append(SeriesDef(
                key=f"{gdx_name}_{sector}",
                gdx_name=gdx_name,
                selector=(sector,),
                label_da=f"{label_da}, {sector}",
                label_en=f"{label_en}, {sector}",
                group="Brancher",
                unit_da=unit,
                trend=trend,
                dev_mode="pct",
            ))
    return defs


def extract_detrended(container: gt.Container, warn: bool = False) -> dict[str, dict[int, float]]:
    """Detrended series + ratios, enough for shock-deviation comparisons."""
    detrended: dict[str, dict[int, float]] = {}
    for sdef in all_series_defs():
        values = read_records(container, sdef)
        if not values:
            if warn:
                print(f"  WARNING: no data for {sdef.key} ({sdef.gdx_name}{list(sdef.selector)})")
            continue
        detrended[sdef.key] = values
    for key, numerator, denominator, *_ in RATIOS:
        if numerator in detrended and denominator in detrended:
            detrended[key] = {
                year: detrended[numerator][year] / detrended[denominator][year]
                for year in detrended[numerator]
                if year in detrended[denominator]
            }
    return detrended


def extract_baseline(container: gt.Container) -> tuple[dict[str, dict[int, float]], dict[str, list[float | None]]]:
    """Returns (detrended series for shock comparisons, actual-level columns for the app)."""
    factors = read_trend_factors(container)
    detrended = extract_detrended(container, warn=True)
    columns: dict[str, list[float | None]] = {}
    ratio_keys = {key for key, *_ in RATIOS}
    for sdef in all_series_defs():
        if sdef.key not in detrended:
            continue
        scale = DISPLAY_SCALE.get(sdef.key, 1)
        actual = apply_trend(detrended[sdef.key], sdef.trend, factors)
        columns[sdef.key] = to_column({year: value * scale for year, value in actual.items()})
    for key in ratio_keys:
        if key in detrended:
            columns[key] = to_column({year: value * 100 for year, value in detrended[key].items()})
    return detrended, columns


def read_hbi(container: gt.Container) -> float | None:
    if "rHBI" not in container.data:
        return None
    records = container.data["rHBI"].records
    if records is None or len(records) == 0:
        return None
    return sig_round(float(records.iloc[0]["level"]))


def extract_shock(gdx_path: Path, baseline_detrended: dict[str, dict[int, float]]) -> dict:
    """Compute deviation-from-baseline columns for one solved shock GDX."""
    container = open_gdx(gdx_path)
    solver_meta = read_solver_meta(container)
    deviations: dict[str, list[float | None]] = {}
    shock_detrended: dict[str, dict[int, float]] = {}
    for sdef in all_series_defs():
        if sdef.key not in baseline_detrended:
            continue
        values = read_records(container, sdef)
        if not values:
            continue
        shock_detrended[sdef.key] = values
        base = baseline_detrended[sdef.key]
        if sdef.dev_mode == "pct":
            dev = {y: (v / base[y] - 1) * 100 for y, v in values.items() if y in base and base[y] != 0}
        else:  # "pp" and "gdp_pp" handled below via ratios; raw pp here
            dev = {y: (v - base[y]) * 100 for y, v in values.items() if y in base}
        deviations[sdef.key] = to_column(dev)
    for key, numerator, denominator, *_ in RATIOS:
        if numerator in shock_detrended and denominator in shock_detrended and key in baseline_detrended:
            shock_ratio = {
                year: shock_detrended[numerator][year] / shock_detrended[denominator][year]
                for year in shock_detrended[numerator]
                if year in shock_detrended[denominator]
            }
            base_ratio = baseline_detrended[key]
            deviations[key] = to_column({
                year: (value - base_ratio[year]) * 100 for year, value in shock_ratio.items() if year in base_ratio
            })
    return {"deviations": deviations, "hbi": read_hbi(container), "solverMeta": solver_meta}


# Data vintage per MAKRO release, as DREAM asks results to be cited ("MAKRO 26-juni baseret på
# Nationalregnskabsdata fra marts 2026", Martin Bonde, 2026-09-09). Not derivable from the repo,
# so it is keyed on the README's version line; an unknown release gets no data-basis line.
DATA_BASIS_DA = {"MAKRO 2026-June": "Nationalregnskabsdata fra marts 2026"}


def model_version(makro_root: Path) -> dict[str, str]:
    readme_first_line = (makro_root / "README.md").read_text(encoding="utf-8").splitlines()[0]
    commit = subprocess.run(
        ["git", "-C", str(makro_root), "rev-parse", "--short", "HEAD"],
        capture_output=True, text=True, check=False,
    ).stdout.strip()
    name = readme_first_line.lstrip("# ").strip()
    return {"name": name, "commit": commit, "fingerprint": model_fingerprint(makro_root),
            "dataBasisDa": DATA_BASIS_DA.get(name, "")}


def model_fingerprint(makro_root: Path) -> str:
    """sha256 of raw.gms inside the calibration zip — the same stamp freesolver writes into its GDX files."""
    zip_path = makro_root / "Model/deep_dynamic_calibration.zip"
    if not zip_path.exists():
        return ""
    with zipfile.ZipFile(zip_path) as archive:
        return hashlib.sha256(archive.read("raw.gms")).hexdigest()[:12]


def read_solver_meta(container: gt.Container) -> dict[str, str]:
    """The `makroskop_meta` stamp freesolver writes (fingerprint, shock spec, date), or {}."""
    if "makroskop_meta" not in container.data:
        return {}
    records = container.data["makroskop_meta"].records
    if records is None:
        return {}
    return {str(row.iloc[0]): str(row.iloc[1]) for _, row in records.iterrows()}


def scenario_model_version(solver_meta: dict[str, str], current: dict[str, str]) -> dict[str, str]:
    """Which MAKRO version a scenario GDX was solved on.

    A stamped file whose fingerprint matches the current MAKRO checkout gets that
    checkout's name/commit; a stamped file with a different fingerprint is reported
    as unknown-but-different (the app warns); an unstamped file is *assumed* to match.
    """
    stamped = solver_meta.get("fingerprint", "")
    if stamped and stamped == current["fingerprint"]:
        return {**current, "source": "gdx"}
    if stamped:
        return {"name": "anden MAKRO-version", "commit": "", "fingerprint": stamped, "source": "gdx"}
    return {**current, "source": "assumed"}


def sector_labels(container: gt.Container) -> dict[str, str]:
    records = container.data["s_"].records
    labels = {row.iloc[0]: row["element_text"] for _, row in records.iterrows() if row["element_text"]}
    labels["off"] = labels.get("off", "Offentlig sektor")
    return labels


def build_meta(container: gt.Container, makro_root: Path, available_shocks: dict[str, list[str]]) -> dict:
    series_meta = [
        {
            "key": sdef.key, "labelDa": sdef.label_da, "labelEn": sdef.label_en,
            "group": sdef.group, "unit": sdef.unit_da, "devMode": sdef.dev_mode,
            "sector": sdef.selector[0] if sdef.group == "Brancher" else None,
        }
        for sdef in all_series_defs()
    ]
    series_meta += [
        {"key": key, "labelDa": label_da, "labelEn": label_en, "group": group, "unit": unit, "devMode": "pp", "sector": None}
        for key, _, _, label_da, label_en, group, unit in RATIOS
    ]
    return {
        "model": model_version(makro_root),
        "yearStart": YEAR_START,
        "yearEnd": YEAR_END,
        "lastDataYear": 2025,
        "defaultShockYear": 2030,
        "sectors": sector_labels(container),
        "series": series_meta,
        "shocks": [
            {
                "name": shock.name, "labelDa": shock.label_da, "labelEn": shock.label_en,
                "group": shock.group, "available": available_shocks.get(shock.name, []),
            }
            for shock in SHOCKS
        ],
        "variations": [
            {"suffix": suffix, "labelDa": label_da, "labelEn": label_en}
            for suffix, label_da, label_en in VARIATIONS
        ],
    }


def scan_shock_gdx_files(shocks_dir: Path) -> dict[str, list[tuple[str, Path]]]:
    """Map shock name -> [(variation suffix, gdx path)] for files like Bundskat_ufin.gdx."""
    found: dict[str, list[tuple[str, Path]]] = {}
    if not shocks_dir.is_dir():
        return found
    for gdx_path in sorted(shocks_dir.glob("*.gdx")):
        stem = gdx_path.stem
        for shock in SHOCKS:
            for suffix, *_ in VARIATIONS + [("", "", "")]:
                if stem == f"{shock.name}{suffix}":
                    found.setdefault(shock.name, []).append((suffix, gdx_path))
    return found


def write_demo_scenario(out_dir: Path) -> None:
    """Synthetic, clearly-flagged demo so the scenario UI can be exercised without GAMS output."""
    def damped(amplitude: float, persistence: float, delay: int = 0) -> list[float | None]:
        column: list[float | None] = []
        for year in YEARS:
            offset = year - 2030 - delay
            column.append(0.0 if offset < 0 else sig_round(amplitude * (persistence ** offset) * (offset + 1) * math.exp(-0.25 * offset), 4))
        return column

    demo = {
        "shock": "_demo",
        "variation": "",
        "synthetic": True,
        "labelDa": "Syntetisk demo-scenarie (IKKE en MAKRO-beregning)",
        "labelEn": "Synthetic demo scenario (NOT a MAKRO simulation)",
        "hbi": None,
        "deviations": {
            "qBNP": damped(0.35, 0.80), "nL": damped(0.28, 0.78, 1), "qC": damped(0.22, 0.85),
            "qX": damped(-0.15, 0.82, 1), "qM": damped(0.25, 0.80), "qI": damped(0.55, 0.75),
            "pC": damped(0.10, 0.90, 2), "vhW": damped(0.18, 0.90, 2), "pBolig": damped(0.40, 0.72),
            "ledighedsgrad": damped(-0.20, 0.78, 1), "saldo2bnp": damped(-0.45, 0.85),
            "primsaldo2bnp": damped(-0.42, 0.85), "rRenteObl": damped(0.0, 0.0),
        },
    }
    (out_dir / "shocks").mkdir(parents=True, exist_ok=True)
    (out_dir / "shocks" / "_demo.json").write_text(json.dumps(demo), encoding="utf-8")
    print("  wrote shocks/_demo.json (synthetic, flagged)")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--makro-root", type=Path, default=Path(__file__).parent.parent.parent / "MAKRO")
    parser.add_argument("--out", type=Path, default=Path(__file__).parent.parent / "app" / "static" / "data")
    parser.add_argument("--shocks-dir", type=Path, default=Path(__file__).parent / "shock_gdx")
    parser.add_argument("--demo", action="store_true", help="also write a synthetic, flagged demo scenario")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "shocks").mkdir(exist_ok=True)

    print("Reading baseline.gdx ...")
    baseline = open_gdx(args.makro_root / "Model/Gdx/baseline.gdx")
    detrended, columns = extract_baseline(baseline)

    # Solver-produced shock GDXs must be compared against the solver's own unshocked
    # reference (the calibration point), which can differ slightly from baseline.gdx.
    reference_path = args.shocks_dir / "_reference.gdx"
    if reference_path.exists():
        print("Reading solver reference (_reference.gdx) for shock comparisons ...")
        shock_reference = extract_detrended(open_gdx(reference_path))
    else:
        shock_reference = detrended
    (args.out / "baseline.json").write_text(
        json.dumps({"years": YEARS, "series": columns, "indicators": {"rHBI": read_hbi(baseline)}}),
        encoding="utf-8",
    )
    print(f"  wrote baseline.json ({len(columns)} series)")

    current_version = model_version(args.makro_root)
    found = scan_shock_gdx_files(args.shocks_dir)
    available: dict[str, list[str]] = {}
    for shock_name, variants in found.items():
        for suffix, gdx_path in variants:
            print(f"Reading shock {gdx_path.name} ...")
            payload = {"shock": shock_name, "variation": suffix, "synthetic": False,
                       "definition": shock_definition(shock_name, suffix, MODEL_HORIZON_END),
                       **extract_shock(gdx_path, shock_reference)}
            payload["modelVersion"] = scenario_model_version(payload.pop("solverMeta"), current_version)
            if payload["modelVersion"]["source"] == "assumed":
                print(f"  note: {gdx_path.name} carries no solver stamp; assuming {current_version['name']}")
            elif payload["modelVersion"]["fingerprint"] != current_version["fingerprint"]:
                print(f"  WARNING: {gdx_path.name} was solved on a different model "
                      f"(fingerprint {payload['modelVersion']['fingerprint']} != {current_version['fingerprint']})")
            if reference_path.exists():
                # solver scenarios fix pre-window years, so the 2022-evaluated HBI is frozen
                payload["hbi"] = None
            (args.out / "shocks" / f"{shock_name}{suffix}.json").write_text(json.dumps(payload), encoding="utf-8")
            available.setdefault(shock_name, []).append(suffix)

    if args.demo:
        write_demo_scenario(args.out)

    (args.out / "meta.json").write_text(
        json.dumps(build_meta(baseline, args.makro_root, available), ensure_ascii=False),
        encoding="utf-8",
    )
    print("  wrote meta.json")


if __name__ == "__main__":
    main()
