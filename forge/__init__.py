# -*- coding: utf-8 -*-
"""forge-code: code reasoning graded by EXECUTION.

Oracle ladder level L3 — the interpreter itself is the judge.
"""
MODULES = {}
for _name in ("output_prediction", "bug_localization", "loop_count",
              "assertion_check", "string_transform"):
    try:
        _m = __import__("forge." + _name, fromlist=["x"])
        MODULES[_m.TYPE] = _m
    except ImportError:
        pass
