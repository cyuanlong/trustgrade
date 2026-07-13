# Claims audit — every literature number in the manuscript, verified against primary sources
**Date:** 2026-07-03. Method: three independent verification passes fetched each primary source and located verbatim supporting text. Source extractions archived in scratchpad (`codeaid.txt, azaiz.txt, codehelp.txt, cs50_2024.txt, cs50_2025.txt, audit/*.txt`; Yasir HTML renders). Verdicts: 29/36 VERIFIED as written; 3 substantive corrections and 4 scope corrections applied to both manuscripts (log below).

## Corrections applied
| # | Was | Now | Basis |
|---|---|---|---|
| 1 | over-validation "4.3–70.6%" | "6.5–70.6% (per-model; Paper B Table 2)" | true min = LLaMA-3.3 6.47% (N<50 flag); 4.3 leaked from F1 range 4–19% |
| 2 | CodeTailor "98% correct puzzles" | 98% = generated *solutions* correct; unit-test gate + closeness check; fallback ⇒ delivered puzzles always from correct code | §5.2.1/§4.1.3 of arXiv:2401.12125 |
| 3 | CS50 "39% endorsed **unmodified**" | "39% endorsed" + authors' caveat that this likely understates accuracy | SIGCSE'24 §5.2 verbatim |
| 4 | LeanTutor "≈57% accurate" | "≈57% at tactic level (whole-proof 18%)" | Table 1 of arXiv:2506.08321 |
| 5 | JudgeBench "LLM judges 50.9%" | "vanilla-prompted GPT-4o judge 50.86%" (Arena-Hard prompt: 56.57%) | Table 1 of arXiv:2410.12784 |
| 6 | Counterfeit "open models ≈60%" | "CodeLlama-34B, DeepSeek-Coder-33B **and GPT-3.5** ≈60%" | Fig. 3 discussion of arXiv:2402.19475 |
| 7 | CodeAid "prompt updates improved" | "refined prompts **together with model upgrade** raised 74%→87%" | §5.1.4/§6.2.1 of arXiv:2401.11314 |
| 8 | Yasir hybrid "deterministic components" | paper's own term "KG-grounded" | Abstract/Discussion of arXiv:2605.16207 |

## Verified as written (selection; full verbatim quotes in audit transcripts)
- CodeAid: 700-student C course, 12 weeks (Abstract); 1,749 analyzed samples (§6.2.1; methods say 1,750 — noted); 79% overall correct (1,386/1,749); 63% Help Fix Code (214/340).
- Azaiz: 165 outputs (55×3, Table 2); 52% complete-and-fully-correct / 60% only-correct-corrections; 22% inconsistencies; "does not seem to be advisable" (§5 Discussion).
- CS50.ai: ≈211,000 users / 10M queries by mid-Nov 2024 ($1.50/student/yr); staff audit 88% curricular (22/25, Summer'23); instruction dilution 22% of 10M messages / 48% of 1.3M conversations (§2.1.1, SIGCSE TS'25).
- CodeHelp: 52 students; perceptions only; no correctness audit (confirmed by absence + §4 limitations).
- Yasir'26b: 10,836 pairs = 516×7×3; states from real logs (solutions LLM-simulated — wording kept precise); over-rejection 12.77–91.07%; η²>0.95 vs η²<0.01 verbatim; Teacher condition = full solution, no repair.
- Yasir'26a: "+10–14pp … degrades 4–6pp" verbatim (Conclusion; Results reports +35pp vs different baseline — we cite the Conclusion sentence); −5.84/−4.46pp derived from Table 2 (flagged as derived); thresholds <70% / >84–85%; "Verification Over-Specification" verbatim; Judge = an LLM that "either enhances or overrides" feedback.
- PyFiXV: 76.0%@31.2% (TigerJython), 72.4%@64.2% (Codeforces) — Fig. 6a.
- GPT4Hints: 94.7/97.6/95.5% @ 76.0/87.5/73.3% — Fig. 6; GPT-3.5 simulated-student gate, execution-checked (§3.3).
- Huang: GSM8K 95.5→91.5→89.0 (Table 3). CRITIC: both quoted sentences verbatim (§1, §4.2).
- VerilogEval-v2: GPT-4o 63% spec-to-RTL pass@1 (Abstract); scoped to single-turn single-model.

## Known residual caveat
- RTL-SMARTIE (GLSVLSI'26): full text paywalled; manuscript uses the qualifier "as far as its available text shows" for the no-gate claim. To resolve before submission.
