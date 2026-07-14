# Cross-domain test — our method vs other LLMs on MBPP (Python)

Ports the Verilog comparison to an open-source programming-education dataset
([MBPP](https://github.com/google-research/google-research/tree/master/mbpp),
974 basic Python problems, each with a reference solution and `assert` tests) to
answer: **on executable educational tasks, how does our execution gate compare to
other LLMs judging correctness?**

## Method

Construction-based ground truth, mirroring the Verilog corpus:

- **Correct class** (n=300) — each problem's reference solution (verified to pass
  its own `test_list`) plus an AST-roundtrip reformat variant that still passes.
- **Buggy class** (n=178) — AST-mutation-injected versions (swap `+`/`-`, flip
  comparisons, `and`/`or`, `+1` on integer constants, `*`→`+`), each **confirmed
  buggy** by the reference tests failing.
- 150 problems → **478 candidates**. `py_exec.py` is the executing backbone: it
  runs a candidate + the problem's asserts in an isolated subprocess with a
  timeout (the Python analog of the Verilog property testbench).

Arms (all judging byte-identical candidates):
- **Execution gate (ours)** — run the tests.
- **Token similarity** — Jaccard to the reference, threshold 0.8.
- **DeepSeek judge (affordable LLM)** — static correctness review, reasoning
  allowed then a verdict (no execution).
- **Claude judge (frontier LLM)** — same, run by Claude reviewers (static only).

## Results (`RESULTS.txt`)

| Method | Catch buggy (178) | Pass correct (300) | Harmful delivered | McNemar vs execution |
|---|---|---|---|---|
| **Execution gate (ours)** | 178/178 | 300/300 | 0 | — |
| Token similarity | 1/178 | 300/300 | 177 | p=1e-53 |
| DeepSeek judge (affordable) | 168/178 | **171/300** | 10 | p=2.9e-42 |
| Claude judge (frontier) | 178/178 | 299/300 | 1 | p=1.0 |

## Honest reading

- **Caveat on the execution gate's perfect score:** on MBPP the correct/buggy
  labels are *defined* by the same `test_list` the gate runs, so its 178/178 is
  tautological — execution is the oracle here, not a contestant. The meaningful
  comparison is among the *static* methods against that oracle.
- **Frontier LLM ≈ execution on common Python.** Claude's static judgment nearly
  matches execution (299/300 correct passed, all 178 bugs caught) — these are
  textbook patterns a frontier model knows cold. Its one "error" was rejecting a
  reformat variant it argued was genuinely mis-indented.
- **Affordable LLM over-rejects badly.** Even with reasoning allowed, DeepSeek
  passed only **171/300 (57%)** correct solutions — a 43% over-rejection rate —
  while catching most bugs. This replicates the Verilog affordable-review finding:
  review-based gating inherits the reviewer's competence, and at accessible price
  points that competence over-blocks valid work.
- **Similarity is useless** for correctness (1/178) — mutants are near-identical
  text.

**Where execution gating matters most is domain-dependent.** On common Python a
frontier LLM judge suffices; the gate's advantage over even frontier review is
largest in specialized, less-represented domains like HDL, where the Verilog
six-arm run showed frontier review still missing property-evaders (8/9) that the
execution gate catches. Execution stays reliable and free across both.

## Reproduce

```bash
python build_mbpp_corpus.py      # downloads MBPP, builds the 478-candidate corpus
python run_free_arms.py          # execution gate + similarity (free)
DEEPSEEK_API_KEY=... python run_ds_judge.py   # affordable LLM judge (key from env)
# frontier judge: run Claude over verdicts/ (static review, no execution)
python score_mbpp.py             # the table above
```
