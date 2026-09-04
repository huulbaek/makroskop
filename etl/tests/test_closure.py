"""Tax-reaction closure: DREAM's financed variant as linear equations appended to the system."""

import numpy as np

import freesolver as fs


def synthetic():
    # ids: 0-2 tLukning(2120..2122), 3-5 vtLukning(tot,2120..2122), 6 vOff13Net(2122), 7 vBNP(2122), 8 other
    ids = {
        "tLukning(2120)": 0, "tLukning(2121)": 1, "tLukning(2122)": 2,
        "vtLukning(tot,2120)": 3, "vtLukning(tot,2121)": 4, "vtLukning(tot,2122)": 5,
        "vOff13Net(2122)": 6, "vBNP(2122)": 7, "x(2122)": 8,
    }
    levels = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 400.0, 100.0, 1.0])
    is_fixed = np.array([False, False, False, True, True, True, False, False, True])
    return ids, levels, is_fixed


def test_build_rows_and_unfix_set():
    ids, levels, is_fixed = synthetic()
    extra, unfix = fs.build_tax_reaction(ids, levels, n_vars=9, first_year=2120, last_year=2122)
    assert sorted(unfix.tolist()) == [3, 4, 5]
    assert extra.n == 3
    assert extra.years.tolist() == [2120, 2121, 2122]
    assert extra.names[0] == "closure:tLukning(2120)=tLukning(2122)"
    assert extra.names[2].startswith("closure:vOff13Net(2122)")
    # equality rows: +1 on tLukning(t), -1 on tLukning(last)
    dense = extra.matrix.toarray()
    assert dense[0].tolist() == [1, 0, -1, 0, 0, 0, 0, 0, 0]
    assert dense[1].tolist() == [0, 1, -1, 0, 0, 0, 0, 0, 0]
    # terminal row: vOff13Net - ratio * vBNP with ratio from the reference levels (4.0)
    assert dense[2].tolist() == [0, 0, 0, 0, 0, 0, 1, -4.0, 0]


def test_residuals_vanish_at_reference_and_react_to_moves():
    ids, levels, is_fixed = synthetic()
    extra, _ = fs.build_tax_reaction(ids, levels, n_vars=9, first_year=2120, last_year=2122)
    assert np.allclose(extra.residuals(levels), 0.0)
    x = levels.copy()
    x[0] = 0.02  # tLukning(2120) deviates from the terminal rate
    x[6] = 410.0  # net worth above the reference ratio
    r = extra.residuals(x)
    assert np.isclose(r[0], 0.02) and np.isclose(r[1], 0.0) and np.isclose(r[2], 10.0)


def test_jacobian_restricted_to_free_columns():
    ids, levels, is_fixed = synthetic()
    extra, unfix = fs.build_tax_reaction(ids, levels, n_vars=9, first_year=2120, last_year=2122)
    is_fixed[unfix] = False
    free_ids = np.where(~is_fixed)[0]  # 0..7
    jac = extra.jacobian_free(free_ids).toarray()
    assert jac.shape == (3, 8)
    assert jac[0].tolist() == [1, 0, -1, 0, 0, 0, 0, 0]
    assert jac[2].tolist() == [0, 0, 0, 0, 0, 0, 1, -4.0]


def test_missing_instance_is_an_error():
    ids, levels, _ = synthetic()
    del ids["tLukning(2121)"]
    try:
        fs.build_tax_reaction(ids, levels, n_vars=9, first_year=2120, last_year=2122)
    except SystemExit:
        return
    raise AssertionError("expected SystemExit for a missing instance")


class _FakeSystem:
    """Just enough of freesolver.System for tax_reaction_closure."""

    def __init__(self, levels, is_fixed):
        self.levels = levels
        self.is_fixed = is_fixed
        self.reindexed = False

    def _index_free(self):
        self.reindexed = True


CLOSURE_DICT_TXT = """CNS written by GAMS Convert
Equations 1 to 1
  e1  E_a(2129)
Variables 1 to 8
  x1  tLukning(2127)
  x2  tLukning(2128)
  x3  tLukning(2129)
  x4  vtLukning(tot,2127)
  x5  vtLukning(tot,2128)
  x6  vtLukning(tot,2129)
  x7  vOff13Net(2129)
  x8  vBNP(2129)
"""


def test_closure_starts_in_the_windows_first_year(tmp_path):
    # --from-year is DREAM's shock_year: the window's first solved year, with from_year-1 frozen
    # as DREAM's t0. B_tax_reaction then holds tLukning constant from shock_year (tx0E), so the
    # closure rows must start at from_year itself, not one year later.
    (tmp_path / "dict.txt").write_text(CLOSURE_DICT_TXT, encoding="utf-8")
    levels = np.array([0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 400.0, 100.0])
    is_fixed = np.array([False, False, False, True, True, True, False, False])
    system = _FakeSystem(levels, is_fixed)
    extra = fs.tax_reaction_closure(system, tmp_path, from_year=2127)
    assert extra.years.tolist() == [2127, 2128, 2129]
    assert extra.names[0] == "closure:tLukning(2127)=tLukning(2129)"
    assert system.is_fixed.tolist() == [False] * 8  # all three vtLukning(tot,t) freed
    assert system.reindexed
