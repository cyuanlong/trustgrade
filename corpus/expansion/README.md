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
