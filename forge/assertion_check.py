# -*- coding: utf-8 -*-
"""forge.assertion-check — will the assertion hold?

A tiny function f(x) (2-4 arithmetic/string lines, template families) is
generated together with one input value v. The task publishes an assertion
`assert f(v) == expected`; depending on difficulty roughly half of the
asserted values are deliberately wrong.

Graded by EXECUTION: the oracle re-runs the recorded function on the
recorded input, derives the actual value and whether the assertion really
holds, and compares both with the claimed answer. Never trusted.
"""
import random

from .common import make_id, knob, run_code

TYPE = "assertion-check"

_ALPHA = "abcdefgh"


# ---------------------------------------------------------------- templates
# Each template returns (body_lines, input_kind); body_lines form `def f(x):`
# (deterministic, no imports / while / I/O — safe to execute by construction).

def _f_arith_lin(rng, difficulty):
    k1, k2 = rng.randrange(2, 12), rng.randrange(2, 9)
    return ["x = x + %d" % k1, "return x * %d" % k2], "int"


def _f_arith_mod(rng, difficulty):
    k1, k2 = rng.randrange(2, 7), rng.randrange(2, 7)
    return ["y = x %% %d" % k1, "return y + x // %d" % k2], "int"


def _f_arith_minmax(rng, difficulty):
    k1, k2 = rng.randrange(2, 20), rng.randrange(2, 20)
    return ["t = min(x, %d)" % k1, "return abs(t - %d) + x" % k2], "int"


def _f_str_upslice(rng, difficulty):
    k = rng.randrange(1, 4)
    return ["t = x.upper()", "return t + x[:%d]" % k], "str"


def _f_str_revdup(rng, difficulty):
    return ["t = x[::-1]", "return (t + x) * 2"], "str"


def _f_str_replace(rng, difficulty):
    a = rng.choice(_ALPHA)
    b = rng.choice([c for c in _ALPHA if c != a])
    k = rng.randrange(3, 7)
    return ['t = x.replace("%s", "%s")' % (a, b), "return t[:%d]" % k], "str"


_TEMPLATES = (_f_arith_lin, _f_arith_mod, _f_arith_minmax,
              _f_str_upslice, _f_str_revdup, _f_str_replace)


# ------------------------------------------------------- wrong-value helpers

def _wrong_int(actual, rng):
    return actual + rng.choice((-3, -2, -1, 1, 2, 3))


def _wrong_str(actual, rng):
    return actual + rng.choice(_ALPHA)


# ------------------------------------------------------------- public API

def generate(seed, difficulty=0.5):
    rng = random.Random("assertion-check|%d" % seed)
    body, kind = rng.choice(_TEMPLATES)(rng, difficulty)
    if kind == "int":
        v = rng.randrange(2, 40)
    else:
        v = "".join(rng.choice(_ALPHA)
                    for _ in range(rng.randrange(4, 9)))
    func_lines = ["def f(x):"] + ["    " + ln for ln in body]
    actual = run_code("\n".join(func_lines + ["result = f(%r)" % (v,)]))
    hold = rng.random() < knob(difficulty, 0.62, 0.38)
    if hold:
        expected = actual
    elif isinstance(actual, int):
        expected = _wrong_int(actual, rng)
    else:
        expected = _wrong_str(actual, rng)
    func_code = "\n".join(func_lines)
    prompt = ("Consider this function:\n\n"
              "```python\n%s\n```\n\n"
              "Will the assertion `assert f(%r) == %r` pass? Answer whether "
              "it holds (true) or fails (false)." % (func_code, v, expected))
    if hold:
        solution = ("Executing f on the given input yields %r, which equals "
                    "the asserted value: the assertion holds." % (actual,))
    else:
        solution = ("Executing f on the given input yields %r, but the "
                    "assertion demands %r: the assertion fails."
                    % (actual, expected))
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"holds": hold, "actual": actual},
        "solution": solution,
        "meta": {"code": func_code, "call_input": v, "asserted": expected},
    }


def verify(problem):
    """Re-EXECUTE the recorded function on the recorded input; compare both
    the derived actual value and the derived holds-flag with the answer."""
    try:
        meta = problem["meta"]
        code = meta["code"] + "\nresult = f(%r)" % (meta["call_input"],)
        actual = run_code(code)
        ans = problem["answer"]
        if ans.get("actual") != actual:
            return False
        return bool(ans.get("holds")) == (actual == meta["asserted"])
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
    hold_seed = next(s for s in range(80) if generate(s, 0.0)["answer"]["holds"])
    nohold_seed = next(s for s in range(80)
                       if not generate(s, 1.0)["answer"]["holds"])
    base = generate(hold_seed, 0.0)
    p = copy.deepcopy(base)
    p["answer"]["holds"] = not p["answer"]["holds"]
    cases.append(("verify-false-flipped-holds", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    a = p["answer"]["actual"]
    p["answer"]["actual"] = a + 1 if isinstance(a, int) else a + "q"
    cases.append(("verify-false-wrong-actual", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["code"] = p["meta"]["code"] + "\ndef f(x):\n    return 99999"
    cases.append(("verify-false-tampered-code", lambda p=p: verify(p) is False))
    base2 = generate(nohold_seed, 1.0)
    p = copy.deepcopy(base2)
    p["meta"]["asserted"] = p["answer"]["actual"]
    cases.append(("verify-false-tampered-asserted",
                  lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    cases.append(("helper-wrong-values",
                  lambda: all(_wrong_int(n, random.Random(n)) != n
                              for n in range(-3, 30))
                  and all(_wrong_str("ab", random.Random(n)) != "ab"
                          for n in range(10))))
    return cases
