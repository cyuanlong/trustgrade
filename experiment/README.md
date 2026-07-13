# `experiment/` — the original evaluation harness (as run)

This directory contains the **actual research code that produced the paper's
results**, exactly as it was run (CPU-only, Icarus Verilog + the DeepSeek public
API). It is research-grade, not library-polished; the cleaned, unit-tested
library API is in [`../src/trustgrade/`](../src/trustgrade), and the two agree by
construction on the algorithms.

## Pipeline

```
corpus_run.py          core: builds the construction-based corpus and runs the
                       four graders (PROP / REF-OUT / TEXT-SIM / STRUCT-SIM).
                       Also holds the shared primitives every other script imports:
                       sh(), compile_run(), prop_grade(), gen_ref_tb(), ref_trace(),
                       parse_ports(), the semantics-preserving variant generators,
                       is_alpha_equiv(), the mutation INJECTORS, and the differential
                       oracle (oracle_golden / mutant_is_buggy).
trustgrade.py          Module 1 — the assessment backbone: assess() = L0 compile ->
                       L1 property TB -> L2 differential-vs-reference, returning
                       ACCEPT / REJECT / UNCERTAIN with a layer and diagnosis.
slice_grader.py        the arbiter vertical slice (P1 exit evidence): PROP vs
                       REF-OUT vs TEXT-SIM on 3 structurally-diverse correct arbiters
                       + 2 broken — the false-negative-on-alternatives argument.
tutor_gate.py          feedback gate v1 (property-TB contract).
tutor_gate2.py         feedback gate v2 — the gate of §4.3: deliver iff (1) tutor
                       verdict agrees with the backbone on the student's code AND
                       (2) the tutor's corrected RTL earns a sound ACCEPT from the
                       FULL backbone; otherwise verifier-only fallback.
scaffold_validate.py   Module 2 — verified scaffolding: s1 compile, s2 checkpoint
                       PASS, s3 final step meets the real property TB.
build_gate_xl.py       builds the expanded ~250-item faulty-feedback corpus (all
                       objectives x all applicable mutation operators, oracle-
                       confirmed; flags the property-evading broken class).
run_exec_arms_xl.py    the two execution arms (full gate, test-only) on the corpus.
run_ds_arms_xl.py      the two DeepSeek arms (static review; simulated student).
score_gatexl.py        final six-arm scoring on the 222-item corpus.
paper_stats.py         inferential statistics: Wilson 95% CIs, exact McNemar on the
                       paired arms, Fisher exact, two-pass agreement.
build_submissions.py   \
diag_metric.py          }  supporting scripts (submission assembly, diagnosis-
score_judge.py          }  actionability metric, LLM-judge scoring, corpus
characterize.py        /   characterization).
```

## Data inputs (released on acceptance)

The scripts read a small set of JSON corpus files authored by the upstream KASE
generation pipeline; they are **not** in this repository because they derive from
course assignments (same non-redistribution constraint as any coursework), and
they are released here on acceptance:

| File | Contents |
|---|---|
| `hard_tasks.json`, `pool_tasks.json` | the 37 objectives: `golden_rtl`, `property_tb`, `buggy_rtl`, `interface` |
| `arb_bundle.json` | the arbiter bundle: 3 structurally-diverse correct + broken arbiters + the property TB |
| `tutor_outputs.json` | frozen LLM-tutor messages (verdict / explanation / corrected RTL) |
| `scaffolds.json` | frozen LLM-generated scaffolds |

Everything else (`corpus_cache.json`, `corpus_results.json`,
`trustgrade_results.json`, `gatexl_*.json`) is a **generated artifact** — it is
recreated deterministically by running the pipeline over the inputs above (the
LLM arms additionally need `DEEPSEEK_API_KEY`).

## Running (once the corpus JSONs are present)

```bash
export PYTHONPATH=.
python corpus_run.py            # graders + corpus_cache.json + corpus_results.json
python trustgrade.py            # backbone verdicts -> trustgrade_results.json
python slice_grader.py          # arbiter vertical slice
python build_gate_xl.py         # -> gatexl_items.json / gatexl_truth.json / batches
python run_exec_arms_xl.py      # -> gatexl_exec_verdicts.json   (needs iverilog)
DEEPSEEK_API_KEY=... python run_ds_arms_xl.py   # -> DeepSeek arm verdicts
python score_gatexl.py          # six-arm table
python paper_stats.py           # Wilson CIs / McNemar / Fisher
```

## A note on how this code was preserved

These files were authored in a working scratch space that was later cleared. They
were **recovered verbatim from the session transcript** (every write went through
a recorded tool call) and re-verified to compile. See
[`../docs/PROVENANCE.md`](../docs/PROVENANCE.md).
