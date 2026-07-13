# Comparison results: TrustGrade vs published paradigms

All numbers below come from reimplementing each baseline **on one shared corpus**
(not copied across papers). Own-experiment values only; see
[`PROVENANCE.md`](PROVENANCE.md).

## Data scale behind the tables

| | |
|---|---|
| Objectives | 37 (combinational → sequential → protocol → clock-domain-crossing) |
| Submissions graded × graders | 221 × 5 = **1,105 grading decisions** |
| Faulty-feedback items × gate arms | 222 × 6 = **1,332 gating decisions** |
| Simulated-student API repairs | **666** DeepSeek calls (3 per item) |
| Total executed verdicts | **≈2,600**, all local Icarus Verilog, with Wilson CIs + exact McNemar/Fisher |
| Ground-truth guarantee | every valid item alpha-equivalence-verified; every mutant confirmed by a 2-seed × 128-cycle differential oracle |

Valid class n=137 (101 structurally-distinct alternatives); buggy class n=84;
faulty-feedback n=222 = 85 broken (36 lazy + 49 mutants, **9 property-evading**) + 137 valid.

## Grader comparison — RQ1 (accept-buggy / reject-valid on 221 submissions)

| Grader | FNR valid (n=137) | FNR alternatives (n=101) | FPR buggy (n=84) |
|---|---|---|---|
| **Property (ours)** | **0.000** [.000,.027] | **0.000** [.000,.037] | **0.107** [.057,.191] |
| Reference-output match | 0.007 [.001,.040] | 0.010 [.002,.054] | 0.131 [.075,.219] |
| Token similarity | 0.124 [.079,.190] | 0.168 [.108,.252] | 0.976 [.917,.993] |
| Structural similarity | 0.015 [.004,.052] | 0.020 [.005,.070] | 0.964 [.900,.988] |

Similarity graders accept 81–82 of 84 buggy submissions — unsafe at any
threshold (Fisher p ≈ 10⁻³³ vs property grader). Reference-matching falsely
rejects structurally-different valid solutions; the property grader rejects none.

## Six-arm gate comparison — RQ4 (222-item corpus; McNemar vs full gate)

| Gating condition (paradigm source) | Catch broken | Pass valid | Evaders (9) | Harmful delivered | McNemar vs full | Cost/check | Deterministic |
|---|---|---|---|---|---|---|---|
| Ungated (CodeAid'24 / Azaiz'24) | 0/85 | 137/137 | 0/9 | **85** | b=84,c=5, p=1.4e-19 | none | yes |
| Simulated student (PyFiXV'23 / GPT4Hints'24) | 6/85 | 130/137 | 1/9 | **79** | b=80,c=0, p=1.7e-24 | 3 LLM+3 sims | no |
| Affordable review (Dean-of-LLM'25) | 81/85 | **67/137** | 7/9 | 4 | b=69,c=1, p=1.2e-19 | ≈1.1k tokens | no |
| Frontier review (same paradigm) | 84/85 | 134/137 | 8/9 | 1 | b=3,c=5, **p=.73** | frontier tokens | no |
| Test-only execution (CodeTailor'24) | 76/85 | 133/137 | **0/9** | 9 | b=8,c=1, **p=.039** | ≈37 ms | yes |
| **Full execution gate (ours)** | **84/85** | 132/137 | **8/9** | **1** | — | ≈71 ms | yes |

## Backbone layer economics (§4.2)

L0 compile ≈9 ms → L1 property testbench ≈37 ms → L2 differential ≈28 ms;
end-to-end ≈75 ms/assessment. Of the 221 verdicts: L0 rejected 7, L1 rejected
68, L2 accepted 137 and escalated 9 to a human. L2 is the insurance layer that
catches the property-evading fault class (8/9) that a test-only gate misses (0/9).

## The one-paragraph verdict

The full execution gate **matches the strongest published paradigm** (frontier
LLM review) on accuracy — statistically indistinguishable, McNemar p=.73 — while
running on a free open-source simulator (≈71 ms, deterministic) instead of
frontier tokens. It is **significantly safer than the cheaper, scalable
paradigms**: vs ungated / simulated-student / affordable-review all p < 10⁻¹⁹,
and vs test-only p=.039 (the difference concentrated entirely in the 9
property-evading fixes it catches 8 of and test-only catches 0 of). It is the
only paradigm that is safe, fair, near-free, and deterministic at once.
