# -*- coding: utf-8 -*-
"""forge.loop-count — nested bounded for-loops, count or accumulate.

A 1-3 layer nested loop over range(a, b) integer bounds is generated. Two
question kinds: the accumulated `result` value, or the total number of
innermost-body executions. Graded by EXECUTION: `result` re-runs the code
from meta, `iterations` re-runs generator-built instrumented code (one
counter per layer). The claimed answer is never trusted.
"""
import random

from .common import make_id, int_knob, run_code

TYPE = "loop-count"


def _ranges(rng, difficulty):
    depth = int_knob(difficulty, 1, 3)
    names = ("i", "j", "k")[:depth]
    total = 1
    rs = []
    for nm in names:
        a = rng.randrange(0, 4)
        w = int_knob(difficulty, 2, 6)
        while total * w > 240 and w > 1:
            w -= 1
        total *= w
        rs.append((nm, a, a + w))
    return rs, total


def _expr(rng, names):
    if len(names) >= 2:
        return rng.choice([
            "%s * %s" % (names[0], names[1]),
            names[1],
            "%s + %s" % (names[0], names[1]),
        ])
    return rng.choice([names[0], "%s * 2" % names[0], "%s + 1" % names[0]])


def _plain(rs, expr):
    lines = ["result = 0"]
    indent = ""
    for nm, a, b in rs:
        lines.append("%sfor %s in range(%d, %d):" % (indent, nm, a, b))
        indent += "    "
    lines.append("%sresult = result + %s" % (indent, expr))
    return "\n".join(lines)


def _instrumented(rs, expr):
    """Same loops, but every layer accumulates a counter; result = innermost."""
    lines = ["acc = 0"]
    for idx in range(len(rs)):
        lines.append("_c%d = 0" % (idx + 1))
    indent = ""
    for idx, (nm, a, b) in enumerate(rs):
        lines.append("%sfor %s in range(%d, %d):" % (indent, nm, a, b))
        indent += "    "
        lines.append("%s_c%d = _c%d + 1" % (indent, idx + 1, idx + 1))
    lines.append("%sacc = acc + %s" % (indent, expr))
    lines.append("result = _c%d" % len(rs))
    return "\n".join(lines)


def generate(seed, difficulty=0.5):
    rng = random.Random("loop-count|%d" % seed)
    rs, total = _ranges(rng, difficulty)
    names = [nm for nm, _, _ in rs]
    expr = _expr(rng, names)
    kind = "iterations" if rng.random() < 0.5 else "result"
    code = _plain(rs, expr)
    code_instr = _instrumented(rs, expr)
    if kind == "iterations":
        answer = {"iterations": total}
        prompt = ("How many times does the innermost loop body run in total "
                  "(summed over all iterations of the outer loops)?\n\n"
                  "```python\n%s\n```" % code)
        solution = ("Each outer iteration runs the inner range fully, so the "
                    "innermost body executes %d times in total." % total)
    else:
        value = run_code(code)
        answer = {"result": value}
        prompt = ("What is the final value of `result` after this code "
                  "runs?\n\n```python\n%s\n```" % code)
        solution = ("Executing the loops step by step yields result = %r."
                    % (value,))
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": answer,
        "solution": solution,
        "meta": {"code": code, "code_instr": code_instr, "kind": kind,
                 "depth": len(rs), "iterations": total},
    }


def verify(problem):
    try:
        kind = problem["meta"]["kind"]
        if kind == "iterations":
            n = run_code(problem["meta"]["code_instr"])
            return isinstance(n, int) and problem["answer"].get("iterations") == n
        value = run_code(problem["meta"]["code"])
        return problem["answer"].get("result") == value
    except Exception:
        return False


def self_cases():
    import copy
    cases = []
    for sd in range(5):
        cases.append(("gen-deterministic-%d" % sd,
                      lambda sd=sd: generate(sd, 0.5) == generate(sd, 0.5)))
    for d in (0.0, 0.25, 0.5, 0.75, 1.0):
        cases.append(("verify-true-d%.2f" % d,
                      lambda d=d: verify(generate(123 + int(d * 100), d))))
    base = generate(7, 0.5)
    p = copy.deepcopy(base)
    if "iterations" in p["answer"]:
        p["answer"]["iterations"] += 1
    else:
        p["answer"]["result"] += 1
    cases.append(("verify-false-wrong-value", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    if p["meta"]["kind"] == "iterations":
        p["meta"]["code_instr"] = p["meta"]["code_instr"] + "\nresult = 0"
    else:
        p["meta"]["code"] = p["meta"]["code"] + "\nresult = result + 1"
    cases.append(("verify-false-tampered-code", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"].pop(next(iter(p["answer"])))
    cases.append(("verify-false-missing", lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    instr = _instrumented([("i", 0, 3), ("j", 0, 4)], "i * j")
    cases.append(("instrumented-helper",
                  lambda: run_code(instr) == 12 and
                          run_code(_plain([("i", 0, 3)], "i * 2")) == 6))
    return cases
