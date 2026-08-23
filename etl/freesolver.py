"""Free (license-less) tooling for MAKRO's GAMS-convert scalar model.

Milestone 1: parse the scalar CNS system from deep_dynamic_calibration.zip
and verify that all ~2.2M equation residuals are ~0 at the file's own
solution point. This validates the parser and evaluator that a future
Newton solver will build on.

Usage (from etl/):
    uv run python freesolver.py parse [--convert-dir DIR]   # one-off, caches to cache/
    uv run python freesolver.py check                        # evaluate residuals, report

The scalar format (GAMS CONVERT output) uses only: + - * / ** ( ),
numbers, xN variable references, and the intrinsics sqr/tanh/exp.
"""

import argparse
import re
import time
from array import array
from pathlib import Path

import numpy as np

CACHE_DIR = Path(__file__).parent / "cache"
DEFAULT_CONVERT_DIR = CACHE_DIR / "convert"  # unzip Model/deep_dynamic_calibration.zip here

# opcodes for the RPN stack machine
OP_VAR, OP_CONST, OP_ADD, OP_SUB, OP_MUL, OP_DIV, OP_POW, OP_NEG, OP_SQR, OP_TANH, OP_EXP = range(11)

FUNCTIONS = {"sqr": OP_SQR, "tanh": OP_TANH, "exp": OP_EXP}
BINARY_OPS = {"+": OP_ADD, "-": OP_SUB, "*": OP_MUL, "/": OP_DIV, "**": OP_POW}
PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2, "**": 4, "u-": 3}

TOKEN_RE = re.compile(
    r"x(\d+)"                                  # variable reference
    r"|(\d+\.?\d*(?:[eE][+-]?\d+)?|\.\d+(?:[eE][+-]?\d+)?)"  # number
    r"|(\*\*|[-+*/()])"                        # operator / paren
    r"|([A-Za-z_][A-Za-z0-9_]*)"               # function name
)


def tokenize(text: str) -> list[tuple[str, str]]:
    tokens: list[tuple[str, str]] = []
    for match in TOKEN_RE.finditer(text):
        var, number, op, name = match.groups()
        if var is not None:
            tokens.append(("var", var))
        elif number is not None:
            tokens.append(("num", number))
        elif op is not None:
            tokens.append(("op", op))
        else:
            tokens.append(("fn", name.lower()))
    return tokens


def to_rpn(tokens: list[tuple[str, str]], code: "array", args: "array", consts: list[float],
           const_index: dict[float, int]) -> None:
    """Shunting-yard straight into the shared code/args streams."""
    op_stack: list[str] = []
    prev_kind = "start"  # start | operand | op | open

    def emit_const(value: float) -> None:
        if value in const_index:
            idx = const_index[value]
        else:
            idx = len(consts)
            consts.append(value)
            const_index[value] = idx
        code.append(OP_CONST)
        args.append(idx)

    def pop_op(op: str) -> None:
        if op == "u-":
            code.append(OP_NEG)
        else:
            code.append(BINARY_OPS[op])
        args.append(0)

    for kind, value in tokens:
        if kind == "var":
            code.append(OP_VAR)
            args.append(int(value) - 1)  # 0-based
            prev_kind = "operand"
        elif kind == "num":
            emit_const(float(value))
            prev_kind = "operand"
        elif kind == "fn":
            op_stack.append(value)
            prev_kind = "op"
        elif value == "(":
            op_stack.append("(")
            prev_kind = "open"
        elif value == ")":
            while op_stack and op_stack[-1] != "(":
                top = op_stack.pop()
                if top in FUNCTIONS:
                    code.append(FUNCTIONS[top])
                    args.append(0)
                else:
                    pop_op(top)
            if not op_stack:
                raise ValueError("unbalanced parentheses")
            op_stack.pop()  # remove "("
            while op_stack and op_stack[-1] in FUNCTIONS:
                code.append(FUNCTIONS[op_stack.pop()])
                args.append(0)
            prev_kind = "operand"
        else:  # binary operator or unary minus
            op = value
            if op == "-" and prev_kind in ("start", "op", "open"):
                op_stack.append("u-")  # prefix operator: pops nothing
                prev_kind = "op"
                continue
            if op == "+" and prev_kind in ("start", "op", "open"):
                prev_kind = "op"
                continue  # unary plus: no-op
            while op_stack and op_stack[-1] not in ("(",) and op_stack[-1] not in FUNCTIONS:
                top = op_stack[-1]
                top_prec = PRECEDENCE[top]
                cur_prec = PRECEDENCE[op]
                right_assoc = op == "**"
                if top_prec > cur_prec or (top_prec == cur_prec and not right_assoc):
                    pop_op(op_stack.pop())
                else:
                    break
            op_stack.append(op)
            prev_kind = "op"
    while op_stack:
        top = op_stack.pop()
        if top == "(":
            raise ValueError("unbalanced parentheses")
        if top in FUNCTIONS:
            code.append(FUNCTIONS[top])
            args.append(0)
        else:
            pop_op(top)


EQ_START_RE = re.compile(r"^e(\d+)\.\.")


def cmd_parse(convert_dir: Path) -> None:
    gams_path = convert_dir / "gams.gms"
    started = time.time()
    code = array("b")
    args = array("i")
    consts: list[float] = []
    const_index: dict[float, int] = {}
    eq_offsets = array("q", [0])
    rhs_values = array("d")

    n_vars = 5_836_546
    levels = np.zeros(n_vars, dtype=np.float64)
    is_fixed = np.zeros(n_vars, dtype=bool)
    suffix_counts: dict[str, int] = {}

    statement_parts: list[str] = []
    in_equations = False
    n_equations = 0

    def finish_equation(statement: str) -> None:
        nonlocal n_equations
        body = statement.split("..", 1)[1]
        lhs_text, rhs_text = body.split("=E=")
        rhs_text = rhs_text.rstrip(";").strip()
        to_rpn(tokenize(lhs_text), code, args, consts, const_index)
        rhs_values.append(float(rhs_text))
        eq_offsets.append(len(code))
        n_equations += 1
        if n_equations % 200_000 == 0:
            print(f"  {n_equations:,} equations, {len(code):,} ops, {time.time() - started:.0f}s", flush=True)

    with gams_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not in_equations:
                if EQ_START_RE.match(line):
                    in_equations = True
                else:
                    continue
            if line[0] == "*":  # comment: '*' in column 1 only (indented '*' is multiplication)
                continue
            stripped = line.strip()
            if not stripped:
                continue
            if stripped[0] in "xe" and "." in stripped.split(" ", 1)[0] and "=" in stripped:
                # bounds/levels/marginals section: xN.suffix = value; or eN.m = value;
                head, _, value_text = stripped.partition("=")
                name, _, suffix = head.strip().partition(".")
                if suffix in ("fx", "l", "lo", "up", "stage", "m", "scale") and name[1:].isdigit():
                    suffix_counts[name[0] + "." + suffix] = suffix_counts.get(name[0] + "." + suffix, 0) + 1
                    if name[0] == "x" and suffix in ("fx", "l"):
                        index = int(name[1:]) - 1
                        levels[index] = float(value_text.strip().rstrip(";"))
                        if suffix == "fx":
                            is_fixed[index] = True
                    continue
            if stripped.startswith("Model") or stripped.startswith("Solve") or stripped.startswith("m."):
                continue
            statement_parts.append(stripped)
            if stripped.endswith(";"):
                finish_equation(" ".join(statement_parts))
                statement_parts.clear()

    print(f"parsed {n_equations:,} equations, {len(code):,} ops, {len(consts):,} unique consts")
    print(f"suffix lines: {suffix_counts}")

    CACHE_DIR.mkdir(exist_ok=True)
    np.savez_compressed(
        CACHE_DIR / "system.npz",
        code=np.array(code, dtype=np.int8),
        args=np.array(args, dtype=np.int32),
        consts=np.array(consts, dtype=np.float64),
        eq_offsets=np.array(eq_offsets, dtype=np.int64),
        rhs=np.array(rhs_values, dtype=np.float64),
        levels=levels,
        is_fixed=is_fixed,
    )
    print(f"cached to {CACHE_DIR / 'system.npz'} in {time.time() - started:.0f}s total")


def make_kernel():
    import numba

    @numba.njit(cache=True, fastmath=False)
    def evaluate(code, args, consts, eq_offsets, rhs, x, out):
        stack = np.empty(4096, dtype=np.float64)
        for eq in range(len(rhs)):
            sp = -1
            for pc in range(eq_offsets[eq], eq_offsets[eq + 1]):
                op = code[pc]
                if op == 0:  # VAR
                    sp += 1
                    stack[sp] = x[args[pc]]
                elif op == 1:  # CONST
                    sp += 1
                    stack[sp] = consts[args[pc]]
                elif op == 2:
                    stack[sp - 1] = stack[sp - 1] + stack[sp]; sp -= 1
                elif op == 3:
                    stack[sp - 1] = stack[sp - 1] - stack[sp]; sp -= 1
                elif op == 4:
                    stack[sp - 1] = stack[sp - 1] * stack[sp]; sp -= 1
                elif op == 5:
                    stack[sp - 1] = stack[sp - 1] / stack[sp]; sp -= 1
                elif op == 6:
                    stack[sp - 1] = stack[sp - 1] ** stack[sp]; sp -= 1
                elif op == 7:
                    stack[sp] = -stack[sp]
                elif op == 8:
                    stack[sp] = stack[sp] * stack[sp]
                elif op == 9:
                    stack[sp] = np.tanh(stack[sp])
                else:
                    stack[sp] = np.exp(stack[sp])
            out[eq] = stack[0] - rhs[eq]
        return out

    return evaluate


def make_jacobian_kernel():
    import numba

    @numba.njit(cache=True, parallel=True, fastmath=False)
    def jacobian(code, args, consts, eq_offsets, x, entry_offsets, out_cols, out_vals):
        """Reverse-mode AD per equation (RPN is a tree: children precede parents).

        Writes (column, d res/d x_col) pairs for every VAR leaf, duplicates included,
        into the slice [entry_offsets[eq], entry_offsets[eq+1]) of out_cols/out_vals.
        """
        for eq in numba.prange(len(eq_offsets) - 1):
            start = eq_offsets[eq]
            n_ops = eq_offsets[eq + 1] - start
            values = np.empty(n_ops, dtype=np.float64)
            child_l = np.full(n_ops, -1, dtype=np.int32)
            child_r = np.full(n_ops, -1, dtype=np.int32)
            adjoint = np.zeros(n_ops, dtype=np.float64)
            idx_stack = np.empty(512, dtype=np.int32)
            sp = -1
            for k in range(n_ops):
                op = code[start + k]
                if op == 0:  # VAR
                    values[k] = x[args[start + k]]
                    sp += 1
                    idx_stack[sp] = k
                elif op == 1:  # CONST
                    values[k] = consts[args[start + k]]
                    sp += 1
                    idx_stack[sp] = k
                elif op <= 6:  # binary
                    right = idx_stack[sp]; sp -= 1
                    left = idx_stack[sp]
                    child_l[k] = left
                    child_r[k] = right
                    a = values[left]; b = values[right]
                    if op == 2:
                        values[k] = a + b
                    elif op == 3:
                        values[k] = a - b
                    elif op == 4:
                        values[k] = a * b
                    elif op == 5:
                        values[k] = a / b
                    else:
                        values[k] = a ** b
                    idx_stack[sp] = k
                else:  # unary
                    child = idx_stack[sp]
                    child_l[k] = child
                    v = values[child]
                    if op == 7:
                        values[k] = -v
                    elif op == 8:
                        values[k] = v * v
                    elif op == 9:
                        values[k] = np.tanh(v)
                    else:
                        values[k] = np.exp(v)
                    idx_stack[sp] = k
            # backward sweep: parents come after children in postfix order
            adjoint[n_ops - 1] = 1.0
            write = entry_offsets[eq]
            for k in range(n_ops - 1, -1, -1):
                op = code[start + k]
                a = adjoint[k]
                if op == 0:  # VAR leaf: emit entry
                    out_cols[write] = args[start + k]
                    out_vals[write] = a
                    write += 1
                elif op == 1:
                    pass
                elif op <= 6:
                    left = child_l[k]; right = child_r[k]
                    vl = values[left]; vr = values[right]
                    if op == 2:  # +
                        adjoint[left] += a
                        adjoint[right] += a
                    elif op == 3:  # -
                        adjoint[left] += a
                        adjoint[right] -= a
                    elif op == 4:  # *
                        adjoint[left] += a * vr
                        adjoint[right] += a * vl
                    elif op == 5:  # /
                        adjoint[left] += a / vr
                        adjoint[right] -= a * values[k] / vr
                    else:  # ** : d/dl = r*l^(r-1), d/dr = v*ln(l)
                        if vl != 0.0:
                            adjoint[left] += a * vr * values[k] / vl
                        if vl > 0.0:
                            adjoint[right] += a * values[k] * np.log(vl)
                else:
                    child = child_l[k]
                    if op == 7:
                        adjoint[child] -= a
                    elif op == 8:
                        adjoint[child] += 2.0 * values[child] * a
                    elif op == 9:
                        adjoint[child] += a * (1.0 - values[k] * values[k])
                    else:  # exp
                        adjoint[child] += a * values[k]

    return jacobian


def make_single_eval():
    import numba

    @numba.njit(cache=True, fastmath=False)
    def evaluate_one(code, args, consts, eq_offsets, rhs, x, eq):
        stack = np.empty(4096, dtype=np.float64)
        sp = -1
        for pc in range(eq_offsets[eq], eq_offsets[eq + 1]):
            op = code[pc]
            if op == 0:
                sp += 1; stack[sp] = x[args[pc]]
            elif op == 1:
                sp += 1; stack[sp] = consts[args[pc]]
            elif op == 2:
                stack[sp - 1] = stack[sp - 1] + stack[sp]; sp -= 1
            elif op == 3:
                stack[sp - 1] = stack[sp - 1] - stack[sp]; sp -= 1
            elif op == 4:
                stack[sp - 1] = stack[sp - 1] * stack[sp]; sp -= 1
            elif op == 5:
                stack[sp - 1] = stack[sp - 1] / stack[sp]; sp -= 1
            elif op == 6:
                stack[sp - 1] = stack[sp - 1] ** stack[sp]; sp -= 1
            elif op == 7:
                stack[sp] = -stack[sp]
            elif op == 8:
                stack[sp] = stack[sp] * stack[sp]
            elif op == 9:
                stack[sp] = np.tanh(stack[sp])
            else:
                stack[sp] = np.exp(stack[sp])
        return stack[0] - rhs[eq]

    return evaluate_one


class System:
    def __init__(self) -> None:
        data = np.load(CACHE_DIR / "system.npz")
        self.code = data["code"]
        self.args = data["args"]
        self.consts = data["consts"]
        self.eq_offsets = data["eq_offsets"]
        self.rhs = data["rhs"]
        self.levels = data["levels"]
        self.is_fixed = data["is_fixed"]
        self.n_eq = len(self.rhs)
        self.free_ids = np.where(~self.is_fixed)[0]
        self.free_index = np.full(len(self.levels), -1, dtype=np.int64)
        self.free_index[self.free_ids] = np.arange(len(self.free_ids))
        var_counts = np.add.reduceat((self.code == OP_VAR).astype(np.int64), self.eq_offsets[:-1])
        self.entry_offsets = np.zeros(self.n_eq + 1, dtype=np.int64)
        np.cumsum(var_counts, out=self.entry_offsets[1:])
        self._jac_kernel = make_jacobian_kernel()
        self._eval_kernel = make_kernel()

    def residuals(self, x: np.ndarray, out: np.ndarray) -> np.ndarray:
        self._eval_kernel(self.code, self.args, self.consts, self.eq_offsets, self.rhs, x, out)
        return out

    def jacobian_csc(self, x: np.ndarray):
        """Sparse Jacobian restricted to free-variable columns, duplicates summed."""
        from scipy import sparse

        total = self.entry_offsets[-1]
        cols = np.empty(total, dtype=np.int32)
        vals = np.empty(total, dtype=np.float64)
        self._jac_kernel(self.code, self.args, self.consts, self.eq_offsets, x,
                         self.entry_offsets, cols, vals)
        rows = np.repeat(
            np.arange(self.n_eq, dtype=np.int32), np.diff(self.entry_offsets).astype(np.int64)
        )
        keep = ~self.is_fixed[cols]
        matrix = sparse.coo_matrix(
            (vals[keep], (rows[keep], self.free_index[cols[keep]])),
            shape=(self.n_eq, self.n_eq),
        )
        return matrix.tocsc()


def cmd_jacobian() -> None:
    system = System()
    x = system.levels.copy()
    started = time.time()
    jac = system.jacobian_csc(x)
    build_time = time.time() - started
    print(f"jacobian: {system.n_eq:,} x {system.n_eq:,}, nnz = {jac.nnz:,} "
          f"(raw entries incl. fixed: {system.entry_offsets[-1]:,}), built in {build_time:.1f}s")

    # finite-difference spot check on random structural nonzeros
    evaluate_one = make_single_eval()
    rng = np.random.default_rng(7)
    coo = jac.tocoo()
    sample = rng.choice(coo.nnz, size=1500, replace=False)
    worst = 0.0
    checked = 0
    skipped_small = 0
    for entry in sample:
        eq = int(coo.row[entry])
        var = int(system.free_ids[coo.col[entry]])
        analytic = coo.data[entry]
        h = 1e-6 * (1.0 + abs(x[var]))
        x[var] += h
        up = evaluate_one(system.code, system.args, system.consts, system.eq_offsets, system.rhs, x, eq)
        x[var] -= 2 * h
        down = evaluate_one(system.code, system.args, system.consts, system.eq_offsets, system.rhs, x, eq)
        x[var] += h
        fd = (up - down) / (2 * h)
        scale = max(abs(analytic), abs(fd))
        if scale < 1e-10:
            skipped_small += 1
            continue
        rel = abs(analytic - fd) / scale
        worst = max(worst, rel)
        checked += 1
    print(f"FD check: {checked} entries, worst rel error = {worst:.2e} "
          f"({skipped_small} near-zero entries skipped)")


def swap_used_gb() -> float:
    import subprocess

    text = subprocess.run(["sysctl", "-n", "vm.swapusage"], capture_output=True, text=True).stdout
    used = text.split("used =")[1].split("M")[0].strip().replace(",", ".")
    return float(used) / 1024


def cmd_lutest(methods: tuple[str, ...], convert_dir: Path, from_year: int = 2022) -> None:
    """Factorize the year-sorted Jacobian with each candidate in a killable subprocess.

    Guards: child RSS cap AND total swap growth (RSS alone hides swapped-out pages
    — the flaw that let the first run freeze this 16GB machine).
    """
    import subprocess
    import sys

    system = System()
    jac = system.jacobian_csc(system.levels)
    print(f"year-sorting rows and columns (window: year >= {from_year}) ...", flush=True)
    eq_year, var_year = load_years(convert_dir, system.n_eq, len(system.levels))
    eq_sel = np.where(eq_year >= from_year)[0]
    free_year = var_year[system.free_ids]
    var_sel = np.where(free_year >= from_year)[0]
    row_perm = eq_sel[np.argsort(eq_year[eq_sel], kind="stable")]
    col_perm = var_sel[np.argsort(free_year[var_sel], kind="stable")]
    jac = jac[row_perm, :][:, col_perm].tocsc()
    sorted_years = np.sort(eq_year[eq_sel])
    boundaries = np.searchsorted(sorted_years, np.arange(from_year, 2131))
    CACHE_DIR.mkdir(exist_ok=True)
    np.savez(CACHE_DIR / "lutest.npz", data=jac.data, indices=jac.indices,
             indptr=jac.indptr, n=np.int64(jac.shape[0]), year_offsets=boundaries)
    print(f"jacobian saved (year-sorted): n = {jac.shape[0]:,}, nnz = {jac.nnz:,}", flush=True)

    for method in methods:
        swap_start = swap_used_gb()
        child = subprocess.Popen(
            [sys.executable, __file__, "_lu_child", "--lu-method", method],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
        )
        peak_rss = 0.0
        peak_swap = 0.0
        reason = ""
        while child.poll() is None:
            probe = subprocess.run(["ps", "-o", "rss=", "-p", str(child.pid)],
                                   capture_output=True, text=True)
            if probe.stdout.strip():
                peak_rss = max(peak_rss, int(probe.stdout.strip()) / 1048576)
            peak_swap = max(peak_swap, swap_used_gb() - swap_start)
            if peak_rss > 8.5:
                reason = f"RSS {peak_rss:.1f}GB over cap"
            elif peak_swap > 2.5:
                reason = f"swap grew {peak_swap:.1f}GB"
            if reason:
                child.kill()
                print(f"{method}: KILLED — {reason}", flush=True)
                break
            time.sleep(0.5)
        else:
            output = (child.stdout.read() if child.stdout else "").strip()
            print(f"{method}: exit {child.returncode}, peak RSS {peak_rss:.1f}GB, "
                  f"swap +{peak_swap:.1f}GB — {output}", flush=True)


def cmd_lu_child(method: str) -> None:
    from scipy import sparse

    data = np.load(CACHE_DIR / "lutest.npz")
    n = int(data["n"])
    jac = sparse.csc_matrix((data["data"], data["indices"], data["indptr"]), shape=(n, n))
    rng = np.random.default_rng(1)
    x_true = rng.standard_normal(n)
    b = jac @ x_true

    t0 = time.time()
    if method == "ilu":
        from scipy.sparse.linalg import spilu, lgmres, LinearOperator
        ilu = spilu(jac, fill_factor=10.0, drop_tol=1e-5)
        t1 = time.time()
        precond = LinearOperator(jac.shape, ilu.solve)
        iterations = [0]
        x, info = lgmres(jac, b, M=precond, rtol=1e-10, maxiter=200,
                         callback=lambda _: iterations.__setitem__(0, iterations[0] + 1))
        t2 = time.time()
        rel_res = np.linalg.norm(jac @ x - b) / np.linalg.norm(b)
        print(f"ilu-factor {t1 - t0:.1f}s, lgmres {t2 - t1:.1f}s, info {info}, "
              f"iters {iterations[0]}, lin res {rel_res:.2e}, "
              f"sol err {np.abs(x - x_true).max() / np.abs(x_true).max():.2e}")
        return
    elif method in ("blockgs", "blockilu", "blockfgs"):
        from scipy.sparse.linalg import splu, spilu, lgmres, LinearOperator
        jac_csr = jac.tocsr()
        offsets = data["year_offsets"]
        blocks = []
        for i in range(len(offsets) - 1):
            lo, hi = int(offsets[i]), int(offsets[i + 1])
            if hi <= lo:
                continue
            diag = jac[lo:hi, lo:hi].tocsc()
            if method == "blockgs":
                factor = splu(diag)
            else:
                try:
                    factor = spilu(diag, fill_factor=6.0, drop_tol=1e-6)
                except RuntimeError:  # singular ILU pivot: fall back to exact LU for this block
                    factor = splu(diag)
            lower = jac_csr[lo:hi, :lo].tocsr() if (method == "blockfgs" and lo > 0) else None
            blocks.append((lo, hi, factor, lower))
        t1 = time.time()

        if method == "blockfgs":
            def block_solve(v):
                out = np.zeros_like(v)
                for lo, hi, factor, lower in blocks:
                    rhs = v[lo:hi].copy()
                    if lower is not None:
                        rhs -= lower @ out[:lo]
                    out[lo:hi] = factor.solve(rhs)
                return out
        else:
            def block_solve(v):
                out = np.empty_like(v)
                for lo, hi, factor, _ in blocks:
                    out[lo:hi] = factor.solve(v[lo:hi])
                return out

        precond = LinearOperator(jac.shape, block_solve)
        iterations = [0]
        x, info = lgmres(jac, b, M=precond, rtol=1e-10, maxiter=300,
                         callback=lambda _: iterations.__setitem__(0, iterations[0] + 1))
        t2 = time.time()
        rel_res = np.linalg.norm(jac @ x - b) / np.linalg.norm(b)
        print(f"block-factor {t1 - t0:.1f}s ({len(blocks)} year blocks), lgmres {t2 - t1:.1f}s, "
              f"info {info}, iters {iterations[0]}, lin res {rel_res:.2e}, "
              f"sol err {np.abs(x - x_true).max() / np.abs(x_true).max():.2e}")
        return
    elif method.startswith("splu"):
        from scipy.sparse.linalg import splu
        spec = "NATURAL" if method == "splu-natural" else "COLAMD"
        lu = splu(jac, permc_spec=spec)
        t1 = time.time()
        x = lu.solve(b)
        t2 = time.time()
    else:
        from kvxopt import matrix, spmatrix, umfpack, klu
        coo = jac.tocoo()
        a = spmatrix(coo.data, coo.row.astype(np.int64), coo.col.astype(np.int64), (n, n))
        rhs = matrix(b)
        module = umfpack if method == "umfpack" else klu
        if method == "umfpack":
            symbolic = module.symbolic(a)
            numeric = module.numeric(a, symbolic)
            t1 = time.time()
            module.solve(a, numeric, rhs)
        else:
            symbolic = module.symbolic(a)
            numeric = module.numeric(a, symbolic)
            t1 = time.time()
            module.solve(a, symbolic, numeric, rhs)
        t2 = time.time()
        x = np.array(rhs).ravel()

    err = np.abs(x - x_true).max() / max(1.0, np.abs(x_true).max())
    print(f"factor {t1 - t0:.1f}s, solve {t2 - t1:.1f}s, rel err {err:.2e}")


YEAR_RE = re.compile(r"\b(19|20|21)\d\d\b")


def load_years(convert_dir: Path, n_eq: int, n_var: int) -> tuple[np.ndarray, np.ndarray]:
    """Year of each equation/variable instance from dict.txt (0 = no year found)."""
    eq_year = np.zeros(n_eq, dtype=np.int16)
    var_year = np.zeros(n_var, dtype=np.int16)
    section = ""
    with (convert_dir / "dict.txt").open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("Equations "):
                section = "e"
                continue
            if line.startswith("Variables "):
                section = "x"
                continue
            if not section:
                continue
            parts = line.split()
            if len(parts) < 2 or not parts[0][1:].isdigit():
                continue
            matches = list(YEAR_RE.finditer(parts[1]))
            if not matches:
                continue
            # take the LAST year in the name (index years come last, e.g. name(a,2044))
            year = int(matches[-1].group(0))
            index = int(parts[0][1:]) - 1
            if section == "e" and parts[0][0] == "e":
                eq_year[index] = year
            elif section == "x" and parts[0][0] == "x":
                var_year[index] = year
    return eq_year, var_year


def cmd_structure(convert_dir: Path) -> None:
    """Measure the year-bandwidth of the Jacobian: is it block-banded in time?"""
    system = System()
    print("scanning dict.txt for years ...", flush=True)
    eq_year, var_year = load_years(convert_dir, system.n_eq, len(system.levels))
    print(f"  equations with a year: {(eq_year > 0).sum():,} / {system.n_eq:,}")
    print(f"  variables with a year: {(var_year > 0).sum():,} / {len(var_year):,}")

    # per-year squareness (free variables vs equations)
    free_years = var_year[system.free_ids]
    years = np.arange(2022, 2130)
    eq_counts = np.array([(eq_year == y).sum() for y in years])
    var_counts = np.array([(free_years == y).sum() for y in years])
    print(f"  eqs/year: min {eq_counts.min():,} max {eq_counts.max():,}; "
          f"free vars/year: min {var_counts.min():,} max {var_counts.max():,}")
    print(f"  years where counts differ: {(eq_counts != var_counts).sum()} "
          f"(total mismatch {np.abs(eq_counts - var_counts).sum():,})")
    print(f"  no-year equations: {(eq_year == 0).sum():,}, no-year free vars: {(free_years == 0).sum():,}")

    print("building jacobian ...", flush=True)
    jac = system.jacobian_csc(system.levels).tocoo()
    row_year = eq_year[jac.row]
    col_year = var_year[system.free_ids[jac.col]]
    valid = (row_year > 0) & (col_year > 0)
    delta = (col_year[valid].astype(np.int32) - row_year[valid].astype(np.int32))
    print(f"nonzeros with both years: {valid.sum():,} / {jac.nnz:,}")
    for width in (0, 1, 2, 3, 5, 10):
        share = (np.abs(delta) <= width).sum() / len(delta)
        print(f"  |year(var) - year(eq)| <= {width}: {share:.4%}")
    print(f"  max lead (var after eq): {delta.max()}, max lag: {delta.min()}")

    # who creates long-range coupling?
    far = np.abs(delta) > 2
    far_rows = jac.row[valid][far]
    unique_far_eqs, far_counts = np.unique(far_rows, return_counts=True)
    print(f"long-range entries (|dy|>2): {far.sum():,} across {len(unique_far_eqs):,} equations")
    sample = unique_far_eqs[np.argsort(-far_counts)][:12]
    names = equation_names(convert_dir, {int(e) + 1 for e in sample})
    print("worst long-range equations:")
    for eq in sample:
        name = names.get(int(eq) + 1, "?")
        print(f"  e{int(eq) + 1:<9} {name.split('(')[0]:<40} entries: {far_counts[unique_far_eqs == eq][0]:,}")

    # equations/columns with no year are also border candidates
    no_year_eqs = (eq_year == 0).sum()
    print(f"border upper bound: {len(unique_far_eqs) + no_year_eqs:,} equations "
          f"of {system.n_eq:,} ({(len(unique_far_eqs) + no_year_eqs) / system.n_eq:.3%})")


class BlockPreconditioner:
    """Symmetric block-Gauss-Seidel over year blocks with per-block (I)LU diagonal solves.

    Forward sweep captures lag couplings, backward sweep the forward-looking leads.
    """

    def __init__(self, jac_sorted, year_offsets: np.ndarray, exact: bool = False):
        from scipy.sparse.linalg import splu, spilu

        jac_csr = jac_sorted.tocsr()
        n = jac_sorted.shape[0]
        self.blocks = []
        self.exact_fallbacks = 0
        for i in range(len(year_offsets) - 1):
            lo, hi = int(year_offsets[i]), int(year_offsets[i + 1])
            if hi <= lo:
                continue
            diag = jac_sorted[lo:hi, lo:hi].tocsc()
            if exact:
                factor = splu(diag)
            else:
                try:
                    factor = spilu(diag, fill_factor=6.0, drop_tol=1e-6)
                except RuntimeError:
                    factor = splu(diag)
                    self.exact_fallbacks += 1
            lower = jac_csr[lo:hi, :lo].tocsr() if lo > 0 else None
            upper = jac_csr[lo:hi, hi:].tocsr() if hi < n else None
            self.blocks.append((lo, hi, factor, lower, upper))

    def solve(self, v: np.ndarray) -> np.ndarray:
        out = np.zeros_like(v)
        for lo, hi, factor, lower, _ in self.blocks:          # forward sweep (lags exact)
            rhs = v[lo:hi].copy()
            if lower is not None:
                rhs -= lower @ out[:lo]
            out[lo:hi] = factor.solve(rhs)
        for lo, hi, factor, lower, upper in reversed(self.blocks):  # backward sweep (leads)
            rhs = v[lo:hi].copy()
            if lower is not None:
                rhs -= lower @ out[:lo]
            if upper is not None:
                rhs -= upper @ out[hi:]
            out[lo:hi] = factor.solve(rhs)
        return out


def solve_linear(jac_sorted, rhs: np.ndarray, year_offsets: np.ndarray,
                 rtol: float = 1e-8, exact_blocks: bool = False,
                 verbose: bool = True) -> tuple[np.ndarray, int, int]:
    """Preconditioned LGMRES step solve; returns (solution, info, outer iterations)."""
    from scipy.sparse.linalg import LinearOperator, lgmres

    t0 = time.time()
    precond = BlockPreconditioner(jac_sorted, year_offsets, exact=exact_blocks)
    if verbose:
        kind = "exact LU" if exact_blocks else f"ILU ({precond.exact_fallbacks} exact fallbacks)"
        print(f"    preconditioner: {len(precond.blocks)} year blocks, {kind}, "
              f"{time.time() - t0:.1f}s", flush=True)
    operator = LinearOperator(jac_sorted.shape, precond.solve)
    rhs_norm = np.linalg.norm(rhs)
    iterations = [0]

    def callback(xk: np.ndarray) -> None:
        iterations[0] += 1
        if verbose and iterations[0] % 5 == 0:
            rel = np.linalg.norm(jac_sorted @ xk - rhs) / rhs_norm
            print(f"    lgmres outer {iterations[0]}: rel res {rel:.2e}", flush=True)

    solution, info = lgmres(jac_sorted, rhs, M=operator, rtol=rtol, maxiter=60,
                            callback=callback)
    return solution, info, iterations[0]


def cmd_newton(perturb: float, max_iter: int, tol: float, from_year: int, convert_dir: Path) -> None:
    system = System()
    print(f"window: equations/variables with year >= {from_year}")
    eq_year, var_year = load_years(convert_dir, system.n_eq, len(system.levels))
    eq_sel = np.where(eq_year >= from_year)[0]
    free_year = var_year[system.free_ids]
    var_sel = np.where(free_year >= from_year)[0]        # indices into free_ids
    window_vars = system.free_ids[var_sel]               # raw variable ids
    assert len(eq_sel) == len(var_sel), (len(eq_sel), len(var_sel))
    print(f"window system: {len(eq_sel):,} equations/unknowns "
          f"({(2130 - from_year)} years of {system.n_eq:,} total)")

    # year-sorted permutations within the window
    eq_perm = eq_sel[np.argsort(eq_year[eq_sel], kind="stable")]
    var_perm = var_sel[np.argsort(free_year[var_sel], kind="stable")]
    sorted_years = np.sort(eq_year[eq_sel])
    year_offsets = np.searchsorted(sorted_years, np.arange(from_year, 2131))
    window_vars_sorted = system.free_ids[var_perm]
    n_years = 2130 - from_year
    exact_blocks = n_years <= 30  # ~65MB LU per year block: exact only for small windows
    direct = n_years <= 12  # direct splu fits ~3.5GB at 10 years on this machine

    x = system.levels.copy()
    rng = np.random.default_rng(42)
    if perturb > 0:
        noise = perturb * (np.abs(x[window_vars]) + 1e-3) * rng.standard_normal(len(window_vars))
        x[window_vars] += noise
        print(f"perturbed {len(window_vars):,} window variables, relative scale {perturb:g}")

    residual_full = np.empty(system.n_eq)
    system.residuals(x, residual_full)
    norm = np.abs(residual_full[eq_sel]).max()
    print(f"start: ||r||_inf = {norm:.3e}")

    for iteration in range(1, max_iter + 1):
        t0 = time.time()
        jac = system.jacobian_csc(x)                     # full free-column jacobian
        jac_window = jac[eq_perm, :][:, var_perm].tocsc()
        t1 = time.time()
        print(f"  iter {iteration}: jacobian {t1 - t0:.1f}s, window nnz {jac_window.nnz:,}", flush=True)
        rhs = -residual_full[eq_perm]
        if direct:
            from scipy.sparse.linalg import splu
            lu = splu(jac_window)
            dx = lu.solve(rhs)
            dx += lu.solve(rhs - jac_window @ dx)  # one step of iterative refinement
            gmres_iters = 0
        else:
            dx, info, gmres_iters = solve_linear(jac_window, rhs, year_offsets,
                                                 exact_blocks=exact_blocks)
            if info != 0:
                print(f"  WARNING: lgmres info={info} after {gmres_iters} iterations")
        t2 = time.time()

        alpha = 1.0
        for _ in range(8):
            x_try = x.copy()
            x_try[window_vars_sorted] += alpha * dx
            system.residuals(x_try, residual_full)
            trial_norm = np.abs(residual_full[eq_sel]).max()
            if np.isfinite(trial_norm) and trial_norm < norm:
                break
            alpha *= 0.5
        else:
            print("  line search failed to reduce ||r||; stopping")
            break

        x = x_try
        norm = trial_norm
        solver_note = "splu" if direct else f"lgmres/{gmres_iters}"
        print(f"iter {iteration}: ||r||_inf = {norm:.3e}  ||dx||_inf = {np.abs(dx).max():.3e}  "
              f"alpha = {alpha}  (jac {t1 - t0:.1f}s, {solver_note} {t2 - t1:.1f}s)", flush=True)
        if norm < tol:
            break

    recovery = np.abs(x[window_vars] - system.levels[window_vars])
    denom = np.abs(system.levels[window_vars]) + 1e-8
    print(f"final ||r||_inf = {norm:.3e}")
    print(f"recovery vs original solution: max rel dev = {(recovery / denom).max():.3e}, "
          f"median = {np.median(recovery / denom):.3e}")


def equation_names(convert_dir: Path, wanted: set[int]) -> dict[int, str]:
    """Scan dict.txt for the names of specific 1-based equation numbers."""
    names: dict[int, str] = {}
    with (convert_dir / "dict.txt").open(encoding="utf-8") as handle:
        in_section = False
        for line in handle:
            if line.startswith("Equations"):
                in_section = True
                continue
            if line.startswith("Variables"):
                break
            if not in_section:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[0].startswith("e"):
                number = int(parts[0][1:])
                if number in wanted:
                    names[number] = parts[1]
                    if len(names) == len(wanted):
                        break
    return names


def cmd_check(convert_dir: Path) -> None:
    data = np.load(CACHE_DIR / "system.npz")
    code, args, consts = data["code"], data["args"], data["consts"]
    eq_offsets, rhs, levels = data["eq_offsets"], data["rhs"], data["levels"]
    print(f"system: {len(rhs):,} equations, {len(code):,} ops, {len(levels):,} variables "
          f"({int(data['is_fixed'].sum()):,} fixed)")

    evaluate = make_kernel()
    out = np.empty(len(rhs), dtype=np.float64)
    started = time.time()
    evaluate(code, args, consts, eq_offsets, rhs, levels, out)
    print(f"residual pass: {time.time() - started:.1f}s")

    absres = np.abs(out)
    finite = np.isfinite(out)
    print(f"non-finite residuals: {int((~finite).sum()):,}")
    print(f"max |residual|:    {absres[finite].max():.3e}")
    print(f"p99.9 |residual|:  {np.percentile(absres[finite], 99.9):.3e}")
    print(f"p50 |residual|:    {np.percentile(absres[finite], 50):.3e}")
    for tol in (1e-3, 1e-5, 1e-7):
        print(f"equations with |res| > {tol:g}: {int((absres > tol).sum()):,}")

    worst = np.argsort(-np.where(finite, absres, np.inf))[:15]
    wanted = {int(i) + 1 for i in worst}
    names = equation_names(convert_dir, wanted)
    print("\nworst equations:")
    for i in worst:
        print(f"  e{int(i) + 1:<9} {names.get(int(i) + 1, '?'):<45} res = {out[i]: .3e}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",
                        choices=["parse", "check", "jacobian", "newton", "lutest", "_lu_child", "structure"])
    parser.add_argument("--convert-dir", type=Path, default=DEFAULT_CONVERT_DIR)
    parser.add_argument("--perturb", type=float, default=1e-4)
    parser.add_argument("--max-iter", type=int, default=8)
    parser.add_argument("--tol", type=float, default=1e-9)
    parser.add_argument("--lu-method", default="umfpack")
    parser.add_argument("--from-year", type=int, default=2110)
    parsed = parser.parse_args()
    if parsed.command == "parse":
        cmd_parse(parsed.convert_dir)
    elif parsed.command == "check":
        cmd_check(parsed.convert_dir)
    elif parsed.command == "jacobian":
        cmd_jacobian()
    elif parsed.command == "lutest":
        methods = ("splu-natural", "umfpack", "splu") if parsed.lu_method == "all" else (parsed.lu_method,)
        cmd_lutest(methods, parsed.convert_dir, parsed.from_year)
    elif parsed.command == "_lu_child":
        cmd_lu_child(parsed.lu_method)
    elif parsed.command == "structure":
        cmd_structure(parsed.convert_dir)
    else:
        cmd_newton(parsed.perturb, parsed.max_iter, parsed.tol, parsed.from_year, parsed.convert_dir)


if __name__ == "__main__":
    main()
