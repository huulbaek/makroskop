"""Factorization lifetime: a stale LU must be released BEFORE the next one is built.

A full-horizon LU is ~28 GB; holding the previous one while factorizing the next
peaked at 61 of 62 GB and OOM-killed two Rente_perm attempts (makroskop-xn2).
The toy window below (exp(y) = s, one unknown) is stiff enough that chord
factorizations are dropped and rebuilt both within a Newton run and inside a
continuation stage that entered with a carried LU.
"""

import weakref

import numpy as np
from scipy import sparse

import freesolver as fs


class ToyWindow:
    """exp(y) = s: y is variable 0 (the window's only unknown), s is exogenous variable 1."""

    n_eq_total = 1
    eq_sel = np.array([0])
    eq_perm = np.array([0])
    var_perm = np.array([0])
    window_vars_sorted = np.array([0])

    def residuals(self, x: np.ndarray, out: np.ndarray) -> None:
        out[0] = np.exp(x[0]) - x[1]

    def jacobian_csc(self, x: np.ndarray):
        return sparse.csc_matrix(np.array([[np.exp(x[0]), -1.0]]))


class FactorizationTracker:
    """Stand-in for make_direct_solver that records, at every build, how many of the
    previously built solvers are still alive (weakrefs: no strong reference kept here)."""

    def __init__(self) -> None:
        self.built: list[weakref.ref] = []
        self.stale_at_build: list[int] = []

    def __call__(self, matrix):
        self.stale_at_build.append(sum(1 for ref in self.built if ref() is not None))
        dense = matrix.toarray()

        def solve(b: np.ndarray) -> np.ndarray:
            return np.linalg.solve(dense, b)

        self.built.append(weakref.ref(solve))
        return solve


def test_solve_window_frees_stale_lu_before_rebuilding(monkeypatch) -> None:
    tracker = FactorizationTracker()
    monkeypatch.setattr(fs, "make_direct_solver", tracker)
    window = ToyWindow()
    x = np.array([0.0, 3.0])  # far from the root ln 3: several fresh Jacobians before chord steps

    norm = fs.solve_window(None, window, x, tol=1e-9, max_iter=12, lu_holder=[])

    assert norm < 1e-9 and abs(x[0] - np.log(3.0)) < 1e-8
    assert len(tracker.built) >= 3, "toy problem no longer forces rebuilds"
    assert tracker.stale_at_build == [0] * len(tracker.built)


def test_continuation_stage_does_not_pin_the_carried_lu(monkeypatch) -> None:
    tracker = FactorizationTracker()
    monkeypatch.setattr(fs, "make_direct_solver", tracker)
    carried_and_rebuilt: list[bool] = []
    real_solve_window = fs.solve_window

    def observing_solve_window(*args, lu_holder=None, **kwargs):
        entered_with_lu = bool(lu_holder)
        builds_before = len(tracker.built)
        result = real_solve_window(*args, lu_holder=lu_holder, **kwargs)
        carried_and_rebuilt.append(entered_with_lu and len(tracker.built) > builds_before)
        return result

    monkeypatch.setattr(fs, "solve_window", observing_solve_window)
    window = ToyWindow()
    x = np.array([0.0, 1.0])

    fs.solve_shock(None, window, x, np.array([1]), np.array([3.0]), tol=1e-9)

    assert abs(x[0] - np.log(3.0)) < 1e-8
    assert any(carried_and_rebuilt), "no stage entered with a chord LU and rebuilt it"
    assert tracker.stale_at_build == [0] * len(tracker.built)


class CleanupTracker(FactorizationTracker):
    """Solvers with a backend `cleanup` hook (Pardiso: MKL keeps the LU until told to free it,
    ~8 GB each on the full horizon). Records, at every build, how many earlier solvers were
    dropped without their hook being called."""

    def __init__(self) -> None:
        super().__init__()
        self.cleaned: list[bool] = []
        self.uncleaned_at_build: list[int] = []

    def __call__(self, matrix):
        self.uncleaned_at_build.append(sum(1 for done in self.cleaned if not done))
        solve = super().__call__(matrix)
        index = len(self.cleaned)
        self.cleaned.append(False)

        def cleanup() -> None:
            assert not self.cleaned[index], "cleanup called twice for one factorization"
            self.cleaned[index] = True

        solve.cleanup = cleanup
        return solve


def test_dropped_factorizations_release_backend_memory(monkeypatch) -> None:
    tracker = CleanupTracker()
    monkeypatch.setattr(fs, "make_direct_solver", tracker)
    window = ToyWindow()
    x = np.array([0.0, 1.0])

    fs.solve_shock(None, window, x, np.array([1]), np.array([3.0]), tol=1e-9)

    assert abs(x[0] - np.log(3.0)) < 1e-8
    assert len(tracker.built) >= 3, "toy problem no longer forces rebuilds"
    assert tracker.uncleaned_at_build == [0] * len(tracker.built), "an LU was dropped without cleanup"
    assert all(tracker.cleaned), "the last carried LU was not released when the continuation ended"


def test_solve_window_without_holder_releases_its_lu(monkeypatch) -> None:
    tracker = CleanupTracker()
    monkeypatch.setattr(fs, "make_direct_solver", tracker)
    window = ToyWindow()
    x = np.array([0.0, 3.0])

    fs.solve_window(None, window, x, tol=1e-9, max_iter=12)

    assert all(tracker.cleaned)
