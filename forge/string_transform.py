# -*- coding: utf-8 -*-
"""forge.string-transform — replay a transformation pipeline.

The task publishes a step-by-step *recipe* in plain English (no code) that
transforms an initial string through K operations drawn from a template
pool: reverse / upper / replace a->b / slice[k:] / duplicate / swap halves.

Graded by EXECUTION twice: the oracle replays the recorded (op, params)
steps in order AND independently runs the equivalent generated code; the
claimed answer must match both derivations. Never trusted.
"""
import random

from .common import make_id, int_knob, run_code

TYPE = "string-transform"

_ALPHA = "abcdefgh"

_STEPS = ("reverse", "upper", "replace", "slice", "duplicate", "swap")

_DESCR = {
    "reverse": "Reverse the string.",
    "upper": "Convert the string to uppercase.",
    "duplicate": "Duplicate the string (append it to itself).",
    "swap": ("Swap the two halves of the string (odd length: the second "
             "half keeps the extra character)."),
}


# ----------------------------------------------------------------- stepping

def _apply_step(s, step):
    """Replay one (op, params) step, e.g. ["replace", "a", "b"]."""
    op = step[0]
    if op == "reverse":
        return s[::-1]
    if op == "upper":
        return s.upper()
    if op == "replace":
        return s.replace(step[1], step[2])
    if op == "slice":
        return s[step[1]:]
    if op == "duplicate":
        return s * 2
    if op == "swap":
        h = len(s) // 2
        return s[h:] + s[:h]
    raise ValueError("unknown step: %r" % (op,))


def _step_line(step):
    """Equivalent Python source line for one step (operates on `s`)."""
    op = step[0]
    if op == "reverse":
        return "s = s[::-1]"
    if op == "upper":
        return "s = s.upper()"
    if op == "replace":
        return 's = s.replace("%s", "%s")' % (step[1], step[2])
    if op == "slice":
        return "s = s[%d:]" % step[1]
    if op == "duplicate":
        return "s = s * 2"
    if op == "swap":
        return "h = len(s) // 2\ns = s[h:] + s[:h]"
    raise ValueError("unknown step: %r" % (op,))


def _step_descr(step):
    op = step[0]
    if op == "replace":
        return "Replace every occurrence of '%s' with '%s'." % (step[1], step[2])
    if op == "slice":
        return "Drop the first %d characters." % step[1]
    return _DESCR[op]


# ------------------------------------------------------------- public API

def generate(seed, difficulty=0.5):
    rng = random.Random("string-transform|%d" % seed)
    initial = "".join(rng.choice(_ALPHA)
                      for _ in range(int_knob(difficulty, 6, 10)))
    k = int_knob(difficulty, 2, 6)
    steps = []
    for op in rng.sample(_STEPS, k):
        if op == "replace":
            a = rng.choice(_ALPHA)
            b = rng.choice([c for c in _ALPHA if c != a])
            steps.append(["replace", a, b])
        elif op == "slice":
            steps.append(["slice", rng.randrange(1, 4)])
        else:
            steps.append([op])
    s = initial
    for st in steps:
        s = _apply_step(s, st)
    code_lines = ['s = "%s"' % initial]
    for st in steps:
        code_lines.append(_step_line(st))
    code_lines.append("result = s")
    code = "\n".join(code_lines)
    numbered = "\n".join("%d. %s" % (i, _step_descr(st))
                         for i, st in enumerate(steps, 1))
    prompt = ("Start with the string `%s`.\n\n"
              "Apply these steps in order:\n%s\n\n"
              "What is the final string? Answer with the exact string only."
              % (initial, numbered))
    solution = ("Applying the steps is equivalent to:\n\n"
                "```python\n%s\n```\n\nThe final string is %r." % (code, s))
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"output": s},
        "solution": solution,
        "meta": {"steps": steps, "initial": initial, "code": code},
    }


def verify(problem):
    """Replay the recorded steps AND re-run the equivalent code; the answer
    must match both independent derivations."""
    try:
        meta = problem["meta"]
        s = meta["initial"]
        for step in meta["steps"]:
            s = _apply_step(s, step)
        if run_code(meta["code"]) != s:
            return False
        return problem["answer"].get("output") == s
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
    p["answer"]["output"] = "WRONG"
    cases.append(("verify-false-wrong-output", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["steps"].append(["duplicate"])
    cases.append(("verify-false-tampered-steps",
                  lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["code"] = p["meta"]["code"] + '\nresult = result + "x"'
    cases.append(("verify-false-tampered-code", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"].pop("output")
    cases.append(("verify-false-missing", lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))

    def _helper():
        ok = (_apply_step("abcd", ["reverse"]) == "dcba"
              and _apply_step("abcd", ["swap"]) == "cdab"
              and _apply_step("abc", ["swap"]) == "bca"
              and _apply_step("abc", ["slice", 1]) == "bc"
              and _apply_step("ab", ["duplicate"]) == "abab")
        rng = random.Random("helper")
        for _ in range(20):
            s = "".join(rng.choice(_ALPHA) for _ in range(6))
            st = [rng.choice(_STEPS)]
            if st[0] == "replace":
                st += ["a", "c"]
            elif st[0] == "slice":
                st += [rng.randrange(1, 4)]
            code = 's = "%s"\n%s\nresult = s' % (s, _step_line(st))
            if run_code(code) != _apply_step(s, st):
                return False
        return ok
    cases.append(("helper-step-apply-vs-code", _helper))
    return cases
