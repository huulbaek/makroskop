"""Can MKL Pardiso factorize MAKRO's window Jacobian reliably? (makroskop-q2r spike)

    uv run python pardiso_probe.py --from-year 2120 [--perturb 1e-3] [--full]

Builds the permuted, row-equilibrated window Jacobian exactly as make_direct_solver does,
then tries Pardiso with several iparm settings (scaling, matching, pivot perturbation,
refinement) and reports factorization time and the same probe residual make_direct_solver
uses to accept a factorization (< 1e-8). UMFPACK (kvxopt) on the same matrix is the reference.
"""

import argparse
import resource
import time

import numpy as np
from scipy import sparse

import freesolver as fs

VARIANTS = {
    "default": {},
    "scale+match": {11: 1, 13: 1},
    "scale+match+refine2": {11: 1, 13: 1, 8: 2},
    "scale+match+pert1e-8": {11: 1, 13: 1, 10: 8},
    "scale+match+pert1e-8+refine2": {11: 1, 13: 1, 10: 8, 8: 2},
    "scale+match+pert1e-13+refine2": {11: 1, 13: 1, 10: 13, 8: 2},
    "match-only+refine2": {13: 1, 8: 2},
    "pert1e-8+refine10": {10: 8, 8: 10},
    "pert1e-5+refine10": {10: 5, 8: 10},
    "par-ordering+par-factor": {2: 3, 24: 1},
}
# Full control: iparm(1)=1 makes MKL honour every value, so the documented mtype-11 defaults are spelled out.
_EXPLICIT = {1: 1, 2: 2, 4: 0, 5: 0, 6: 0, 8: 0, 10: 13, 11: 1, 13: 1, 18: -1, 19: -1, 21: 0, 24: 0, 25: 0,
             27: 0, 28: 0, 31: 0, 34: 0, 35: 0, 36: 0, 37: 0, 56: 0, 60: 0}
VARIANTS.update({
    "explicit-defaults": dict(_EXPLICIT),
    "x-pert1e-8": {**_EXPLICIT, 10: 8},
    "x-pert1e-6": {**_EXPLICIT, 10: 6},
    "x-pert1e-6+refine10": {**_EXPLICIT, 10: 6, 8: 10},
    "x-refine10": {**_EXPLICIT, 8: 10},
    "x-no-match": {**_EXPLICIT, 13: 0},
    "x-no-scale-no-match": {**_EXPLICIT, 11: 0, 13: 0},
    "x-mindeg": {**_EXPLICIT, 2: 0},
    "x-two-level-factor": {**_EXPLICIT, 24: 1},
    "x-pert1e-5+refine10": {**_EXPLICIT, 10: 5, 8: 10},
    "x-pert1e-7+refine10": {**_EXPLICIT, 10: 7, 8: 10},
})


def rss_gb() -> float:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024**2


def equilibrated(matrix):
    csr = matrix.tocsr()
    magnitude = csr.copy()
    magnitude.data = np.abs(magnitude.data)
    row_max = magnitude.max(axis=1).toarray().ravel()
    scale = np.where(row_max > 0, 1.0 / np.maximum(row_max, 1e-300), 1.0)
    scaled = (sparse.diags(scale) @ csr).tocsr()
    scaled.sort_indices()
    return csr, scaled, scale


def probe(csr, solve, n):
    """(raw relative residual, residual after 3 refinement steps as linear_solve does)."""
    rhs = csr @ np.random.default_rng(3).standard_normal(n)
    norm = np.linalg.norm(rhs) + 1e-300
    sol = solve(rhs)
    raw = float(np.linalg.norm(csr @ sol - rhs) / norm)
    for _ in range(3):
        sol = sol + solve(rhs - csr @ sol)
    return raw, float(np.linalg.norm(csr @ sol - rhs) / norm)


def try_pardiso(name, iparms, csr, scaled, scale, n):
    import pypardiso

    solver = pypardiso.PyPardisoSolver()
    if name == "default":
        print(f"  pypardiso default iparm (1-based nonzero): "
              f"{{{', '.join(f'{i + 1}:{v}' for i, v in enumerate(solver.iparm) if v)}}}", flush=True)
    for i, v in iparms.items():
        solver.set_iparm(i, v)
    t0 = time.time()
    try:
        solver.factorize(scaled)
    except Exception as exc:  # pypardiso raises on Pardiso errors
        print(f"  {name:32s} FAILED: {exc}", flush=True)
        solver.free_memory(everything=True)
        return None
    t_fac = time.time() - t0
    t0 = time.time()
    rel, refined = probe(csr, lambda b: solver.solve(scaled, scale * b), n)
    t_solve = time.time() - t0
    peak = rss_gb()
    ip = solver.iparm  # MKL output iparms (1-based in the docs): 14 perturbed pivots, 15-17 memory KB, 7 refinement steps
    diag = f"perturbed pivots {ip[13]}, refine steps {ip[6]}, mem {max(ip[14], ip[15] + ip[16]) / 1024**2:.1f} GB"
    solver.free_memory(everything=True)
    verdict = "PASS" if rel < 1e-8 else ("rescuable" if refined < 1e-11 else "reject")
    print(f"  {name:32s} factor {t_fac:7.1f}s  solve {t_solve:5.1f}s  probe {rel:9.1e} -> refined {refined:9.1e}  {verdict}  peakRSS {peak:.1f} GB  [{diag}]", flush=True)
    return rel, t_fac


def try_umfpack(csr, scaled, scale, n):
    from kvxopt import matrix as kmatrix, spmatrix, umfpack

    coo = scaled.tocoo()
    a = spmatrix(coo.data, coo.row.astype(np.int64), coo.col.astype(np.int64), (n, n))
    t0 = time.time()
    numeric = umfpack.numeric(a, umfpack.symbolic(a))
    t_fac = time.time() - t0

    def solve(b):
        rhs = kmatrix(scale * b)
        umfpack.solve(a, numeric, rhs)
        return np.asarray(rhs).ravel()

    rel, refined = probe(csr, solve, n)
    print(f"  {'umfpack (reference)':32s} factor {t_fac:7.1f}s  probe {rel:9.1e} -> refined {refined:9.1e}  peakRSS {rss_gb():.1f} GB", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--from-year", type=int, default=2120)
    parser.add_argument("--perturb", type=float, default=0.0)
    parser.add_argument("--variants", default=",".join(VARIANTS))
    parser.add_argument("--skip-umfpack", action="store_true")
    args = parser.parse_args()

    system = fs.System()
    window = fs.Window(system, fs.DEFAULT_CONVERT_DIR, args.from_year)
    x = system.levels.copy()
    if args.perturb > 0:
        rng = np.random.default_rng(42)
        x[window.window_vars] += args.perturb * (np.abs(x[window.window_vars]) + 1e-3) * rng.standard_normal(len(window.window_vars))
    jac = window.jacobian_csc(x)
    jw = jac[window.eq_perm, :][:, window.var_perm].tocsc()
    del jac
    n = jw.shape[0]
    csr, scaled, scale = equilibrated(jw)
    print(f"window from {args.from_year}: {n:,} equations, nnz {csr.nnz:,}, perturb {args.perturb:g}", flush=True)
    for name in args.variants.split(","):
        try_pardiso(name, VARIANTS[name], csr, scaled, scale, n)
    if not args.skip_umfpack:
        try_umfpack(csr, scaled, scale, n)


if __name__ == "__main__":
    main()
