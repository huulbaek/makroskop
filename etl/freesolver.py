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
DEFAULT_CONVERT_DIR = Path(
    "/private/tmp/claude-501/-Users-huulbaek-vserver-MAKRO/0c2712fa-ab43-4db0-a50c-eff3ce64abe0/scratchpad/convert"
)

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
    parser.add_argument("command", choices=["parse", "check"])
    parser.add_argument("--convert-dir", type=Path, default=DEFAULT_CONVERT_DIR)
    parsed = parser.parse_args()
    if parsed.command == "parse":
        cmd_parse(parsed.convert_dir)
    else:
        cmd_check(parsed.convert_dir)


if __name__ == "__main__":
    main()
