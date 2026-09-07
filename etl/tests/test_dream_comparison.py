"""dream_comparison: MAKROskop pct deviations -> DREAM's units at DREAM's shock size."""

import dream_comparison as dc


REF = dc.RefLevels(employment_thousands=3000.0, export_share=0.8, consumption_share=0.5)


def test_convert_to_dream_units() -> None:
    # employment: pct of 3,000 thousand persons -> thousand persons, then x shock-size factor 2
    assert dc.convert("nL", 0.1, 2.0, REF) == 6.0
    # exports and consumption: pct -> pct-points of GDP via the 2030 shares
    assert dc.convert("qX", 1.0, 2.0, REF) == 1.6
    assert dc.convert("qC", 1.0, 2.0, REF) == 1.0
    # GDP and hourly wages stay in pct
    assert dc.convert("qBNP", 0.5, 2.0, REF) == 1.0
    assert dc.convert("vhW", -0.3, 2.0, REF) == -0.6


def test_row_values_pairs_readings_with_scaled_ours() -> None:
    years = [2029, 2030, 2031, 2032]
    ours = [0.0, 0.5, 1.0, None]  # pct deviations, aligned with `years`
    readings = {"2030": 0.8, "2032": 0.4}
    row = dc.row_values("qBNP", readings, ours, years, scale=2.0, ref=REF, columns=[2030, 2031, 2032])
    assert row["dream"] == {"2030": 0.8, "2031": None, "2032": 0.4}
    assert row["ours"] == {"2030": 1.0, "2031": 2.0, "2032": None}


def test_row_values_never_emits_negative_zero() -> None:
    row = dc.row_values("qBNP", {}, [-0.001], [2030], scale=1.0, ref=REF, columns=[2030])
    assert str(row["ours"]["2030"]) == "0.0"


def test_unknown_series_is_an_error() -> None:
    try:
        dc.convert("pBolig", 1.0, 1.0, REF)
    except KeyError:
        return
    raise AssertionError("expected KeyError for a series without a DREAM unit")
