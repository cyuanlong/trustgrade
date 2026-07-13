# Expansion corpus — a second, fully public, independently-authored benchmark

30 new HDL objectives (plus the arbiter), authored for this repository and
**freely redistributable** (unlike the course-derived primary corpus, which
releases on acceptance). Each objective is construction-based ground truth:

- `golden_rtl` — a correct reference implementation
- `property_tb` — a self-checking property testbench asserting spec-level
  invariants (prints `PASS` / `FAIL …`, with a timeout)
- `buggy_rtl` — the same module with one realistic functional bug
- every objective is verified end-to-end with Icarus Verilog: golden → ACCEPT,
  buggy → REJECT (`python verify_obj.py batches/<file>.json`)

The recovered harness (`../../experiment/corpus_run.py`) additionally, per
objective, generates alpha-equivalence-verified valid variants and
oracle-confirmed injected mutants, giving the full valid/buggy classes.

## Composition (30 objectives, 4 design classes)

| Class | n | file | examples |
|---|---|---|---|
| Combinational | 8 | `batches/batch_comb.json` | ripple-carry adder, 4:1 mux, priority encoder, barrel rotate, bin↔gray, popcount |
| Sequential | 8 | `batches/batch_seq.json` | up/down counter, mod-10, SIPO shift, LFSR, edge detector, ring/Johnson/gray counters |
| FSM / protocol | 7 | `batches/batch_fsm.json` | "1011" detector, req/ack handshake, traffic light, UART-TX, LIFO, sync FIFO, vending |
| Datapath / CDC | 7 | `batches/batch_cdc.json` | 2-flop bus synchronizer, bit-reverse, ÷6 tick, accumulator, saturating MAC, running-max, gray counter |

Built out to full classes by the harness: **31 objectives, 152 submissions**
(88 valid incl. 58 alternatives; 64 buggy).

## Reproduce

```bash
cd ../../experiment
cp ../corpus/expansion/objectives.json hard_tasks.json
cp ../corpus/expansion/arb_bundle.json .
python corpus_run.py        # four graders + corpus_cache.json + corpus_results.json
python trustgrade.py        # L0/L1/L2 backbone
python ../corpus/expansion/expansion_stats.py   # Wilson CIs + Fisher vs property
```

## Result (see `RESULTS.txt` for the full run)

The primary corpus's findings replicate on this independent benchmark:

| Grader | FNR valid (n=88) | FPR buggy (n=64) | Fisher vs property |
|---|---|---|---|
| Property (ours) | 0/88 | 2/64 | — |
| Reference-output match | 1/88 | 3/64 | p=1.00 |
| Token similarity | 1/88 | 64/64 | p=9.1e-13 |
| Structural similarity | 1/88 | 62/64 | p=9.5e-13 |

Backbone (full execution gate): sound-verdict accuracy **149/149**, buggy caught
62/64, valid delivered 87/88, 3 escalated to a human (the 2 property-evading
`const+1` mutants + 1 legitimate alternative — escalated, never falsely
accepted). Similarity grading again accepts essentially every buggy submission
at any threshold; the property grader's only residual is the property-coverage
gap the differential layer is designed to close.

## Full six-arm gate comparison (all three paid LLM arms actually run)

Framed as a faulty-feedback corpus — 152 proposed "fixes" (88 valid OK, 64 broken
incl. 2 property-evaders) — and judged by all six paradigms. The DeepSeek review
and simulated-student arms were run against the public API; the frontier-review
arm was run by Claude reviewers doing static review only (no execution). Scored
by `score_expansion.py`; verdicts archived under `arms/`.

| Gating condition | Catch broken (64) | Pass valid (88) | Evaders (2) | Harmful delivered | McNemar vs full |
|---|---|---|---|---|---|
| Ungated | 0/64 | 88/88 | 0/2 | 64 | b=64,c=1, p=3.6e-18 |
| Simulated student | 16/64 | 66/88 | 1/2 | 48 | b=70,c=1, p=6.1e-20 |
| Affordable review (DeepSeek) | 51/64 | 83/88 | 1/2 | 13 | b=18,c=1, p=7.6e-05 |
| Frontier review (Claude) | 61/64 | 88/88 | 0/2 | 3 | b=3,c=1, **p=0.62** |
| Test-only execution | 62/64 | 88/88 | 0/2 | 2 | b=2,c=1, p=1.0 |
| **Full execution gate (ours)** | **64/64** | 87/88 | **2/2** | **0** | — |

The primary corpus's ordering replicates on this independent, fully-public
benchmark: the full gate delivers **zero** harmful fixes and catches both
property-evaders via the L2 differential layer; it is statistically
indistinguishable from frontier review (p=0.62) while being deterministic and
free, and significantly safer than affordable review, the simulated-student
paradigm, and ungated delivery (all p ≤ 8e-5). Reproduce the LLM arms with
`DEEPSEEK_API_KEY=... python run_ds_arms_expansion.py` (the key is read from the
environment and never stored).
