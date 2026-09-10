"""Pole j-terms: recomputed from their (dropped) equations after the solve, undefined at a zero stock."""

from pathlib import Path

import numpy as np
import pytest

import freesolver as fs


DICT_TXT = """CNS written by GAMS Convert
Equations 1 to 4
  e1  E_jrUdlAktRenter_portf(Obl,2065)
  e2  E_jrUdlPasOmv_portf(Bank,2065)
  e3  E_jrUdlAktRenter_portf(Obl,2066)
  e4  E_vBNP(2065)
Variables 1 to 6
  x1  jrUdlAktRenter(Obl,2066)
  x2  jrUdlPasOmv(Bank,2065)
  x3  jrUdlAktRenter(Obl,2065)
  x4  jrUdlAktRenter(Obl,2064)
  x5  vBNP(2065)
  x6  jrUdlPasRenter(Obl,2065)
"""


def write_convert_dir(tmp_path: Path) -> Path:
    (tmp_path / "dict.txt").write_text(DICT_TXT, encoding="utf-8")
    return tmp_path


def test_pairs_match_each_equation_to_its_own_jterm(tmp_path: Path) -> None:
    is_fixed = np.zeros(6, dtype=bool)
    pairs = fs.load_pole_jterm_pairs(write_convert_dir(tmp_path), is_fixed)
    # (equation index, variable index), 0-based, paired by "(portf,year)" — not by position
    assert sorted(pairs) == [(0, 2), (1, 1), (2, 0)]


def test_pairs_skip_fixed_jterms(tmp_path: Path) -> None:
    is_fixed = np.zeros(6, dtype=bool)
    is_fixed[1] = True  # jrUdlPasOmv(Bank,2065) exogenous: nothing to drop or recompute
    pairs = fs.load_pole_jterm_pairs(write_convert_dir(tmp_path), is_fixed)
    assert sorted(pairs) == [(0, 2), (2, 0)]


# Synthetic affine "income = (r + jr) * stock / fv" equations on a small x:
#   x = [jr_a, income_a, stock_a, jr_b, income_b, stock_b]; fv = 1.03, r = 0.02
FV, R = 1.03, 0.02


def affine_residual(x: np.ndarray, eq: int) -> float:
    base = 3 * eq
    return float(x[base + 1] - (R + x[base]) * x[base + 2] / FV)


def test_recompute_solves_each_dropped_equation_for_its_jterm() -> None:
    x = np.array([0.0, 20.0, 400.0, 0.0, -5.0, -50.0])
    n_done, undefined = fs.recompute_pole_jterms(affine_residual, [(0, 0), (1, 3)], x)
    assert n_done == 2 and undefined == []
    assert np.isclose(x[0], 20.0 * FV / 400.0 - R)
    assert np.isclose(x[3], -5.0 * FV / -50.0 - R)
    assert np.isclose(affine_residual(x, 0), 0.0) and np.isclose(affine_residual(x, 1), 0.0)
    # nothing else touched
    assert x[[1, 2, 4, 5]].tolist() == [20.0, 400.0, -5.0, -50.0]


def test_recompute_leaves_a_jterm_undefined_below_the_stock_floor() -> None:
    x = np.array([0.5, 20.0, 400.0, 0.5, -5.0, 0.4])  # stock_b = 0.4 mia. kr. < floor
    n_done, undefined = fs.recompute_pole_jterms(affine_residual, [(0, 0), (1, 3)], x, floor=1.0)
    assert n_done == 1 and undefined == [3]
    assert np.isnan(x[3])
    assert np.isclose(affine_residual(x, 0), 0.0)


REAL_SYSTEM = (fs.CACHE_DIR / "system.npz").exists() and (fs.DEFAULT_CONVERT_DIR / "dict.txt").exists()


@pytest.fixture(scope="module")
def real_system():
    if not REAL_SYSTEM:
        pytest.skip("needs etl/cache/system.npz and the convert dump")
    return fs.System()


def test_reference_point_is_a_fixed_point_of_the_recompute(real_system) -> None:
    pairs = fs.load_pole_jterm_pairs(fs.DEFAULT_CONVERT_DIR, real_system.is_fixed)
    assert len(pairs) == 1944
    x = real_system.levels.copy()
    n_done, undefined = fs.recompute_pole_jterms(real_system.residual_one, pairs, x)
    assert n_done == 1944 and undefined == []
    assert np.allclose(x, real_system.levels, rtol=0, atol=1e-8)


def test_perturbed_income_zeroes_the_dropped_equation(real_system) -> None:
    ids = fs.variable_ids(fs.DEFAULT_CONVERT_DIR, {"vUdlAktRenter(Obl,2065)", "jrUdlAktRenter(Obl,2065)"})
    pairs = [(e, v) for e, v in fs.load_pole_jterm_pairs(fs.DEFAULT_CONVERT_DIR, real_system.is_fixed)
             if v == ids["jrUdlAktRenter(Obl,2065)"]]
    assert len(pairs) == 1
    x = real_system.levels.copy()
    x[ids["vUdlAktRenter(Obl,2065)"]] += 1.0  # one mia. kr. more interest income on the same stock
    before = abs(real_system.residual_one(x, pairs[0][0]))
    assert before > 0.5
    fs.recompute_pole_jterms(real_system.residual_one, pairs, x)
    assert abs(real_system.residual_one(x, pairs[0][0])) < 1e-9 * before
    assert x[ids["jrUdlAktRenter(Obl,2065)"]] != real_system.levels[ids["jrUdlAktRenter(Obl,2065)"]]


class _FakeSystem:
    """Just enough of freesolver.System for Window's bookkeeping."""

    def __init__(self, levels, is_fixed, n_eq):
        self.levels = levels
        self.is_fixed = is_fixed
        self.n_eq = n_eq
        self.free_ids = np.where(~is_fixed)[0]


WINDOW_DICT_TXT = """CNS written by GAMS Convert
Equations 1 to 4
  e1  E_jrUdlAktRenter_portf(Obl,2065)
  e2  E_jrUdlAktRenter_portf(Obl,2066)
  e3  E_vBNP(2065)
  e4  E_vBNP(2066)
Variables 1 to 5
  x1  jrUdlAktRenter(Obl,2065)
  x2  jrUdlAktRenter(Obl,2066)
  x3  vBNP(2065)
  x4  vBNP(2066)
  x5  vBNP(2064)
"""


def test_window_keeps_only_the_pole_pairs_it_dropped(tmp_path: Path) -> None:
    (tmp_path / "dict.txt").write_text(WINDOW_DICT_TXT, encoding="utf-8")
    system = _FakeSystem(np.zeros(5), np.array([False, False, False, False, True]), n_eq=4)
    window = fs.Window(system, tmp_path, from_year=2066)
    assert window.pole_pairs == [(1, 1)]  # the 2066 instance; 2065 is before the window
    assert window.eq_sel.tolist() == [3]  # only E_vBNP(2066) is solved
