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


def export_solution_gdx(convert_dir: Path, x: np.ndarray, out_path: Path) -> None:
    """Write a solved point as a baseline.gdx-style GDX (symbol names + domains from dict.txt).

    The last domain column is named 't' when it holds years, matching what the
    MAKROskop ETL (extract.py read_records) expects.
    """
    import pandas as pd
    import gams.transfer as gt
    import gamspy_base
    from collections import defaultdict

    records: dict[str, list] = defaultdict(list)
    with (convert_dir / "dict.txt").open(encoding="utf-8") as handle:
        in_vars = False
        for line in handle:
            if line.startswith("Variables "):
                in_vars = True
                continue
            if not in_vars:
                continue
            parts = line.split()
            if len(parts) < 2 or parts[0][0] != "x" or not parts[0][1:].isdigit():
                continue
            symbol, _, rest = parts[1].partition("(")
            keys = rest.rstrip(")").split(",") if rest else []
            records[symbol].append((keys, x[int(parts[0][1:]) - 1]))

    container = gt.Container(system_directory=gamspy_base.directory)
    written = 0
    for symbol, entries in records.items():
        ndim = len(entries[0][0])
        columns = [f"d{i}" for i in range(ndim)]
        if ndim and all(entry[0][-1].isdigit() for entry in entries[:50]):
            columns[-1] = "t"
        frame = pd.DataFrame(
            [(*keys, value) for keys, value in entries],
            columns=columns + ["level"],
        )
        frame["marginal"] = 0.0
        frame["lower"] = -np.inf
        frame["upper"] = np.inf
        frame["scale"] = 1.0
        gt.Variable(container, symbol, "free", domain=columns or None, records=frame)
        written += 1
    container.write(str(out_path))
    print(f"wrote {out_path} ({written:,} symbols, {sum(len(v) for v in records.values()):,} records)")


def cmd_solve_export(from_year: int, shock_name: str, shock_years: tuple[int, int] | None,
                     shock_factor: float, shock_delta: float, out_path: Path,
                     convert_dir: Path, tol: float) -> None:
    """Solve a (possibly multi-year) shock with continuation and export the solution as GDX."""
    system = System()
    window = Window(system, convert_dir, from_year)
    print(f"window: {len(window.eq_sel):,} equations ({window.n_years} years)")

    shock_vars = np.array(find_shock_variables(convert_dir, shock_name, shock_years))
    fixed_ok = system.is_fixed[shock_vars]
    if not fixed_ok.all():
        raise SystemExit(f"{(~fixed_ok).sum()} of {len(shock_vars)} shock variables are endogenous")
    targets = system.levels[shock_vars] * shock_factor + shock_delta
    print(f"shock: {shock_name} x {len(shock_vars)} instances "
          f"(years {shock_years}), factor {shock_factor}, delta {shock_delta}")

    x = system.levels.copy()
    solve_shock(system, window, x, shock_vars, targets, tol=tol)
    residual = np.empty(system.n_eq)
    system.residuals(x, residual)
    print(f"solved: ||r||_inf = {np.abs(residual[window.eq_sel]).max():.3e}")
    export_solution_gdx(convert_dir, x, out_path)


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


def make_direct_solver(matrix):
    """Factorize once, return a solve callable. Prefers MKL Pardiso (x86) over SuperLU.

    Rows are equilibrated first: this system mixes ~1e5-scale NPV rows with
    ~1e-2-scale ratio rows, which wrecks pivot quality (observed as sporadic
    Pardiso factorizations too inaccurate for Newton's final digits).
    """
    from scipy import sparse

    csr = matrix.tocsr()
    magnitude = csr.copy()
    magnitude.data = np.abs(magnitude.data)
    row_max = magnitude.max(axis=1).toarray().ravel()
    scale = np.where(row_max > 0, 1.0 / np.maximum(row_max, 1e-300), 1.0)
    scaled = (sparse.diags(scale) @ csr).tocsr()
    try:
        import pypardiso

        solver = pypardiso.PyPardisoSolver()
        solver.factorize(scaled)
        return lambda b: solver.solve(scaled, scale * b)
    except ImportError:
        from scipy.sparse.linalg import splu

        lu = splu(scaled.tocsc())
        return lambda b: lu.solve(scale * b)


class Window:
    """A trailing time-window of the system: equations/free vars with year >= from_year."""

    def __init__(self, system: System, convert_dir: Path, from_year: int):
        self.from_year = from_year
        self.n_years = 2130 - from_year
        eq_year, var_year = load_years(convert_dir, system.n_eq, len(system.levels))
        self.eq_year = eq_year
        self.var_year = var_year
        self.eq_sel = np.where(eq_year >= from_year)[0]
        free_year = var_year[system.free_ids]
        var_sel = np.where(free_year >= from_year)[0]
        assert len(self.eq_sel) == len(var_sel), (len(self.eq_sel), len(var_sel))
        self.window_vars = system.free_ids[var_sel]
        self.eq_perm = self.eq_sel[np.argsort(eq_year[self.eq_sel], kind="stable")]
        var_perm = var_sel[np.argsort(free_year[var_sel], kind="stable")]
        self.window_vars_sorted = system.free_ids[var_perm]
        self.var_perm = var_perm
        sorted_years = np.sort(eq_year[self.eq_sel])
        self.year_offsets = np.searchsorted(sorted_years, np.arange(from_year, 2131))

    def in_window_eq_mask(self, n_eq: int) -> np.ndarray:
        mask = np.zeros(n_eq, dtype=bool)
        mask[self.eq_sel] = True
        return mask


def solve_window(system: System, window: Window, x: np.ndarray,
                 tol: float = 1e-9, max_iter: int = 10, lu_reuse=None):
    """Newton on the window, mutating x in place. Returns (final ||r||_inf, last solver).

    A carried-over factorization (chord iterations) is tried first and rebuilt from a
    fresh Jacobian whenever progress is poor — cheap on continuation ladders where the
    Jacobian barely changes between stages.
    """
    residual_full = np.empty(system.n_eq)
    system.residuals(x, residual_full)
    norm = np.abs(residual_full[window.eq_sel]).max()
    print(f"start: ||r||_inf = {norm:.3e}", flush=True)
    lu = lu_reuse
    fresh = False
    history: list[float] = [norm]

    for iteration in range(1, max_iter + 1):
        if norm < tol:
            break
        t0 = time.time()
        if lu is None:
            jac = system.jacobian_csc(x)
            jac_window = jac[window.eq_perm, :][:, window.var_perm].tocsc()
            lu = (make_direct_solver(jac_window), jac_window)
            fresh = True
        factor_time = time.time() - t0
        solve_fn, matrix = lu
        rhs = -residual_full[window.eq_perm]
        rhs_norm = np.linalg.norm(rhs) + 1e-300
        dx = solve_fn(rhs)
        # iterative refinement to measured convergence: backends (Pardiso especially)
        # deliver ~1e-6 accuracy alone, far too loose for Newton's final digits
        for _ in range(6):
            linear_residual = rhs - matrix @ dx
            if np.linalg.norm(linear_residual) < 1e-11 * rhs_norm:
                break
            dx += solve_fn(linear_residual)
        else:
            rel = np.linalg.norm(rhs - matrix @ dx) / rhs_norm
            if rel > 1e-8:
                print(f"  WARNING: linear solve stalled at rel residual {rel:.1e}", flush=True)

        # Non-monotone acceptance: a full Newton step may raise ||r||_inf temporarily
        # (bilinear cross-terms of large-scale NPV variables) yet be nearly exact in
        # relative terms — quadratic contraction cleans it up next iteration. The
        # legitimate rise scales with the RESPONSE size, not the starting residual:
        # measured ~3e-6 * ||dx||^2 for the NPV recursions, so allow 1e-4 * ||dx||^2.
        dx_inf = np.abs(dx).max()
        reference = min(max(1e3 * max(history[-3:]), 1e-4 * dx_inf * dx_inf), 1e7)
        alpha = 1.0
        accepted = False
        for _ in range(8):
            x_try = x.copy()
            x_try[window.window_vars_sorted] += alpha * dx
            system.residuals(x_try, residual_full)
            trial_norm = np.abs(residual_full[window.eq_sel]).max()
            if np.isfinite(trial_norm) and (trial_norm < norm or (alpha == 1.0 and trial_norm < reference)):
                accepted = True
                break
            alpha *= 0.5
        if not accepted:
            system.residuals(x, residual_full)  # restore residual at x
            if fresh:
                print("  line search failed with fresh Jacobian; stopping", flush=True)
                return norm, lu
            lu = None  # stale chord LU: rebuild and retry
            continue

        reduction = trial_norm / norm if norm > 0 else 0.0
        x[:] = x_try
        norm = trial_norm
        history.append(norm)
        note = "fresh" if fresh else "chord"
        print(f"iter {iteration}: ||r||_inf = {norm:.3e}  ||dx||_inf = {np.abs(dx).max():.3e}  "
              f"alpha = {alpha}  ({note}, factor {factor_time:.1f}s)", flush=True)
        # keep the LU for chord iterations only while contraction is strong
        if not (alpha == 1.0 and reduction <= 0.02):
            lu = None
        fresh = False
    return norm, lu


def solve_shock(system: System, window: Window, x: np.ndarray, shock_vars: np.ndarray,
                target_values: np.ndarray, tol: float = 1e-9) -> float:
    """Continuation on shock size: ramp the exogenous variables to their targets.

    Mirrors MAKRO's own homotopy trick (solve at 1/100 size, then rescale).
    """
    base_values = x[shock_vars].copy()
    deltas = target_values - base_values
    solved_share = 0.0
    step = 0.01
    checkpoint = x.copy()
    lu = None
    attempts = 0

    while solved_share < 1.0 - 1e-12:
        attempts += 1
        if attempts > 40:
            raise SystemExit("continuation gave up after 40 stages")
        share = min(1.0, solved_share + step)
        x[:] = checkpoint
        x[shock_vars] = base_values + share * deltas
        print(f"--- continuation: {solved_share:.4f} -> {share:.4f} of shock ---", flush=True)
        norm, lu = solve_window(system, window, x, tol=tol, max_iter=8, lu_reuse=lu)
        if norm < tol:
            solved_share = share
            checkpoint = x.copy()
            step = min(step * 2.5, 1.0 - solved_share) or step
        else:
            step /= 2
            lu = None
            if step < 1e-4:
                raise SystemExit(f"continuation stalled at share {solved_share}")
    return tol


def cmd_newton(perturb: float, max_iter: int, tol: float, from_year: int, convert_dir: Path) -> None:
    system = System()
    window = Window(system, convert_dir, from_year)
    print(f"window system: {len(window.eq_sel):,} equations/unknowns "
          f"({window.n_years} years of {system.n_eq:,} total)")

    x = system.levels.copy()
    rng = np.random.default_rng(42)
    if perturb > 0:
        noise = perturb * (np.abs(x[window.window_vars]) + 1e-3) * rng.standard_normal(len(window.window_vars))
        x[window.window_vars] += noise
        print(f"perturbed {len(window.window_vars):,} window variables, relative scale {perturb:g}")

    norm, _ = solve_window(system, window, x, tol=tol, max_iter=max_iter)

    recovery = np.abs(x[window.window_vars] - system.levels[window.window_vars])
    denom = np.abs(system.levels[window.window_vars]) + 1e-8
    print(f"final ||r||_inf = {norm:.3e}")
    print(f"recovery vs original solution: max rel dev = {(recovery / denom).max():.3e}, "
          f"median = {np.median(recovery / denom):.3e}")


def find_shock_variables(convert_dir: Path, name: str, years: tuple[int, int] | None) -> list[int]:
    """Variable ids for a shock spec.

    'rRenteECB(2124)' -> that exact instance; 'rRenteECB' + years -> every instance
    (all domain combinations) whose final index falls in the year range.
    """
    if "(" in name:
        return [find_variable(convert_dir, name)]
    prefix = name + "("
    ids: list[int] = []
    with (convert_dir / "dict.txt").open(encoding="utf-8") as handle:
        in_vars = False
        for line in handle:
            if line.startswith("Variables "):
                in_vars = True
                continue
            if not in_vars:
                continue
            parts = line.split()
            if len(parts) < 2 or not parts[1].startswith(prefix):
                continue
            last_key = parts[1].rstrip(")").rsplit(",", 1)[-1].rsplit("(", 1)[-1]
            if not last_key.isdigit():
                continue
            if years is None or years[0] <= int(last_key) <= years[1]:
                ids.append(int(parts[0][1:]) - 1)
    if not ids:
        raise SystemExit(f"no variables matched shock spec {name!r} in years {years}")
    return ids


def find_variable(convert_dir: Path, name: str) -> int:
    """Exact dict.txt variable name (e.g. 'jvBNI(2124)') -> 0-based x index."""
    with (convert_dir / "dict.txt").open(encoding="utf-8") as handle:
        in_vars = False
        for line in handle:
            if line.startswith("Variables "):
                in_vars = True
                continue
            if not in_vars:
                continue
            parts = line.split()
            if len(parts) >= 2 and parts[1] == name:
                return int(parts[0][1:]) - 1
    raise SystemExit(f"variable {name!r} not found in dict.txt")


def iter_equation_statements(gams_path: Path):
    """Yield (eq_index_0based, full_statement_text) for every equation in gams.gms."""
    statement: list[str] = []
    eq_index = -1
    in_equations = False
    with gams_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not in_equations:
                if EQ_START_RE.match(line):
                    in_equations = True
                else:
                    continue
            if line[0] == "*":
                continue
            stripped = line.strip()
            if not stripped:
                continue
            if not statement:
                match = EQ_START_RE.match(stripped)
                if not match:
                    return  # equations section over
                eq_index = int(match.group(1)) - 1
            statement.append(stripped)
            if stripped.endswith(";"):
                # join on spaces: a wrapped line may start with '*' (multiplication),
                # which GAMS would treat as a comment in column 1
                yield eq_index, " ".join(statement)
                statement = []


def wrap_names(names: list[str], width: int = 200) -> str:
    lines: list[str] = []
    current = "    "
    for name in names:
        if len(current) + len(name) + 1 > width and current.strip():
            lines.append(current)
            current = "    "
        current += name + ","
    lines.append(current)
    return "\n".join(lines).rstrip(",")


def export_window_gms(system: System, window: Window, convert_dir: Path, x: np.ndarray,
                      out_path: Path) -> np.ndarray:
    """Write a runnable GAMS scalar model for the window at point x (shocks already applied).

    Equations are copied verbatim from the original convert file; out-of-window and
    exogenous variables are fixed at their values in x. Returns the referenced var ids.
    """
    eq_mask = window.in_window_eq_mask(system.n_eq)
    entry_counts = np.diff(system.entry_offsets)
    entry_mask = np.repeat(eq_mask, entry_counts)
    var_stream = system.args[np.asarray(system.code) == OP_VAR]
    referenced = np.unique(var_stream[entry_mask])
    free_mask = np.zeros(len(system.levels), dtype=bool)
    free_mask[window.window_vars] = True

    with out_path.open("w", encoding="utf-8") as out:
        out.write("$offlisting\n$offsymxref\noption limrow=0, limcol=0, solprint=off;\n")
        out.write("Variables zobj,\n")
        out.write(wrap_names([f"x{v + 1}" for v in referenced]))
        out.write(";\n\nEquations eobj,\n")
        out.write(wrap_names([f"e{e + 1}" for e in window.eq_sel]))
        out.write(";\n\neobj.. zobj =E= 0;\n")
        for eq_index, statement in iter_equation_statements(convert_dir / "gams.gms"):
            if eq_mask[eq_index]:
                out.write(statement)
                out.write("\n")
        out.write("\n* levels for window unknowns, fixes for everything else\n")
        for v in referenced:
            suffix = "l" if free_mask[v] else "fx"
            out.write(f"x{v + 1}.{suffix} = {float(x[v])!r};\n")
        out.write("\nModel mw /all/;\nmw.holdfixed = 1;\noption nlp=ipopt;\n")
        out.write("Solve mw using NLP minimizing zobj;\n")
        out.write("execute_unload 'oracle_out.gdx';\n")
    return referenced


def run_gams(workdir: Path, gms_name: str) -> None:
    import subprocess

    gams_binary = Path(__file__).parent / ".venv/lib/python3.12/site-packages/gamspy_base/gams"
    license_path = Path.home() / "Library/Application Support/GAMSPy/gamspy_license.txt"
    result = subprocess.run(
        [str(gams_binary), gms_name, f"license={license_path}", "lo=2"],
        cwd=workdir, capture_output=True, text=True,
    )
    log = (workdir / gms_name.replace(".gms", ".log"))
    if result.returncode != 0:
        tail = log.read_text(encoding="utf-8")[-2000:] if log.exists() else result.stdout[-2000:]
        raise SystemExit(f"gams exited {result.returncode}:\n{tail}")
    lst = workdir / gms_name.replace(".gms", ".lst")
    if lst.exists():
        statuses = [line.strip() for line in lst.read_text(encoding="utf-8").splitlines()
                    if "SOLVER STATUS" in line or "MODEL STATUS" in line or "Iteration count" in line]
        for line in statuses[:4]:
            print(f"  {line}")


def read_oracle_solution(workdir: Path, referenced: np.ndarray, n_vars: int) -> np.ndarray:
    """Parse xN levels from gdxdump of the oracle GDX into a full-length array."""
    import subprocess

    gdxdump = Path(__file__).parent / ".venv/lib/python3.12/site-packages/gamspy_base/gdxdump"
    text = subprocess.run([str(gdxdump), "oracle_out.gdx"], cwd=workdir,
                          capture_output=True, text=True, check=True).stdout
    values = np.full(n_vars, np.nan)
    # gdxdump: "free     Variable x103 /L 1, LO 1, UP 1 /;" — the L field is OMITTED when 0
    pattern = re.compile(r"Variable x(\d+)\s*/([^/;]*)/")
    level_re = re.compile(r"\bL\s+([^,\s/]+)")
    special = {"Eps": 0.0, "+Inf": np.inf, "-Inf": -np.inf, "Na": np.nan, "Undf": np.nan}
    count = 0
    for match in pattern.finditer(text):
        fields = level_re.search(match.group(2))
        token = fields.group(1) if fields else "0"
        values[int(match.group(1)) - 1] = special.get(token, None) if token in special else float(token)
        count += 1
    print(f"  oracle solution: parsed {count:,} variable levels from gdxdump")
    return values


def cmd_oracle(from_year: int, shock_name: str, shock_factor: float, shock_delta: float,
               convert_dir: Path, tol: float, max_iter: int, reuse_gams: bool = False) -> None:
    """Solve the same shocked window with GAMS/IPOPT and with the free Newton solver; compare."""
    system = System()
    window = Window(system, convert_dir, from_year)
    print(f"window: {len(window.eq_sel):,} equations ({window.n_years} years)")

    shock_var = find_variable(convert_dir, shock_name)
    if not system.is_fixed[shock_var]:
        raise SystemExit(f"{shock_name} is endogenous (free) — shock an exogenous variable")
    old_value = system.levels[shock_var]
    new_value = old_value * shock_factor + shock_delta
    print(f"shock: {shock_name} (x{shock_var + 1}) {old_value!r} -> {new_value!r}")

    x = system.levels.copy()
    x[shock_var] = new_value

    workdir = CACHE_DIR / "oracle"
    workdir.mkdir(parents=True, exist_ok=True)
    if reuse_gams and (workdir / "oracle_out.gdx").exists():
        print("reusing existing oracle_out.gdx", flush=True)
        referenced = np.array([], dtype=np.int64)
    else:
        print("exporting window model for GAMS ...", flush=True)
        referenced = export_window_gms(system, window, convert_dir, x, workdir / "window.gms")
        if shock_var not in set(referenced.tolist()):
            print("  WARNING: shock variable is not referenced by any window equation!")
        print(f"  wrote window.gms ({len(referenced):,} variables referenced)")
        print("running GAMS + IPOPT ...", flush=True)
        t0 = time.time()
        run_gams(workdir, "window.gms")
        print(f"  gams finished in {time.time() - t0:.0f}s")
    oracle = read_oracle_solution(workdir, referenced, len(system.levels))

    print("running free Newton solver on the same shocked window ...", flush=True)
    ours = system.levels.copy()
    solve_shock(system, window, ours, np.array([shock_var]), np.array([new_value]), tol=tol)
    final_residual = np.empty(system.n_eq)
    system.residuals(ours, final_residual)
    print(f"free solver final ||r||_inf = {np.abs(final_residual[window.eq_sel]).max():.3e}")

    w = window.window_vars
    have = np.isfinite(oracle[w])
    deviation = np.abs(ours[w][have] - oracle[w][have])
    scale = np.maximum(np.abs(oracle[w][have]), 1e-6)
    rel = deviation / scale
    moved = np.abs(oracle[w][have] - system.levels[w][have]) / scale
    print("\n=== ORACLE COMPARISON (free Newton vs GAMS/IPOPT, same shocked system) ===")
    print(f"variables compared: {have.sum():,}")
    print(f"shock actually moved the solution: max |change| rel = {moved.max():.3e}, "
          f"p90 = {np.percentile(moved, 90):.3e}")
    print(f"solver disagreement: max rel = {rel.max():.3e}, median rel = {np.median(rel):.3e}, "
          f"p99.9 rel = {np.percentile(rel, 99.9):.3e}")
    responded = moved > 1e-6  # clear of both solvers' tolerance floor
    if responded.any():
        irf_err = deviation[responded] / (moved[responded] * scale[responded])
        print(f"variables that responded to the shock (rel change > 1e-8): {responded.sum():,}")
        print(f"  disagreement relative to response size: max = {irf_err.max():.3e}, "
              f"median = {np.median(irf_err):.3e}")


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
                        choices=["parse", "check", "jacobian", "newton", "lutest", "_lu_child",
                                 "structure", "oracle", "solve-export", "export-baseline"])
    parser.add_argument("--shock-name", default="",
                        help="exact instance 'rRenteECB(2124)' or symbol 'rRenteECB' with --shock-years")
    parser.add_argument("--shock-years", default="",
                        help="year range for symbol-level shocks, e.g. '2030-2129'")
    parser.add_argument("--shock-factor", type=float, default=1.0)
    parser.add_argument("--shock-delta", type=float, default=0.0)
    parser.add_argument("--out", type=Path, default=Path(__file__).parent / "shock_gdx" / "solved.gdx")
    parser.add_argument("--reuse-gams", action="store_true")
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
    elif parsed.command == "oracle":
        cmd_oracle(parsed.from_year, parsed.shock_name, parsed.shock_factor, parsed.shock_delta,
                   parsed.convert_dir, parsed.tol, parsed.max_iter, parsed.reuse_gams)
    elif parsed.command == "export-baseline":
        data = np.load(CACHE_DIR / "system.npz")
        export_solution_gdx(parsed.convert_dir, data["levels"], parsed.out)
    elif parsed.command == "solve-export":
        years = None
        if parsed.shock_years:
            lo, _, hi = parsed.shock_years.partition("-")
            years = (int(lo), int(hi or lo))
        cmd_solve_export(parsed.from_year, parsed.shock_name, years, parsed.shock_factor,
                         parsed.shock_delta, parsed.out, parsed.convert_dir, parsed.tol)
    else:
        cmd_newton(parsed.perturb, parsed.max_iter, parsed.tol, parsed.from_year, parsed.convert_dir)


if __name__ == "__main__":
    main()
