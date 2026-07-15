# TrustGrade — consolidated experimental data (all runs)

Single source of truth for every number that may enter the manuscript. Three
experiment sets; all own-experiment, all reproducible from `../trustgrade/`.

---

## Set 1 — Primary Verilog corpus (course-derived; the manuscript's §5)

Corpus: 37 objectives, 221 submissions (137 valid incl. 101 alternatives; 84 buggy);
222-item faulty-feedback corpus (85 broken incl. 9 property-evaders; 137 valid).

### RQ1 graders (221 submissions)
| Grader | FNR valid (137) | FNR alt (101) | FPR buggy (84) |
|---|---|---|---|
| Property (ours) | 0.000 [.000,.027] | 0.000 [.000,.037] | 0.107 [.057,.191] |
| Reference match | 0.007 | 0.010 | 0.131 |
| Token similarity | 0.124 | 0.168 | 0.976 |
| Structural similarity | 0.015 | 0.020 | 0.964 |

### RQ4 six-arm gate (222 items) — McNemar vs full gate
| Condition | Catch broken | Pass valid | Evaders (9) | Harmful | McNemar |
|---|---|---|---|---|---|
| Ungated | 0/85 | 137/137 | 0/9 | 85 | b=84,c=5, p=1.4e-19 |
| Simulated student | 6/85 | 130/137 | 1/9 | 79 | b=80,c=0, p=1.7e-24 |
| Affordable review | 81/85 | 67/137 | 7/9 | 4 | b=69,c=1, p=1.2e-19 |
| Frontier review | 84/85 | 134/137 | 8/9 | 1 | b=3,c=5, p=.73 |
| Test-only | 76/85 | 133/137 | 0/9 | 9 | b=8,c=1, p=.039 |
| Full gate (ours) | 84/85 | 132/137 | 8/9 | 1 | — |

Backbone layer economics: L0 ≈9 ms, L1 ≈37 ms, L2 ≈28 ms, end-to-end ≈75 ms;
gate check ≈71 ms. Layer yields: L0 rej 7, L1 rej 68, L2 acc 137 + escalate 9.

---

## Set 2 — Public expansion corpus (NEW; fully redistributable)

130 newly-authored objectives across **14 design classes** (combinational,
sequential, FSM/protocol, datapath/CDC, arithmetic, memory, bus/serial protocol,
DSP, coding/ECC, bit-manipulation, advanced FSM, advanced sequential,
CDC/synchronizers, ALU/control), each iverilog-verified (golden→ACCEPT,
buggy→REJECT), independently re-checked 130/130. Built out to **131 objectives /
664 submissions** (402 valid incl. 272 alternatives; 262 buggy incl. 9 evaders).

### Graders (664 submissions)
| Grader | FNR valid (402) | FNR alt (272) | FPR buggy (262) | Fisher vs property |
|---|---|---|---|---|
| Property (ours) | 0/402 | 0/272 | 9/262 | — |
| Reference match | 1/402 | 1/272 | 16/262 | p=0.22 |
| Token similarity | 9/402 | 9/272 | 260/262 | p=1.8e-12 |
| Structural similarity | 1/402 | 1/272 | 255/262 | p=9.7e-13 |

Backbone: sound-verdict accuracy 654/656; valid delivered 401/402; buggy caught
253/262 by sound layers; 8 escalated. Deterministic gate arms (664-item):
- Ungated: catch 0/262, 262 harmful.
- Test-only: catch 253/262, 0/9 evaders, 9 harmful, pass 402/402.
- Full gate: catch 260/262, 7/9 evaders (L2), 2 harmful, pass 401/402.

### Six-arm gate on the earlier 152-item expansion subset (all paid arms run)
| Condition | Catch broken (64) | Pass valid (88) | Evaders (2) | Harmful | McNemar vs full |
|---|---|---|---|---|---|
| Ungated | 0/64 | 88/88 | 0/2 | 64 | p=3.6e-18 |
| Simulated student | 16/64 | 66/88 | 1/2 | 48 | p=6.1e-20 |
| Affordable review | 51/64 | 83/88 | 1/2 | 13 | p=7.6e-05 |
| Frontier review | 61/64 | 88/88 | 0/2 | 3 | p=0.62 |
| Test-only | 62/64 | 88/88 | 0/2 | 2 | p=1.0 |
| Full gate (ours) | 64/64 | 87/88 | 2/2 | 0 | — |

---

## Set 3 — Cross-domain: MBPP Python (NEW; open dataset)

478 candidates (300 correct = reference + reformat variant; 178 buggy =
AST-mutation-injected, oracle-confirmed by the reference tests). Python execution
backbone (`py_exec.py`).

| Method | Catch buggy (178) | Pass correct (300) | Harmful | McNemar vs execution |
|---|---|---|---|---|
| Execution gate (ours) | 178/178 | 300/300 | 0 | — (oracle here) |
| Token similarity | 1/178 | 300/300 | 177 | p=1e-53 |
| DeepSeek judge (affordable) | 168/178 | 171/300 | 10 | p=2.9e-42 |
| Claude judge (frontier) | 178/178 | 299/300 | 1 | p=1.0 |

**Caveat (state in manuscript):** on MBPP the labels are defined by the same
tests the gate runs, so the execution gate is the oracle, not a contestant; the
comparison is among the static methods against it.

**Cross-domain finding:** frontier LLM static judgment ≈ execution on common
Python; affordable LLM over-rejects 43% of correct code; similarity is useless.
The gate's advantage over even frontier review is domain-dependent — largest in
specialized domains (HDL), where frontier review still misses property-evaders.

---

## Totals for the paper
- 2 independent HDL corpora (37 + 130 = **167 objectives, 14 design classes**),
  **885 HDL submissions** graded; plus **478 Python candidates** (cross-domain).
- ≈**2,600 executed verdicts** on the primary set + **664 + 478** on the new sets.
- All paid LLM arms run (DeepSeek + Claude); all numbers reproducible from the
  public repo (github.com/cyuanlong/trustgrade).
