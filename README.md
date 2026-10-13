# forge-code

> **The interpreter is the judge.** Procedurally generated code-reasoning problems where every answer is graded by *actually executing the code* — never by another language model, never by string matching.

Part of the [forge family](https://github.com/chenhz01/forge-kit): [scireason-forge](https://github.com/chenhz01/scireason-forge) · [forge-agentic](https://github.com/chenhz01/forge-agentic) · [forge-sql](https://github.com/chenhz01/forge-sql) · [forge-security](https://github.com/chenhz01/forge-security) · [forge-optimize](https://github.com/chenhz01/forge-optimize).

## Why this exists

Code benchmarks are the most contaminated benchmarks on earth — SWE-bench-style suites leak into training corpora and quietly stop measuring anything. Every problem here is **born from a seed**: same seed, byte-identical problem; new seed, brand-new exam, on demand, forever. And grading is at the top of what we call the oracle ladder: the code shown in the problem is *run*, and the interpreter's output is the truth.

## Five task types (W1: 250 problems)

| Type | What it drills | Oracle |
|---|---|---|
| `output-prediction` | Trace a snippet, predict `result` | Real execution |
| `bug-localization` | Find the injected bug's line | Clean-vs-buggy differential execution |
| `loop-count` | Count iterations through nested loops | Instrumented execution |
| `assertion-check` | Will the assertion hold? | Execution + comparison |
| `string-transform` | Replay a transformation spec | Spec replay + execution cross-check |

## Quickstart

```bash
python cli.py generate --type all --per-type 50 --seed0 1000 --out data/w1.jsonl
python cli.py grade --file data/w1.jsonl        # SUMMARY: 250/250 passed
python self_test.py                             # SUMMARY: PASS 160/160
python -m bench.harness --file data/w1.jsonl --backend random   # chance level: 0.0%
```

A random-guess baseline scores **0.0%** — structured answers cannot be lucked into. Plug a real model via `python -m bench.harness --backend cmd --cmd "your-model-cli"`.

## Safety note

Execution is restricted to code our own templates generate (no imports, no while loops, bounded for-loops, restricted builtins). We never execute external code.

## When NOT to use

Open-ended dialogue scoring; frontier-model evaluation (scores saturate).

## License & contact

MIT — © zhengming contributors. Developer tooling, not professional advice. Contact: hcac4735@agent.qq.com
