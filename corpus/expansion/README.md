# Expansion corpus — a large, fully public, independently-authored benchmark

**130 new HDL objectives** across **14 design classes**, authored for this
repository and **freely redistributable** (unlike the course-derived primary
corpus, which releases on acceptance). Each objective is construction-based
ground truth:

- `golden_rtl` — a correct reference implementation
- `property_tb` — a self-checking property testbench asserting spec-level
  invariants (prints `PASS` / `FAIL …`, with a timeout)
- `buggy_rtl` — the same module with one realistic functional bug
- every objective is verified end-to-end with Icarus Verilog: golden → ACCEPT,
  buggy → REJECT (`python verify_obj.py batches/<file>.json`) — 130/130 pass

The recovered harness (`../../experiment/corpus_run.py`) additionally, per
objective, generates alpha-equivalence-verified valid variants and
oracle-confirmed injected mutants, giving the full valid/buggy classes:
**131 objectives → 664 submissions** (402 valid incl. 272 alternatives; 262 buggy).

## Composition (130 objectives, 14 design classes)

| Class | n | file |
|---|---|---|
| Combinational | 8 | `batches/batch_comb.json` |
| Sequential | 8 | `batches/batch_seq.json` |
| FSM / protocol | 7 | `batches/batch_fsm.json` |
| Datapath / CDC | 7 | `batches/batch_cdc.json` |
| Arithmetic (multipliers, dividers, CLA/CSA, BCD, saturating) | 10 | `batches/batch_arith.json` |
| Memory (register file, RAM, FIFO-8, stack, CAM, circular buffer) | 10 | `batches/batch_mem.json` |
| Bus / serial protocol (UART-rx, SPI, skid, serializer, credit) | 10 | `batches/batch_proto.json` |
| DSP / datapath (FIR, MAC, integrator, comb, dot-product) | 10 | `batches/batch_dsp.json` |
| Coding / ECC (parity, Hamming(7,4) enc/dec, CRC-8, checksum) | 10 | `batches/batch_ecc.json` |
| Bit manipulation (ffs/fls, clz/ctz, reverse, rotate, isolate-lsb) | 10 | `batches/batch_bitmanip.json` |
| Advanced FSM (detectors, elevator, combo-lock, debounce) | 10 | `batches/batch_fsm2.json` |
| Advanced sequential (PWM, timers, watchdog, BCD chain) | 10 | `batches/batch_seq2.json` |
| CDC / synchronizers (3-flop, pulse/toggle sync, handshake, MCP) | 10 | `batches/batch_cdc2.json` |
| ALU / control (8-op ALU, flags, shifter, cond-eval, bit-field) | 10 | `batches/batch_alu.json` |

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

The primary corpus's findings replicate at scale on this independent benchmark
(131 objectives, 664 submissions).

### Graders

| Grader | FNR valid (n=402) | FNR alternatives (n=272) | FPR buggy (n=262) | Fisher vs property |
|---|---|---|---|---|
| Property (ours) | **0/402** | **0/272** | 9/262 | — |
| Reference-output match | 1/402 | 1/272 | 16/262 | p=0.22 |
| Token similarity | 9/402 | 9/272 | 260/262 | p=1.8e-12 |
| Structural similarity | 1/402 | 1/272 | 255/262 | p=9.7e-13 |

The property grader falsely rejects **0 of 402** valid submissions (including all
272 structurally-distinct alternatives); similarity grading accepts 255–260 of
262 buggy submissions — unsafe at any threshold. The property grader's only
residual is 9 `const+1` mutants that evade the property set (the R(Φ,∅) class).

### Backbone / execution gate (deterministic, free)

- Backbone sound-verdict accuracy **654/656**; valid delivered 401/402; buggy
  caught 253/262 by sound layers; 8 escalated to a human (never falsely accepted).
- Full execution gate on the 664-item gate corpus: catches **260/262** broken
  fixes, **7 of 9** property-evaders via the L2 differential layer, passes
  401/402 valid, delivers only **2** harmful (the residual R(Φ,H) that evades
  both the property set and the auto-generated differential harness).
- Test-only gate: 253/262, **0/9** evaders, 9 harmful. Ungated: 0/262, 262 harmful.

The paid LLM arms (DeepSeek review + simulated student, Claude frontier review)
were run in full on the earlier 152-item gate corpus (see git history / the
`arms/` verdicts) and can be re-run at this scale with
`DEEPSEEK_API_KEY=... python run_ds_arms_expansion.py` (key read from env, never
stored) plus the frontier-review batches.
