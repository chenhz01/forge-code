# -*- coding: utf-8 -*-
"""forge.bug-localization — is there a bug, and on which line?

A correct snippet (2-5 arithmetic/string lines, >=4 template families) is
generated procedurally. With probability knob(difficulty, 0.5, 0.9) exactly
one bug is injected (a single operator or number changed); high difficulty
always injects, low difficulty leaves roughly half of the tasks bug-free.

Graded by EXECUTION: the oracle re-runs the clean and the published version
on 5 seed-derived random inputs and compares outputs. The claimed answer is
never trusted.
"""
import random
import re

from .common import make_id, knob, run_code

TYPE = "bug-localization"

_ALPHA = "abcdefgh"

_QUOTED_RE = re.compile(r'("[^"]*")')
_NUM_RE = re.compile(r"\d+")


# ---------------------------------------------------------------- templates

def _t_arith_two(rng, difficulty):
    x, y = rng.randrange(2, 21), rng.randrange(2, 21)
    op1 = rng.choice("+-*")
    op2 = rng.choice("+-*")
    op3 = rng.choice("+-*")
    k1, k2 = rng.randrange(2, 10), rng.randrange(2, 10)
    lines = [
        "x = %d" % x,
        "y = %d" % y,
        "x = x %s %d" % (op1, k1),
        "y = y %s %d" % (op2, k2),
        "result = x %s y" % op3,
    ]
    specs = [("x", "int", 2, 21), ("y", "int", 2, 21)]
    return lines, specs


def _t_arith_abs(rng, difficulty):
    x, y = rng.randrange(2, 30), rng.randrange(2, 30)
    k1, k2, k3 = rng.randrange(2, 8), rng.randrange(2, 12), rng.randrange(2, 6)
    lines = [
        "x = %d" % x,
        "y = %d" % y,
        "x = abs(x - y) + %d" % k1,
        "y = max(y, %d)" % k2,
        "result = min(x, y) * %d" % k3,
    ]
    specs = [("x", "int", 2, 31), ("y", "int", 2, 31)]
    return lines, specs


def _t_string(rng, difficulty):
    n = rng.randrange(6, 11)
    s = "".join(rng.choice(_ALPHA) for _ in range(n))
    k = rng.randrange(2, 6)
    suf = "".join(rng.choice(_ALPHA) for _ in range(2))
    lines = [
        's = "%s"' % s,
        "t = s.upper()",
        "t = t[::-1]",
        "t = t[:%d]" % k,
        't = t + "%s"' % suf,
        "result = t",
    ]
    specs = [("s", "str", 6, 10)]
    return lines, specs


def _t_string_mixed(rng, difficulty):
    n = rng.randrange(4, 9)
    s = "".join(rng.choice(_ALPHA) for _ in range(n))
    ch = rng.choice(_ALPHA)
    k1, k2 = rng.randrange(2, 6), rng.randrange(2, 5)
    lines = [
        's = "%s"' % s,
        "n = len(s) * %d" % k1,
        'c = s.count("%s")' % ch,
        "result = n + c * %d" % k2,
    ]
    specs = [("s", "str", 4, 8)]
    return lines, specs


TEMPLATES = (_t_arith_two, _t_arith_abs, _t_string, _t_string_mixed)


# ------------------------------------------------------- execution plumbing

def _input_sets(seed, specs):
    """5 fixed-seed-derived random input value sets (never trust answers)."""
    rng = random.Random("bug-localization-inputs|%d" % seed)
    out = []
    for _ in range(5):
        vals = []
        for _name, kind, p1, p2 in specs:
            if kind == "int":
                vals.append(rng.randrange(p1, p2))
            else:
                ln = rng.randrange(p1, p2 + 1)
                vals.append("".join(rng.choice(_ALPHA) for _ in range(ln)))
        out.append(vals)
    return out


def _run_variant(lines, specs, values):
    ls = list(lines)
    for idx, (spec, val) in enumerate(zip(specs, values)):
        if spec[1] == "int":
            ls[idx] = "%s = %d" % (spec[0], val)
        else:
            ls[idx] = '%s = "%s"' % (spec[0], val)
    return run_code("\n".join(ls))


def _outputs(lines, specs, sets):
    return [_run_variant(lines, specs, vals) for vals in sets]


# ------------------------------------------------------------- bug injector

def _segment(line):
    """Alternating (outside_quotes, text) spans of a line."""
    return [(i % 2 == 0, part) for i, part in enumerate(_QUOTED_RE.split(line))]


def _mut_candidates(line):
    """Candidate (kind, seg_index, start, end, replacement) mutations."""
    cands = []
    for seg_i, (outside, text) in enumerate(_segment(line)):
        if not outside:
            continue
        for old, new in (("+", "-"), ("-", "+"), ("*", "+")):
            start = 0
            while True:
                p = text.find(old, start)
                if p < 0:
                    break
                cands.append(("op", seg_i, p, p + 1, new))
                start = p + 1
        for m in _NUM_RE.finditer(text):
            n = int(m.group())
            for d in (1, -1, 2):
                if n + d >= 0:
                    cands.append(("num", seg_i, m.start(), m.end(), str(n + d)))
    return cands


def _apply(line, cand):
    _kind, seg_i, start, end, repl = cand
    parts = _segment(line)
    out = []
    for i, (outside, text) in enumerate(parts):
        if i == seg_i and outside:
            text = text[:start] + repl + text[end:]
        out.append(text)
    return "".join(out)


def _inject(lines, specs, sets, clean_outs, rng):
    """Change exactly one operator/number on a non-input line such that the
    buggy version still runs but disagrees with the clean version somewhere."""
    order = list(range(len(specs), len(lines)))
    rng.shuffle(order)
    for li in order:
        cands = _mut_candidates(lines[li])
        rng.shuffle(cands)
        for cand in cands:
            new_line = _apply(lines[li], cand)
            if new_line == lines[li]:
                continue
            trial = list(lines)
            trial[li] = new_line
            try:
                outs = _outputs(trial, specs, sets)
            except Exception:
                continue
            if outs != clean_outs:
                return trial, li + 1
    return None


# ------------------------------------------------------------ public API

def generate(seed, difficulty=0.5):
    rng = random.Random("bug-localization|%d" % seed)
    lines, specs = rng.choice(TEMPLATES)(rng, difficulty)
    sets = _input_sets(seed, specs)
    clean_outs = _outputs(lines, specs, sets)
    p = knob(difficulty, 0.5, 0.9)
    inject = rng.random() < p or difficulty >= 0.95
    bug_line = None
    buggy = list(lines)
    if inject:
        res = _inject(lines, specs, sets, clean_outs, rng)
        if res is not None:
            buggy, bug_line = res
    code_buggy = "\n".join(buggy)
    code_clean = "\n".join(lines)
    has_bug = bug_line is not None
    prompt = ("Does this version of the code contain a bug? If it does, on "
              "which line (1-based, counting the lines of the code shown "
              "below)?\n\n```python\n%s\n```" % code_buggy)
    if has_bug:
        solution = ("Running both the clean and this version on several "
                    "inputs shows they diverge: the bug is on line %d."
                    % bug_line)
    else:
        solution = ("Running this version on several inputs matches the "
                    "clean reference everywhere: there is no bug.")
    return {
        "id": make_id(TYPE, seed),
        "type": TYPE,
        "difficulty": float(difficulty),
        "seed": int(seed),
        "prompt": prompt,
        "answer": {"has_bug": has_bug, "bug_line": bug_line},
        "solution": solution,
        "meta": {"code_buggy": code_buggy, "code_clean": code_clean,
                 "bug_line": bug_line,
                 "specs": [[s[0], s[1], s[2], s[3]] for s in specs]},
    }


def verify(problem):
    """Re-EXECUTE clean vs published code on 5 derived inputs; the answer
    is only compared against what the oracle derives, never trusted."""
    try:
        meta = problem["meta"]
        clean = meta["code_clean"].split("\n")
        buggy = meta["code_buggy"].split("\n")
        specs = [(s[0], s[1], s[2], s[3]) for s in meta["specs"]]
        sets = _input_sets(int(problem["seed"]), specs)
        outs_c, outs_b = [], []
        for vals in sets:
            outs_c.append(_run_variant(clean, specs, vals))
            outs_b.append(_run_variant(buggy, specs, vals))
        if outs_c != outs_b:
            has_bug = True
            line = meta["bug_line"]
        else:
            has_bug, line = False, None
        ans = problem["answer"]
        if bool(ans.get("has_bug")) != has_bug:
            return False
        claimed = ans.get("bug_line")
        if not has_bug:
            return claimed in (None, 0)
        return claimed == line
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
    nobug = next(s for s in range(80) if not generate(s, 0.0)["answer"]["has_bug"])
    cases.append(("verify-true-nobug", lambda nobug=nobug: verify(generate(nobug, 0.0))))
    withbug = next(s for s in range(80) if generate(s, 0.9)["answer"]["has_bug"])
    base = generate(withbug, 0.9)
    p = copy.deepcopy(base)
    p["answer"]["bug_line"] = p["answer"]["bug_line"] + 1
    cases.append(("verify-false-wrong-line", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["answer"]["has_bug"] = not p["answer"]["has_bug"]
    cases.append(("verify-false-flipped-flag", lambda p=p: verify(p) is False))
    p = copy.deepcopy(base)
    p["meta"]["bug_line"] = p["meta"]["bug_line"] + 1
    cases.append(("verify-false-tampered-meta", lambda p=p: verify(p) is False))
    from .common import schema_ok
    cases.append(("schema-ok", lambda: schema_ok(generate(42, 0.3))))
    sets = _input_sets(9, [("x", "int", 2, 21)])
    cases.append(("input-sets-helper",
                  lambda: len(sets) == 5 and sets == _input_sets(9, [("x", "int", 2, 21)])))
    return cases
