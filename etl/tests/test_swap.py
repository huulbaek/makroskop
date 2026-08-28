"""find_swap_pairs: DREAM's exo/endo swap (fix the target, free the parameter) on a tiny dict.txt."""

from pathlib import Path

import numpy as np

import freesolver as fs


DICT_TXT = """CNS written by GAMS Convert
Equations 1 to 3
  e1  E_a(2030)
Variables 1 to 8
  x1  snLHh(tot,2030)
  x2  snLHh(14,2030)
  x3  snLHh(15,2030)
  x4  snLHh(16,2030)
  x5  snLHh(15,2031)
  x6  uDeltag(15,2030)
  x7  uDeltag(16,2030)
  x8  uDeltag(15,2031)
"""


def write_convert_dir(tmp_path: Path) -> Path:
    (tmp_path / "dict.txt").write_text(DICT_TXT, encoding="utf-8")
    return tmp_path


def test_pairs_by_domain_keys_and_drops_unpaired(tmp_path: Path) -> None:
    convert_dir = write_convert_dir(tmp_path)
    matched = fs.find_shock_variables_with_years(convert_dir, "snLHh", (2030, 2030))
    assert [v for v, _ in matched] == [0, 1, 2, 3]  # tot, 14, 15, 16
    pairs = fs.find_swap_pairs(convert_dir, matched, "uDeltag")
    # (shock id, endogenised id, year): only ages with a uDeltag partner survive
    assert pairs == [(2, 5, 2030), (3, 6, 2030)]


def test_pairs_respect_year_range(tmp_path: Path) -> None:
    convert_dir = write_convert_dir(tmp_path)
    matched = fs.find_shock_variables_with_years(convert_dir, "snLHh", (2031, 2031))
    assert fs.find_swap_pairs(convert_dir, matched, "uDeltag") == [(4, 7, 2031)]


def test_no_partner_is_an_error(tmp_path: Path) -> None:
    convert_dir = write_convert_dir(tmp_path)
    matched = fs.find_shock_variables_with_years(convert_dir, "snLHh", (2030, 2030))
    try:
        fs.find_swap_pairs(convert_dir, matched, "uh")
    except SystemExit:
        return
    raise AssertionError("expected SystemExit when nothing pairs")


def test_swap_flags() -> None:
    is_fixed = np.array([False, False, True, True])
    fs.apply_swap(is_fixed, fix_ids=np.array([0]), free_ids=np.array([3]))
    assert is_fixed.tolist() == [True, False, True, False]
