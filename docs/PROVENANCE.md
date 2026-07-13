# Provenance: what is in this repository, and where it comes from

This note is deliberately explicit so a reviewer or reader can tell exactly which
artifacts are self-contained code and which depend on the (release-on-acceptance)
evaluation corpus.

## Fully self-contained — runs and verifies from this repo alone

| Path | Provenance | Verified |
|---|---|---|
| `src/trustgrade/backbone.py` | Reference implementation of Algorithm 1 (§4.2) and the L0/L1/L2 spec. | end-to-end on the arbiter example + `tests/` |
| `src/trustgrade/gate.py` | Reference implementation of Algorithm 2 (§4.3), checks C1 + C2. | `tests/test_backbone_gate.py` |
| `src/trustgrade/scaffold.py` | Reference implementation of Algorithm 3 (§4.4), conditions s1–s3. | `tests/test_backbone_gate.py` |
| `src/trustgrade/diagnosis.py` | The delta extractor (§4.5), first-failing-assertion rule. | exercised by the backbone tests |
| `src/trustgrade/stats.py` | Wilson CI, exact McNemar, Fisher exact, Cohen's kappa (§5.3). | `tests/test_stats.py` vs textbook values |
| `src/trustgrade/prompts.py`, `prompts/*.txt` | Appendix A, **verbatim**. | — |
| `examples/arbiter/property_tb.v` | The corpus round-robin-arbiter property testbench, **verbatim** (Appendix B). | compiles + runs |
| `examples/arbiter/{reference,alt_token,buggy_starvation}.v` | The three artifacts of the §4.2 running example, re-authored to match the described behaviour (rotating-pointer reference; a valid structurally-distinct alternative; the `base <= gidx` starvation bug). | reference/alt → ACC, buggy → REJ (the paper's verdicts) |
| `manuscript/`, `figures/` | The manuscript (EN + zh) and its figures. | — |
| `docs/claims_audit.md` | Evidence table auditing every external claim, with verbatim source quotes. | — |

## Corpus-dependent — released on acceptance

| Item | Why it is not in the repo now |
|---|---|
| The 37-objective corpus, the 221-item ground-truth submissions, and the 222-item faulty-feedback corpus | Derived from course assignments; governed by the same non-redistribution constraints as coursework. Released on acceptance per the manuscript's *Data and code availability* statement. The arbiter objective is included here in full as a worked example. |
| The frozen per-item verdicts of the six arms (used to compute the §5.4 tables) | Products of running the arms over that corpus (the deterministic arms with Icarus Verilog; the LLM arms with API calls). Re-derivable from the corpus + `arms.py`. |

## Reconstruction note

The experimental harness that produced the paper's numbers was authored in a
working scratch space that was not preserved. The code in `src/` is a faithful
re-implementation of the **published** algorithms and interfaces — not a copy of
that harness — and is verified to reproduce the algorithms' behaviour on the
worked example end-to-end. Where a number in the paper depends on the private
corpus or on model calls, this note says so rather than implying the repo
regenerates it bit-for-bit.
