# -*- coding: utf-8 -*-
"""forge.output-prediction — reference implementation.

Problem: read a short procedurally generated Python snippet and predict
what it prints/stores in `result`. Graded by actually EXECUTING the code
shown in the prompt — the oracle is the interpreter itself.
"""
import random

from .common import make_id, int_knob, run_code

TYPE = "output-prediction"


def _arith_snippet(rng, difficulty):
    n = int_knob(difficulty, 2, 5)
    lines = ["x = %d" % rng.randrange(2, 50)]
    for _ in range(n):
        op = rng.choice(["+", "-", "*"])
        lines.append("x = x %s %d" % (op, rng.randrange(2, 13)))
    lines.append("result = x")
    return "\n".join(lines)


def _string_snippet(rng, difficulty):
    alpha = "abcdefgh"
    s = "".join(rng.choice(alpha) for _ in range(int_knob(difficulty, 6, 12)))
    lines = ["s = \"%s\"" % s]
    k = int_knob(difficulty, 2, 5)
    ops = [("s = s.upper()", None), ("s = s[::-1]", None),
           ("s = s[:%d]" % k, None), ("s = s * %d" % rng.randrange(2, 3), None)]
    used = rng.sample(ops, int_knob(difficulty, 2, 4))
    for code, _ in used:
        lines.append(code)
    lines.append("result = s")
    return "\n".join(lines)


def _loop_snippet(rng, difficulty):
    n = int_knob(difficulty, 3, 9)
    k = rng.randrange(1, 5)
    start = rng.randrange(0, 10)
    return ("total = %d\n"
            "for i in range(%d):\n"
            "    total = total + i * %d\n"
            "result = total" % (start, n, k))


TEMPLATES = (_arith_snippet, _string_snippet, _loop_snippet)


def generate(seed, difficulty=0.5):
    rng = random.Random("output-prediction|%d" % seed)
    template = rng.choice(TEMPLATES)
    code = template(rng, difficulty)
    output = run_code(code)
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": ("What is the value of `result` after this snippet runs?\n\n"
                   "```python\n%s\n```" % code),
        "answer": {"output": output},
        "solution": "Executing the snippet yields result = %r." % (output,),
        "meta": {"code": code},
    }


def verify(problem):
    """Re-EXECUTE the code from meta and compare with the claimed output."""
    try:
        return run_code(problem["meta"]["code"]) == problem["answer"]["output"]
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
    if isinstance(p["answer"]["output"], str):
        p["answer"]["output"] = "WRONG"
    else:
        p["answer"]["output"] += 1
    cases.append(("verify-false-wrong-output", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["code"] = p["meta"]["code"] + "\nresult = result + 1"
    cases.append(("verify-false-tampered-code", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"].pop("output")
    cases.append(("verify-false-missing", lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("sandbox-no-builtins", lambda: run_code("result = len") is len))
    return cases
