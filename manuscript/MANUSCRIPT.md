# Verify Before You Teach: An Execution-Gated Framework and System for Trustworthy LLM Tutoring in Digital Hardware Design Education

**Target venue:** Computers and Education: Artificial Intelligence (CAEAI)
**Draft v2 — 2026-07-01.** All statistics from archived artifacts (§ Data availability). Figures appear at their positions in the text (sources in `figures/`).

---

## Abstract

Large language model (LLM) tutors now serve hundreds of thousands of students, yet audits of deployed systems consistently find that a substantial fraction of their feedback is technically incorrect, that repair-oriented help is the weakest category, that only a minority of unsupervised answers withstand staff review, and that models systematically validate incorrect student work. Because erroneous feedback is delivered fluently and confidently, learners are poorly placed to detect it, and prompt-level guardrails have been shown to erode at scale. This paper argues that in disciplines whose artifacts are machine-checkable, feedback reliability is an engineering choice rather than a model-capability lottery. We contribute (1) a design framework for *verification-gated tutoring* — four principles under which no AI-generated verdict, explanation, fix, or scaffolding step reaches a learner without validation by an executing verifier; (2) TrustGrade, a reference implementation for digital hardware design (Verilog) education, combining a layered assessment backbone (compilation, property-based testbenches, differential testing) with a feedback gate and a scaffold validator; and (3) a technical evaluation on a 221-submission corpus with construction-based ground truth. The backbone delivered verifier-backed verdicts for 95.9% of submissions (95% CI [92.4, 97.8]) at 99.5% accuracy [97.4, 99.9]; the gate intercepted 100% of harmful feedback across three adversarial tutor-failure models (76/76, [95.2, 100]) at ≈71 ms per check; and all 36 delivered scaffold steps were executable with all 12 final steps provably satisfying the assignment contract. We further reimplemented five gating paradigms from the literature and ran all six conditions on an identical 222-item corpus whose 85 faulty fixes include nine that evade the property tests: the full execution gate was statistically indistinguishable from a frontier-LLM review gate on accuracy (McNemar exact p = .73) at near-zero cost; it significantly outperformed test-only gating (p = .039), the difference lying in the property-evading class (8/9 vs. 0/9 caught); an affordable LLM reviewer wrongly withheld 51% of valid feedback; and a faithful reimplementation of the strongest published gate — simulated-student validation — proved blind to code artifacts, delivering 79 of 85 harmful fixes. These findings replicate on a second, independently-authored corpus of 130 objectives spanning fourteen design classes (664 submissions, released in full), and a cross-domain check on introductory Python (MBPP) both extends the mechanism beyond hardware and bounds it: the execution gate stays reliable at near-zero cost while an affordable LLM reviewer over-rejects 43% of correct solutions — though a frontier reviewer nearly matches execution on those textbook tasks, locating the gate's largest advantage in specialized, sparsely-represented domains such as HDL. We position execution gating as the deterministic-diagnosis half of the hybrid architecture that recent evaluations of LLM tutors call for, and discuss implications for equitable, trustworthy AI in engineering education.

**Keywords:** intelligent tutoring systems; large language models; automated assessment; formative feedback; trustworthy AI; hardware design education

---

## 1. Introduction

Generative AI tutoring has crossed from laboratory demonstrations into routine educational infrastructure. Harvard's CS50 assistant answered roughly ten million queries from over two hundred thousand learners in a single academic year (Liu et al., 2025); classroom assistants such as CodeAid ran for full semesters in large programming courses (Kazemitabaar et al., 2024); and commercial tutors are being procured at institutional scale. The pedagogical promise is real — immediate, personalized, always-available formative feedback is among the most powerful levers on learning (Hattie & Timperley, 2007) — but the same deployments that demonstrate the promise also quantify a structural weakness. LLM feedback is *not reliably correct*, and its errors arrive wrapped in the same fluent confidence as its successes.

The published record is consistent on this point. In CodeAid's audited classroom deployment, a substantial share of responses — and of repair-oriented help in particular — was technically incorrect (Kazemitabaar et al., 2024). An independent audit of GPT-4-generated feedback on authentic introductory-programming submissions found that only about half was fully correct and complete and that a noticeable fraction contradicted itself, leading its authors to advise against unsupervised deployment (Azaiz et al., 2024). In CS50's forum deployment, only a minority of the assistant's answers were endorsed by human staff, and the system's prompt-level "no code" guardrail was progressively diluted at scale despite explicit instructions (Liu et al., 2024, 2025). Most recently, a large-scale evaluation of LLM tutoring agents on logic proofs found that models systematically validate incorrect student solutions and reject valid but non-standard ones, that model choice explains nearly all of the variance in feedback quality, and that supplying the model with the full solution does not repair the failure — leading the authors to recommend hybrid architectures in which KG-grounded components handle diagnosis while LLMs support scaffolding and dialogue (Yasir et al., 2026b).

For education these numbers carry more weight than equivalent error rates would in general software assistance. Feedback that misdiagnoses an error, validates a broken solution, or "corrects" code into a subtly different bug does not merely fail to help: it installs misconceptions with the full authority of the tutor's voice, and formative-feedback research has long established that learners act on confident feedback largely uncritically (Shute, 2008). Automation bias compounds the effect for AI tutors specifically. The mitigation strategies in deployed systems to date form a spectrum of trade-offs: prompt-level constraints erode at scale (Liu et al., 2025); human endorsement queues (CS50's forum) reintroduce precisely the expert labor AI was meant to conserve; and gating LLM output with *another LLM* (Phung et al., 2023, 2024) inherits the reviewing model's own fallibility — a serious concern given converging evidence that LLMs cannot reliably validate outputs without external signals (Gou et al., 2024; Huang et al., 2024; Kamoi et al., 2024), that LLM judges perform near chance on correctness-grounded comparisons (Tan et al., 2025), and that models are unreliable at statically detecting plausible-but-wrong code (Gu et al., 2024).

There is, however, a family of disciplines in which this dilemma dissolves: those whose artifacts have executable semantics. A student's Verilog design can be compiled, simulated against testbenches that assert the *behavioral invariants* of the learning objective, and differentially tested against a reference implementation — deterministically, in milliseconds, at effectively zero marginal cost. Digital hardware design is also a discipline of acute educational importance, given the global shortage of integrated-circuit design talent and national-scale investments in semiconductor workforce development; yet the tooling lags the need. The only published AI tutor for register-transfer-level (RTL) design evaluates student code with an LLM-generated rubric and, as far as its available text shows, no verification gate (RTL-SMARTIE, GLSVLSI 2026), and our systematic search across 2023–2026 venues found no published tutoring system, in any domain, that machine-verifies every piece of feedback by execution before delivery (§2.5).

The central problem this paper addresses is therefore: *how should an LLM-based tutoring system be architected so that the reliability of what reaches the learner does not depend on the reliability of the LLM?* Our answer has three parts, mirroring the framework–instance–evaluation structure that design-oriented work in this journal has established (Pozdniakov et al., 2024):

1. **A design framework** for verification-gated tutoring: four principles (§3) under which the LLM acts as an explainer while executing verifiers act as the authority, every delivered artifact is either verified or explicitly labeled unverified, gates validate-or-withhold but never rewrite, and assessment accepts the entire space of valid solutions rather than a single reference.
2. **A reference implementation**, TrustGrade (§4), instantiating the framework for Verilog education: a three-layer executing assessment backbone, a feedback gate that cross-checks every LLM tutoring message, a validator that certifies LLM-generated multi-step scaffolds, and a diagnosis layer that turns verifier signals into formative feedback.
3. **A technical evaluation** (§5) on a 221-submission corpus with construction-based ground truth and a 222-item adversarial feedback corpus, in which we reimplement five gating paradigms from the literature and run all six conditions on identical items with exact inferential statistics; we then replicate the study on a second, independently-authored corpus of 130 objectives across fourteen design classes (664 submissions; §5.5) and test cross-domain transfer on introductory Python (§5.6).

We state our claims' boundaries explicitly. On our corpora, a frontier LLM reviewer matched the execution gate's accuracy (McNemar exact p = .73 and p = .62 on the two HDL corpora; p = 1 on Python); the execution gate's advantage over frontier-model review is cost, determinism, and contract-backed guarantees rather than raw detection, and — as the cross-domain check makes explicit (§5.6) — that detection advantage is largest in specialized, sparsely-represented domains such as HDL and small on textbook Python. Our evaluation is technical and adversarial, not a classroom study (§7). And the approach transfers only to disciplines with machine-checkable semantics — which programming, hardware design, and formal mathematics are, and essay writing is not.

The remainder of this paper is organized as follows. Section 2 reviews LLM tutoring reliability, feedback-gating approaches, the self-correction literature, and AI in hardware-design education, closing with the research gap. Section 3 develops the design framework and derives our evaluation constructs from formative-feedback theory. Section 4 presents TrustGrade. Section 5 reports the evaluation questions, corpus, procedures, statistical methods, and results. Section 6 discusses findings and implications; Section 7 states limitations and future work; Section 8 concludes.

---

## 2. Related work

### 2.1 LLM tutoring systems and the reliability of their feedback

Deployed LLM assistants for programming education form the empirical backdrop of this work. CodeAid (Kazemitabaar et al., 2024) served a large C-programming course for a full semester with prompt-engineered pedagogical constraints; a thematic audit of sampled usages found that a substantial share of responses was technically incorrect, with repair-oriented help markedly worse, and mid-semester updates (refined prompts together with a model upgrade) improved but did not eliminate the errors. CodeHelp (Liffiton et al., 2023) contributed a three-stage prompt "guardrail" pipeline but reported student perceptions rather than a correctness audit. CS50.ai (Liu et al., 2024, 2025) is the largest documented deployment; its audits are sobering both for accuracy — only a minority of forum answers earned staff endorsement — and for guardrail durability, with code-bearing responses persisting at scale despite an explicit no-code instruction ("instruction dilution"). Azaiz et al. (2024) provide the cleanest standalone estimate of unsupervised GPT-4 feedback quality on real submissions, finding barely half fully correct. Beyond programming, Yasir et al. (2026a, 2026b) evaluated LLMs as logic-proof tutors on a benchmark derived from real student interaction logs: models near-perfectly confirm optimal work but fail precisely where feedback matters, over-validating incorrect solutions and over-rejecting valid alternatives at rates that vary enormously across models; and an LLM judge empowered to rewrite feedback helps only weak tutors while measurably degrading strong ones, through what the authors call verification over-specification (Yasir et al., 2026a). Collectively this literature establishes the problem our framework targets: the failure is architectural, not promptable away.

### 2.2 Gating and validating LLM feedback before delivery

A smaller line of work interposes a validator between the LLM and the learner. PyFiXV (Phung et al., 2023) validates generated explanations of Python syntax errors by asking a second model to reproduce the fix from the explanation, exposing a tunable precision–coverage trade-off in which precision is bought by discarding a large share of feedback. GPT4Hints-GPT3.5Val (Phung et al., 2024) enriches the generator's prompt with executed failing-test information and gates each hint with a GPT-3.5 "simulated student"; it attains the highest precision among published gates while still withholding a nontrivial fraction of feedback — and it remains, notably, an *LLM* gate. CodeTailor (Hou et al., 2024) execution-gates one artifact type in Python — LLM-generated personalized solutions for Parsons puzzles — on passing all integrated unit tests plus a closeness check, with failing candidates falling back to a verified common solution so that delivered puzzles are always built from correct code. LeanTutor formally verifies feedback for mathematics through the Lean proof assistant, but its natural-language-to-Lean entry point is itself unverified and error-prone, relocating rather than removing the trust problem. Retrieval and knowledge-graph grounding reduce hallucination in generated feedback but provide no delivery-time guarantee (Nongkhai et al., 2026). Daheim et al. (2024) train a verifier that *conditions* feedback generation on the detected error step (soft steering, no hard withhold), and "Dean of LLM Tutors" (2025) screens tutor feedback with LLM evaluators. Relative to all of these, the present work differs in three ways: the gate is a *deterministic executing verifier* rather than a model; it covers *all* student-facing artifact types (verdicts, explanations, fixes, scaffold steps) rather than a single one; and it is instantiated in a domain — hardware design — where execution against behavioral contracts is the discipline's own notion of correctness.

### 2.3 Why the LLM cannot be its own gate

The self-correction literature explains why LLM-gated designs inherit fragility. CRITIC (Gou et al., 2024) finds that "exclusive reliance on self-correction without external feedback may yield modest improvements or even deteriorate performance," and specifically that program repair without interpreter feedback is "limited and unstable." Huang et al. (2024) show that intrinsic self-correction *reduces* reasoning accuracy once ground-truth-label stopping is removed. Kamoi et al. (2024) survey the field and attribute reported successes to hidden oracle signals. On code specifically, Gu et al. (2024) show that models classify "counterfeit" (plausible-but-wrong) programs unreliably — several near chance — and Chen et al. (2025) show that self-generated tests bias self-debugging. LLM-as-judge studies generalize the point: even frontier judges perform near chance on correctness-grounded response pairs (Tan et al., 2025), with systematic biases cataloged across many dimensions (Ye et al., 2025). This body of evidence generates the central prediction the gating-condition comparison of §5.4 tests: review-based gates should track the reviewing model's capability, while execution-based gates should not.

### 2.4 AI in hardware-design education

Hardware description language (HDL) education has strong non-AI tooling — HDLBits popularized simulation-judged practice, and VPLAS (2025) reports a guided-workflow system with rule-based grading — but thin AI tooling. On the generation side, benchmarks such as VerilogEval (Liu et al., 2023) and RTLLM (Lu et al., 2024) evaluate LLM RTL synthesis with testbench execution — where even frontier models remain far from reliable — and training loops that exploit testbench feedback are now standard for code generation (e.g., VeriReason, 2026). Education-facing AI is nascent: RTL-SMARTIE (GLSVLSI 2026) offers a multi-agent LLM tutor whose evaluation mode scores student Verilog against an LLM-generated rubric; its available description reports no execution or formal gate on the feedback path. The irony motivating our work is that execution verification is ubiquitous in HDL *engineering* practice and in LLM *benchmarking*, yet absent from HDL *tutoring*.

### 2.5 Research gap and contribution

Synthesizing §2.1–2.4: (i) ungated LLM tutoring feedback carries error and guardrail-dilution rates that formative-feedback theory says learners will absorb (Kazemitabaar et al., 2024; Azaiz et al., 2024; Liu et al., 2025; Yasir et al., 2026b); (ii) existing gates are prompt-level (erode), human (do not scale), or LLM-based (inherit model fallibility, as §2.3 predicts and §5.4 confirms for affordable models); (iii) execution-gating exists only for single artifact types outside our domain; and (iv) no published system in HDL education — or, to our knowledge, any domain — machine-verifies *every* student-facing feedback artifact by execution before delivery. The contribution of this paper is the framework, reference system, and evaluation that fill this gap, with an explicit accounting of where the approach's guarantees end.

---

## 3. Problem formulation and the verification-gated tutoring framework

This section formalizes the objects the system manipulates (§3.1), states the delivery problem that ungated LLM tutoring leaves unsolved (§3.2), presents the four design principles as formal requirements (§3.3), and derives the framework's guarantees as propositions whose proofs are by construction (§3.4). Section 3.5 then maps the formal machinery onto the constructs of formative-feedback theory, which the evaluation in §5 measures. Throughout, a running example — the 4-way round-robin arbiter objective from our corpus — grounds each definition in real course data.

### 3.1 Setting and notation

**Definition 1 (Learning objective).** A learning objective is a tuple `o = (σ, I, r, Φ, H)` where `σ` is the natural-language specification; `I` the module interface (port names, directions, widths); `r` a reference implementation; `Φ = {φ₁,…,φₖ}` a finite set of *executable behavioral properties*, realized as a self-checking testbench that drives the interface and asserts each `φⱼ` over the resulting trace; and `H` a *differential harness*, i.e., a stimulus generator and observation window over `I`'s outputs.

*Running example.* In the arbiter objective, `σ` requires one-hot grants rotating fairly among four requesters; `I = (clk, rst_n, req[3:0], grant[3:0])`; `Φ` contains three properties — `φ₁` (mutual exclusion): `onehot0(grant)` at every cycle; `φ₂` (no empty grant): `grant ∧ ¬req = 0`; `φ₃` (bounded wait): a continuously asserted `req[i]` receives `grant[i]` within `N+2` cycles — asserted by the testbench over randomized and held-request stimulus. Across the 37 objectives in our corpus (12 protocol/flow-control, 12 sequential, 7 clock-domain-crossing, 6 combinational), testbenches carry a median of 3 assertion sites (range 1–11).

Let `S` denote the space of submissions (Verilog sources declaring interface `I`). Ground truth is defined against the *ideal* contract: writing `Φ*` for the (in general infinite) set of behavioral requirements entailed by `σ`, a submission `s ∈ S` **conforms** to `o` iff `s ⊨ Φ*`. The executable set is a finite under-approximation, `Φ ⊆ Φ*`; this inclusion — properties assert only requirements actually entailed by the specification — is an authoring obligation we call *contract validity*, and it is the single assumption on which all soundness results below rest. We write `s ⊨ Φ` when the property testbench passes on `s`, `compiles(s)` for successful elaboration, and `s ≡_H r` when `s` and `r` produce identical observation sequences under `H`.

**Definition 2 (Grader; error notions).** A grader is a function `V : S → {ACC, REJ}` (or a three-valued variant, below). Against ground truth, its **false-negative rate** `FNR = P(V(s) = REJ | s conforms)` measures *unfairness* — valid work rejected — and its **false-positive rate** `FPR = P(V(s) = ACC | s does not conform)` measures *unsafety* — buggy work accepted. Section 5.4 estimates both, with the valid class deliberately including structurally diverse implementations so that FNR captures the penalty a grader imposes on legitimate design freedom.

### 3.2 The delivery problem

A tutoring pipeline emits *artifacts* to the learner: verdicts, explanations, proposed fixes, scaffold steps. An LLM tutor is a stochastic generator `g : (σ, s, context) → m` producing messages `m = (v_t, e, f)` — a claimed verdict, an explanation, and a proposed corrected implementation. The deployments audited in §2.1 implement the *identity delivery policy*: whatever `g` emits reaches the learner, so the probability that a harmful artifact — a wrong verdict, a non-conformant fix, an unachievable practice step — reaches the learner equals `g`'s own error rate, which is model-dependent, unobservable at delivery time, and empirically substantial in precisely the categories that matter most (Kazemitabaar et al., 2024; Yasir et al., 2026b).

The **delivery problem** is to design a delivery policy `D` such that the probability of harmful delivery is bounded by quantities of the *contract* `(Φ, H)` — inspectable, improvable engineering artifacts — and is *independent of* `g`. The LLM's quality may then affect how often rich feedback is delivered (coverage), but never the correctness of what is delivered.

### 3.3 Design principles as formal requirements

**P1 (Verifier authority).** Every correctness-bearing predicate over artifacts — `conform(s)?`, `conform(f)?`, "is step `i` achievable?" — is evaluated by executing verifiers; `g` is never the evaluator of record. *Grounding:* the architectural failure identified by Yasir et al. (2026b) — nearly all feedback-classification variance explained by model choice — makes any `g`-dependent evaluator a lottery; P1 removes `g` from the trusted base entirely.

**P2 (No unverified confidence).** The codomain of the delivery policy is `{verified content} ∪ {explicitly-flagged uncertainty}`: formally, every delivered artifact `a` carries a status `st(a) ∈ {VER, UNC}`, and `st(a) = VER` only if an executing check backs `a`. The dangerous quadrant — unverified content presented with tutorial authority, which Shute's (2008) validity analysis identifies as actively harmful — is unreachable by construction.

**P3 (Validate-or-withhold).** The gate's action space is `{deliver(m), withhold(m)}`; it has no rewrite action. This is the formal difference between a *gate* and the LLM *judge* of Yasir et al. (2026a), whose harm pathway — degrading already-correct feedback by rewriting it more abstractly — requires an action our gate does not possess.

**P4 (Solution-space completeness).** Assessment predicates are stated over behavior entailed by `σ` (i.e., membership in `Φ*`-satisfaction), never over similarity to `r`. Consequently every implementation of the contract — including strategies the instructor did not anticipate — is acceptable, operationalizing assessment validity for divergent solutions (cf. the high over-rejection of valid alternatives by LLM tutors; Yasir et al., 2026b).

### 3.4 Verdicts, gates, and guarantees

**Definition 3 (Layered backbone verdict).** The backbone verdict `V_B : S → {ACC, REJ, UNC}` is

```
V_B(s) = REJ                    if ¬compiles(s) ∨ s ⊭ Φ          (L0, L1)
       = ACC                    if s ⊨ Φ ∧ s ≡_H r               (L2 agree)
       = UNC                    if s ⊨ Φ ∧ s ≢_H r               (L2 disagree)
```

with a watchdog timeout treating non-terminating simulation as `s ⊭ Φ` (a hang violates every liveness-style property's bounded-response reading). The three-valued design is essential: L1 alone would grant P4's freedom but miss invariant-evading bugs; L2 alone would be a reference-matcher violating P4; their *disagreement region is exactly the class the system must not silently decide*.

**Proposition 1 (Rejection soundness).** *If contract validity holds (`Φ ⊆ Φ*`, with testbench stimulus within `σ`'s operating conditions), then `V_B(s) = REJ ⇒ s` does not conform.*
*Proof.* `V_B(s) = REJ` means `¬compiles(s)` (non-conformant trivially, as `s` realizes no behavior over `I`) or the testbench exhibits a trace on which some `φⱼ ∈ Φ` fails. Since `φⱼ ∈ Φ*` and the trace lies within the contract's operating conditions, `s ⊭ Φ*`. ∎

**Proposition 2 (Acceptance-risk characterization).** *If `V_B(s) = ACC` and `s` does not conform, then every behavioral divergence of `s` from the contract is invisible to both `Φ`'s testbench traces and `H`'s observation window.*
*Proof.* `ACC` requires `s ⊨ Φ` and `s ≡_H r`. Any requirement `φ ∈ Φ* \ Φ` violated by `s` produces, by assumption of violation, some distinguishing trace; if that trace were generated by the `Φ`-testbench, `s ⊭ Φ`; if its divergence were observable under `H`, then since `r ⊨ Φ*`, `s ≢_H r`. Both contradict `ACC`. ∎

Proposition 2 defines the **residual class** `R(Φ, H)` — non-conformant submissions whose defects evade both checks — which is the *entire* exposure of the architecture, is shrunk monotonically by adding properties or widening `H`, and is estimated empirically at 1/212 sound verdicts in §5.4 (RQ1). This is the formal content of the claim that reliability becomes an engineering choice: the exposure is a measurable property of two inspectable artifacts, not of a model.

**Definition 4 (Feedback gate).** For tutor message `m = (v_t, e, f)` about submission `s`, the gate is

```
G(m, s) = DELIVER(m)                       if v_t = V_B(s) ∧ V_B(f) = ACC     (C1 ∧ C2)
        = FALLBACK(V_B(s), δ(s))           otherwise
```

where `δ(s)` is the diagnosis extractor of §4.5. Scaffold delivery is gated analogously: a step sequence `⟨(g_i, h_i, r_i, c_i)⟩ᵢ₌₁..ₙ` (goal, hint, step reference, checkpoint testbench) is delivered only if every pair `(r_i, c_i)` compiles and passes and the final reference meets the real contract, `r_n ⊨ Φ`.

**Proposition 3 (No unverified authority).** *Under `G`, every artifact reaching the learner is either (i) a backbone verdict and diagnosis, backed by Propositions 1–2; (ii) an LLM message whose verdict equals the backbone's and whose fix satisfies `V_B(f) = ACC`; or (iii) explicitly labeled `UNC`. In particular, a delivered fix that is nonetheless non-conformant lies in `R(Φ, H)`.*
*Proof.* By case analysis on the delivery paths of Definition 4 and Figure 8: the only route by which LLM content reaches the learner is `DELIVER`, whose guard imposes (ii); all other paths emit backbone-generated content (i) or the `UNC` escalation (iii). The final claim instantiates Proposition 2 at `f`. ∎

**Corollary 1 (Model-independence).** *The bound of Proposition 3 contains no term depending on the generator `g`. `g`'s quality determines only the delivery rate `P(C1 ∧ C2)` — i.e., how often learners receive rich LLM feedback rather than the verifier fallback — never the soundness of delivered content.*

Corollary 1 is the framework's central claim, and it is falsifiable: §5.4 (RQ4) tests it by holding the corpus fixed and swapping gate mechanisms — the execution gate's interception is invariant, while review-based gates track the reviewing model (frontier: comparable; affordable: 5 harmful deliveries and 62% over-blocking).

### 3.5 From feedback theory to measurable constructs

Hattie and Timperley's (2007) model requires feedback to answer *Where am I going?*, *How am I going?*, and *Where to next?*. The formal machinery turns each into a measurable requirement: answering "How am I going?" validly is verdict correctness — coverage and accuracy of `V_B` (RQ1); answering it *informatively* requires `δ(s)` to name the violated `φⱼ` with observed evidence — diagnosis actionability (reported with RQ1); answering "Where to next?" safely requires delivered fixes and steps to satisfy the contract — gate interception (RQ2) and scaffold validity (RQ3). Nicol and Macfarlane-Dick's (2006) "high-quality information about learning" thereby ceases to be aspirational: in a verifiable discipline it is a checkable postcondition, and §5 checks it.

---

## 4. TrustGrade: a reference implementation for HDL education

TrustGrade instantiates the framework for Verilog coursework. Figure 8 situates the architecture in its application scenario — one assignment lifecycle across four planes (instructor, student, verifier, LLM) — and Figure 1 details the component view. This section walks the pipeline block by block; each subsection states the block's interface contract (inputs, outputs, failure modes), gives its algorithm, and traces the running example through real corpus data.

![Figure 1](figures/fig1_architecture.png)

**Figure 1.** Component architecture of TrustGrade. A submission flows through the executing assessment backbone (L0 compilation, L1 property testbenches, L2 differential testing) to a verifier-backed verdict, an UNCERTAIN escalation, or — via the feedback gate — gated LLM tutoring content; LLM-generated scaffolds pass a separate validator. Shaded components are verifier-owned; the gate delivers or withholds but never rewrites.


### 4.1 Deployment scenario and data context

The intended deployment is an undergraduate digital-design course. The *instructor* authors each objective `o` once — specification, interface, reference, property testbench, at the effort level of a conventional autograder assignment plus explicit invariants (the 37-objective corpus of §5.1, spanning combinational logic through clock-domain-crossing protocol design, was authored this way and doubles as the evaluation corpus). The *student* submits `s` through the course environment and interacts with two feedback channels: assessment (verdict + diagnosis, always verifier-backed) and tutoring (explanation + fix, or scaffold steps — LLM-generated, gate-passed). The *instructor* additionally receives the `UNC` escalation queue (4.1% of verdicts in our evaluation), each item pre-annotated with the disagreement evidence (`s ⊨ Φ` yet `s ≢_H r`), which is precisely the information a human needs to either extend `Φ` (a missed requirement) or recognize a legitimate alternative (extend nothing; accept). The entire verifier plane runs on the open-source Icarus Verilog simulator on commodity hardware — no proprietary EDA licenses — which the equity discussion in §6.3 turns from an implementation detail into a policy argument. Figure 8 traces one assignment lifecycle through these planes; note that every arrow entering the student lane originates in the verifier plane — the graphical form of Proposition 3.

![Figure 8](figures/fig8_scenario.png)

**Figure 8.** The application scenario: one assignment lifecycle across four planes (instructor, student, verifier, LLM). Instructors author objectives `o = (σ, I, r, Φ, H)` and receive the UNCERTAIN escalation queue (4.1% of verdicts, pre-annotated with disagreement evidence); students receive only verifier-backed verdicts/diagnoses and gate-passed tutoring content; all correctness decisions occur in the verifier plane.


### 4.2 Assessment backbone

**Interface contract.** Input: submission `s`, objective `o`. Output: `(V_B(s), δ(s))` per Definition 3. Failure modes handled: non-elaboration (L0 diagnostic), assertion violation (first failing property line), simulation hang (watchdog; classified as combinational-loop/clock fault), harness inapplicability (interface mismatch → REJ with port diff).

**Algorithm 1 — layered verdict.**
```
function ASSESS(s, o = (σ, I, r, Φ, H)):
    if not COMPILE(s):            return (REJ, δ_compile)          # L0
    t ← SIMULATE(s, TB(Φ), watchdog W)                             # L1
    if t = TIMEOUT:               return (REJ, δ_hang)
    if ∃ φⱼ failed in t:          return (REJ, δ_invariant(φⱼ, t))
    (y_s, y_r) ← (OBS(s, H), OBS(r, H))                            # L2
    if y_s = y_r:                 return (ACC, "meets Φ; matches r under H")
    else:                         return (UNC, δ_divergence(y_s, y_r))
```

**Running example.** A submission implementing the arbiter with `base <= gidx` (instead of `gidx + 1`) — a realistic bug that keeps the just-served requester at highest priority — compiles (L0 passes) and satisfies `φ₁, φ₂`, but under held requests `req = 0101` line 2 starves; L1 emits `REJ` with the corpus-verbatim diagnosis `δ = "VIOLATION starvation: req[2] unserved for 5 cycles (req=0101 …)"`. Conversely, a mask-based arbiter — structurally unlike the rotating-pointer reference — satisfies all three properties; under `H` its grant timing coincides with the reference, so it earns `ACC`; and the counter-scan variant, whose grant timing differs legitimately, lands in `UNC` rather than being falsely rejected — the three-valued semantics working as designed. All three artifacts are drawn from the evaluation corpus, not constructed for exposition.

**Layer economics.** Measured on the corpus (Apple M4): median L0 ≈ 9 ms, L1 ≈ 37 ms (bounded by the W = 3 s watchdog only on hangs), L2 ≈ 28 ms including the reference run; end-to-end median ≈ 75 ms per assessment (the ≈71 ms figure elsewhere is the independently measured gate-check median), enabling per-keystroke use if desired. Layer yields in the evaluation: L0 decided 7 rejections, L1 68, L2 accepted 137 and escalated 9 (§5.4).

### 4.3 Feedback gate

**Interface contract.** Input: tutor message `m = (v_t, e, f)`, submission `s`, objective `o`. Output: `DELIVER(m)` or `FALLBACK(V_B(s), δ(s))`. The gate never mutates `e` (P3).

**Algorithm 2 — gate.**
```
function GATE(m = (v_t, e, f), s, o):
    (v, d) ← ASSESS(s, o)                       # backbone verdict on the student's work
    if v_t ≠ v:                    return FALLBACK(v, d)          # C1
    (v_f, _) ← ASSESS(f, o)                     # full backbone on the proposed fix
    if v_f ≠ ACC:                  return FALLBACK(v, d)          # C2
    return DELIVER(v, e, f, tag="verified")
```

Two design decisions matter. *C2 uses the full backbone, not the property testbench alone.* On the stress corpus of §5.4 (RQ2) the cheaper test-only gate happens to suffice — every broken fix there violates an asserted invariant — but the assessment corpus shows why the insurance is kept: 9/84 bugs (10.7%) evade the property set entirely (§5.4), and a test-only gate inherits exactly that `R(Φ, ∅)` exposure of Proposition 2. The full contract closes it at the measured cost of one over-conservative interception. *The fallback is generated from verifier signals,* not by revising `e`: Figure 7 panels (b) and (d) show, for the running example, the delivered artifacts in both the intercept and pass cases.

![Figure 7](figures/fig7_worked_example.png)

**Figure 7.** Worked example from the corpus (round-robin arbiter). (a) Student submission whose priority pointer fails to rotate; (b) backbone rejection with the corpus-verbatim starvation diagnosis; (c) the LLM tutor's draft message; (d) gate checks C1/C2 passing and the verified message delivered. On C1 or C2 failure the learner receives (b) instead — harmful feedback cannot reach the learner.


### 4.4 Verified scaffolding

**Interface contract.** Input: objective `o`, requested decomposition depth `n ∈ {3, 4}`. Output: a validated scaffold `⟨(g_i, h_i, r_i, c_i)⟩` or a regeneration request; delivered steps satisfy s1–s3 below.

**Algorithm 3 — scaffold validation.**
```
function VALIDATE-SCAFFOLD(⟨(g_i, h_i, r_i, c_i)⟩ᵢ₌₁..ₙ, o):
    for i in 1..n:
        if not COMPILE(r_i ∥ c_i):        return REGENERATE(i)     # s1
        if SIMULATE(r_i, c_i) ≠ PASS:     return REGENERATE(i)     # s2
    if ASSESS(r_n, o) ≠ ACC-or-UNC-valid: return REGENERATE(n)     # s3: r_n ⊨ Φ
    return DELIVER-ALL
```

The generator (an LLM with tool access, run at authoring time) produces per-step goals, Socratic hints phrased as questions, step references, and *checkpoint testbenches* — per-step contracts a student's partial implementation can be checked against, so the learner receives executable formative feedback at every stage rather than only at the end. The s3 condition is what distinguishes a *verified* scaffold from a plausible one: the delivered sequence provably terminates in a contract-satisfying solution. Authoring cost (the generate–test–repair loop) is incurred once per assignment; in our evaluation all 36 generated steps validated and all 12 endpoints met their contracts (§5.4, RQ3), with the caveat — stated there — that the generator's self-testing, not one-shot generation, deserves the credit for raw validity; the validator remains the delivery-time guarantee.

### 4.5 Diagnosis extraction

The extractor `δ` maps each rejection to a structured diagnosis: `δ_compile(line, msg)` (syntactic/structural), `δ_invariant(φⱼ, t, observed values)` (behavioral — the named requirement, the violation time, the witnessing signal values), or `δ_hang(class)` (combinational loop / non-advancing clock). One implementation detail moved the headline metric: extracting the *first failing assertion line* of the simulation log — which carries `φⱼ`'s name and the observed values — rather than the simulator's terminal summary raised actionable diagnoses from 9% to 89% of rejections (§5.4, RQ1). The structured form serves two consumers: the learner (as the "How am I going?" answer) and the LLM explainer, which may receive `δ(s)` as verified raw material for `e`. (In the evaluation of §5 the tutor drafted from the specification and submission alone; the guarantee is carried by the gate, not by the prompt.)

### 4.6 Implementation notes

The verifier plane is ≈1,400 lines of Python orchestrating Icarus Verilog; determinism is enforced by fixed seeds and watchdogs. The tutor and scaffold-generator roles were played by a frontier LLM (Claude); the affordable-review condition of §5.4 (RQ4) used DeepSeek-chat via its public API; all prompts appear in Appendix A. The complete corpus — objectives, contracts, ground-truth generators, and per-arm verdicts — is archived for reproduction (§ Data availability).

---

## 5. Evaluation of assessment and gated tutoring in TrustGrade

The aim of the evaluation was twofold: first, to investigate the intrinsic quality of the assessment delivered by the executing backbone — its fairness toward valid alternative solutions, its safety against buggy work, and the informativeness of its diagnoses; and second, to examine how effectively different gating mechanisms prevent faulty tutoring feedback from reaching learners. The evaluation used a corpus of 221 submissions across 37 assignment objectives with construction-based ground truth, and a separate 222-item faulty-feedback corpus with oracle-confirmed labels. For the assessment aim, we compared four graders: the property-based grader, reference output matching, token-level similarity, and structural similarity, and additionally the full layered backbone. For the gating aim, we compared six conditions, each operationalizing a paradigm from the literature: (1) an *ungated* condition, in which every tutor message is delivered as generated, the deployment practice audited in CodeAid and by Azaiz et al.; (2) a *simulated-student* condition reimplementing the PyFiXV/GPT4Hints validation paradigm — a GPT-3.5-class student model (DeepSeek-chat, matching the class of their GPT-3.5Val) receives the buggy program and the tutor's explanation only, attempts the repair three times, and the message is approved if at least two repairs pass the property testbench; (3) an *affordable-review* condition, in which DeepSeek-chat statically reviews the proposed fix against the specification (the Dean-of-LLM-Tutors paradigm); (4) a *frontier-review* condition, identical but with a frontier reviewer (Claude), run twice to measure decision stability; (5) a *test-only* condition gating on the assignment's property testbench alone (the CodeTailor paradigm); and (6) the *full execution gate* of §4.3. Our analysis focused on (i) grader fairness and safety, (ii) interception of harmful feedback and its over-conservatism cost, (iii) validity of delivered scaffolds, and (iv) differences among the six gating conditions in delivered-content correctness and cost. Guided by these considerations, the evaluation addressed the following research questions:

- **RQ1:** How fair, safe, and informative is the assessment delivered by the property-based grader and the layered backbone, compared with reference-matching and similarity-based graders?
- **RQ2:** To what extent does the execution-based feedback gate intercept faulty tutoring feedback, and at what cost in over-conservatism and latency?
- **RQ3:** Are LLM-generated scaffolds, after validation, executable at every step and provably terminating in a correct solution?
- **RQ4:** How do the six gating conditions differ in delivered-content correctness, harmful-delivery counts, and marginal cost, on identical items?
- **RQ5:** Do these findings generalize — to a second, independently-authored HDL corpus (§5.5) and to a different executable discipline, introductory Python (§5.6)?

### 5.1 Corpus and ground truth

Evaluating graders and gates requires ground truth that is neither circular nor infeasible at scale; we therefore construct it (Fig. 6). The corpus comprises 37 assignment objectives spanning combinational, sequential, protocol, and clock-domain-crossing design, each with a specification, interface, reference solution, and property testbench (median 3 assertion sites, range 1–11). The **valid class** (n = 137) contains each reference solution plus semantics-preserving variants, admitted only if token-level alpha-equivalence to the reference is machine-verified, and algorithmically distinct verified implementations; 101 of the 137 are non-identical alternatives. The **buggy class** (n = 84) contains one instructor-authored realistic bug per objective plus mutation-injected faults, each admitted only if an independent differential oracle (two seeds × 128 cycles, distinct from the L2 harness) confirms observable divergence; mutations affecting only unconstrained behavior are excluded. The **faulty-feedback corpus** (n = 222) applies the same construction at scale: 137 valid "fixes" (the construction-proven valid class presented as tutor-proposed corrections), and 85 broken fixes — 36 lazy fixes (the student's buggy code returned as the "fix") and 49 oracle-confirmed mutants obtained by applying every applicable mutation operator to every reference solution. Nine of the 85 broken fixes evade the property testbench entirely (the `R(Φ, ∅)` class of Proposition 2), giving the corpus the discriminating power that a property-catchable-only fault population lacks. A further 58 oracle-behavior-preserving mutants cannot be assigned a proven label and are excluded from the primary analysis. Items are identifier-anonymized, and all gating conditions judge byte-identical artifacts.

![Figure 6](figures/fig6_corpus.png)

**Figure 6.** Construction of ground truth. Valid items pass a machine-checked alpha-equivalence filter; buggy items pass an independent two-seed differential oracle; changes affecting only don't-care behavior are excluded from the buggy class.

### 5.2 Procedure and data collection

For RQ1, all 221 submissions were graded by the four graders and by the layered backbone; each grader consumed the identical submission files, and per-submission verdicts were recorded together with the failing layer and extracted diagnosis. For RQ2, tutor messages were first generated by a frontier LLM for the 35 instructor-authored buggy submissions (verdict, explanation, corrected implementation; the prompt is reproduced in Appendix A.1); the gate was then stress-tested under three simulated failure modes constructed from these messages — wholesale verdict flips, lazy fixes, and mutated fixes — plus the authentic message stream. For RQ3, scaffolds for 12 representative objectives (36 steps) were generated with the tool-assisted authoring loop of §4.4 and passed through the validator; per-step compilation, checkpoint, and final-contract outcomes were recorded. For RQ4, the six gating conditions were executed on the 222-item corpus: the ungated condition delivers everything; the simulated-student condition issued 3 repair attempts per item (666 DeepSeek calls, temperature 0.8), each checked by execution; the two review conditions received identical inputs (specification, tutor explanation, proposed fix) and an identical static-review instruction (Appendix A.2), at temperature 0; the test-only and full-gate conditions executed the artifacts directly. Per-item verdicts, token counts, and wall-clock times were logged for every condition.

### 5.3 Data analysis

To answer RQ1, each grader's verdicts were compared against construction ground truth, instantiating Definition 2: the false-negative rate on the valid class (reported separately for the 101 alternatives) measures unfairness, and the false-positive rate on the buggy class measures unsafety. All proportions are reported with Wilson score 95% confidence intervals, which remain well-behaved for proportions near 0 or 1 at these sample sizes. Differences between graders' error rates were tested with two-sided Fisher exact tests, appropriate for the extreme cell counts involved. To answer RQ2, interception and delivery rates were computed per tutor stream with Wilson intervals; no inferential contrast is required because the ungated comparator delivers all faulty items by construction. To answer RQ3, step validity and final-contract satisfaction are reported as proportions with Wilson intervals. To answer RQ4, per-item correctness (harmful message withheld; valid message delivered) under each condition was compared with the full execution gate using exact two-sided McNemar tests on discordant pairs, the appropriate test for paired binary outcomes with small discordant counts; we report b (full gate correct, comparison condition wrong), c (the converse), and the exact binomial p. Stability of the frontier reviewer across its two passes was quantified with raw agreement and Cohen's κ. Given the small number of pre-specified contrasts, no multiplicity correction was applied; exact p-values are reported throughout so that readers may apply their preferred adjustment. All analysis code is archived with the artifacts.

### 5.4 Results

**RQ1. Assessment fairness, safety, and diagnosis.** The property grader rejected none of the 137 valid submissions (FNR = 0.000, 95% CI [0.000, 0.027]) and none of the 101 structurally different alternatives ([0.000, 0.037]), while accepting 9 of 84 buggy submissions (FPR = 0.107 [0.057, 0.191]). The token-similarity and structural-similarity graders accepted 82/84 (0.976 [0.917, 0.993]) and 81/84 (0.964 [0.900, 0.988]) buggy submissions, respectively; Fisher exact tests indicated that both false-positive rates differed significantly from the property grader's (p = 2.0 × 10⁻³⁴ and p = 4.7 × 10⁻³³). Reference output matching rejected one valid alternative (FNR = 0.007 [0.001, 0.040]) and accepted 11/84 buggy submissions (0.131 [0.075, 0.219]). Results are summarized in Table 1 and visually presented in Fig. 2. This pattern suggests that similarity-based grading is unsafe regardless of threshold on this corpus, and that the property grader's residual error is confined to the property-coverage gap that the differential layer is designed to close.

**Table 1.** Grader error rates on the 221-submission corpus. *Note:* FNR = rejects valid work; FPR = accepts buggy work; brackets are Wilson 95% CIs.

| Grader | FNR, valid (n=137) | FNR, alternatives (n=101) | FPR, buggy (n=84) |
|---|---|---|---|
| Property (ours) | 0.000 [.000,.027] | 0.000 [.000,.037] | 0.107 [.057,.191] |
| Reference output match | 0.007 [.001,.040] | 0.010 [.002,.054] | 0.131 [.075,.219] |
| Token similarity | 0.124 [.079,.190] | 0.168 [.108,.252] | 0.976 [.917,.993] |
| Structural similarity | 0.015 [.004,.052] | 0.020 [.005,.070] | 0.964 [.900,.988] |

![Figure 2](figures/fig2_graders.png)

**Figure 2.** Error rates of the four graders on the 221-submission corpus. The left bar of each pair is the false-negative rate on valid work; the right bar is the false-positive rate on buggy work. Error bars are Wilson 95% confidence intervals; fractions annotate raw counts.

Combining the layers, the backbone soundly decided 212 of 221 submissions (95.9% [92.4, 97.8]) with 211 of 212 sound verdicts correct (99.5% [97.4, 99.9]), and escalated 9 of 221 (4.1% [2.2, 7.6]) as UNCERTAIN. Per layer, L0 decided 7 rejections, L1 68, and L2 accepted 137 and escalated 9. The single erroneous sound verdict was a mutant whose behavior coincided with the reference under the L2 harness but diverges under the extended oracle — an empirical member of the residual class `R(Φ, H)` of Proposition 2. The nine escalations comprised the eight property-evading mutants and one valid alternative implementation. Of the 75 sound rejections, 67 (89.3% [80.3, 94.5]) carried an actionable named diagnosis — a labeled failing check (51%), an observable mismatch with values (17%), a named invariant (12%), or a compiler line (9%) — and 11% remained generic. Results are visually presented in Fig. 5. Two extraction details were consequential and are reported as engineering findings: taking the first failing assertion line rather than the simulator's terminal summary raised actionability from 9% to 88%, and extending token capture to non-`FAIL`-prefixed assertion formats raised it further to 89.3%.

![Figure 5](figures/fig5_diagnosis.png)

**Figure 5.** Diagnosis classes attached to the 75 sound rejections. Named signals (failing check, observable mismatch with values, named invariant, compiler line) support formative feedback; the generic class consists predominantly of watchdog timeouts.

**RQ2. Gate interception, over-conservatism, and latency.** Across the three simulated failure modes, the gate intercepted all 76 harmful messages (100% [95.2, 100]): 35 of 35 verdict flips were caught by check C1, and 35 of 35 lazy fixes together with 6 of 6 oracle-confirmed broken fixes were caught by check C2. Of legitimate content, 34 of 35 authentic tutor messages (97.1% [85.5, 99.5]) and 28 of 29 behavior-preserving variants (96.6% [82.8, 99.4]) were delivered. Median gate latency was ≈71 ms per check. Results are summarized in Table 2 and visually presented in Fig. 4. Under the ungated comparator, all 76 harmful messages would have reached learners by construction. An ablation clarifies the layers' respective contributions: a test-only gate matched the full gate on this corpus — all six broken fixes violate asserted invariants — while avoiding the single over-conservative interception; its exposure is the property-evading class measured at 10.7% [5.7, 19.1] on the assessment corpus under RQ1. This suggests that the differential layer functions as insurance against property-evading fixes, purchased at approximately 3% over-conservatism, and that the value of this insurance depends on the fault population.

**Table 2.** Feedback-gate stress tests. *Note:* interception is the desired outcome for the three faulty streams; delivery is the desired outcome for the two legitimate streams; brackets are Wilson 95% CIs.

| Tutor stream | n | Intercepted | Harmful delivered |
|---|---|---|---|
| Authentic frontier tutor | 35 | 1 | 0 |
| Verdict flips | 35 | 35 [.902, 1.0] | 0 |
| Lazy fixes | 35 | 35 [.902, 1.0] | 0 |
| Broken fixes (oracle-confirmed) | 6 | 6 [.610, 1.0] | 0 |
| Behavior-preserving variants | 29 | 1 | 0 |

![Figure 4](figures/fig4_gate_stress.png)

**Figure 4.** Gate interception by tutor stream. Red bars are simulated faulty streams, for which interception is the desired outcome; grey bars are legitimate streams, for which delivery is desired. Error bars are Wilson 95% CIs.

**RQ3. Scaffold validity.** All 36 generated step checkpoints compiled and passed against their step references (100% [90.4, 100]), and all 12 final steps satisfied the assignment's property contract (100% [75.8, 100]). The high raw validity is attributable to the generator's tool-assisted authoring loop; one-shot generation would be substantially lower (cf. spec-to-RTL pass rates on VerilogEval; Liu et al., 2023), and the validator remains the delivery-time guarantee in either regime.

**RQ4. Comparison of the six gating conditions.** Table 3 summarizes the paired comparison on the 222-item corpus (85 broken fixes, of which 9 evade the property set; 137 valid). The ungated condition delivered all 85 harmful messages. The simulated-student condition caught 6 of 85 broken fixes and delivered 79; its student model, given a correct explanation, repaired the buggy program regardless of the state of the attached artifact. The affordable-review condition caught 81 of 85 but withheld 70 of 137 valid fixes (51.1%), many with justifications referring to defects not present in the code. The test-only condition caught 76 of 85, delivering all 9 property-evading fixes. The frontier-review and full-gate conditions each delivered a single harmful fix and caught 8 of the 9 property-evaders. Exact McNemar tests indicated that per-item correctness under the full execution gate differed significantly from the ungated (b = 84, c = 5, p = 1.4 × 10⁻¹⁹), simulated-student (b = 80, c = 0, p = 1.7 × 10⁻²⁴), affordable-review (b = 69, c = 1, p = 1.2 × 10⁻¹⁹), and test-only (b = 8, c = 1, p = .039) conditions, and did not differ significantly from the frontier-review condition (b = 3, c = 5, p = .73). The affordable reviewer consumed approximately 1.1k tokens per check; the execution conditions required approximately 37 ms (test-only) and 71 ms (full) per check. Results are visually presented in Fig. 3. These results indicate that, at a sample size able to resolve the top of the table, the full gate is distinguishable from the test-only gate — the difference lying almost entirely in the property-evading class (8/9 versus 0/9) — while remaining statistically indistinguishable from frontier review on accuracy; the remaining differences between those two are marginal cost, determinism, and the contractual character of the guarantee, which we take up in Section 6.

**Table 3.** Verdicts of the six gating conditions on the 222-item faulty-feedback corpus (85 broken, incl. 9 property-evading; 137 valid). *Note:* McNemar tests are exact and two-sided, against the full execution gate; brackets are Wilson 95% CIs; costs are per item.

| Gating condition (paradigm source) | Catch broken | Pass valid | Evaders caught | Harmful delivered | McNemar vs. full gate | Marginal cost |
|---|---|---|---|---|---|---|
| Ungated (CodeAid'24 / Azaiz'24) | 0/85 | 137/137 | 0/9 | 85 | b=84, c=5, p=1.4e-19 | none |
| Simulated student (PyFiXV'23 / GPT4Hints'24) | 6/85 | 130/137 | 1/9 | 79 | b=80, c=0, p=1.7e-24 | 3 LLM calls + 3 sims |
| Affordable review (Dean-of-LLM-Tutors'25) | 81/85 | 67/137 | 7/9 | 4 | b=69, c=1, p=1.2e-19 | ≈1.1k tokens |
| Frontier review (same paradigm) | 84/85 | 134/137 | 8/9 | 1 | b=3, c=5, p=.73 | frontier tokens |
| Test-only execution (CodeTailor'24) | 76/85 | 133/137 | 0/9 | 9 | b=8, c=1, p=.039 | ≈37 ms |
| Full execution gate (this work) | 84/85 | 132/137 | 8/9 | 1 | — | ≈71 ms |

![Figure 3](figures/fig3_three_arm.png)

**Figure 3.** Delivered-content outcomes of the six gating conditions on the 222-item corpus. Bars show catch rate on the 85 broken fixes and pass rate on the 137 valid fixes; annotations give harmful-delivery counts; error bars are Wilson 95% CIs.

### 5.5 Replication and scale-up on an independent public corpus

A result on a single, course-derived corpus may reflect that corpus rather than the mechanism. To test whether the findings of RQ1 and RQ4 generalize, and to provide an artifact others can run without the (non-redistributable) course material, we authored a second corpus *de novo* and repeated the evaluation on it. The **expansion corpus** comprises 130 newly written objectives spanning fourteen design classes — combinational, sequential, FSM/protocol, datapath, arithmetic (multipliers, dividers, carry-lookahead/carry-save adders, BCD, saturating units), memory (register file, RAM, FIFO, stack, content-addressable match, circular buffer), bus/serial protocol (UART, SPI, skid buffer, serializer, credit flow), DSP (FIR, MAC, integrator, comb filter, dot product), coding/ECC (parity, Hamming(7,4) encode/decode, CRC-8, checksum), bit manipulation (find-first/last-set, count-leading/trailing-zeros, reverse, rotate), advanced FSM, advanced sequential (PWM, timers, watchdog), clock-domain-crossing synchronizers, and ALU/control datapaths. Every objective was authored with a golden solution, a property testbench, and one realistic bug, and admitted only after machine verification that the golden solution passes the property testbench and the bug fails it (130/130 objectives passed; the corpus is released in full, unlike the primary corpus). The same construction procedure of §5.1 then expanded these into 131 objectives and **664 submissions** (402 valid, of which 272 are structurally distinct alternatives; 262 buggy, of which 9 evade the property set).

**Graders replicate at scale.** On the 664 submissions the property grader again rejected no valid submission (FNR = 0.000, 95% CI [0.000, 0.009]) and none of the 272 alternatives ([0.000, 0.014]), while the token- and structural-similarity graders accepted 260/262 (0.992 [0.972, 0.998]) and 255/262 (0.973 [0.945, 0.988]) buggy submissions, respectively — differing from the property grader's false-positive rate at p = 1.8 × 10⁻¹² and p = 9.7 × 10⁻¹³ (Fisher exact). The property grader's residual (9/262 accepted) was confined entirely to constant-increment mutants that evade the property set, exactly the `R(Φ, ∅)` class of Proposition 2. The layered backbone delivered sound verdicts at 654/656 accuracy and, as a delivery gate on the same corpus, caught 260 of 262 broken fixes including 7 of the 9 property-evaders through its differential layer, over-blocked one valid alternative (401/402 delivered), and delivered two harmful fixes — the residual `R(Φ, H)` that evades both the property set and the auto-generated differential harness. A test-only gate on the same corpus caught 253 of 262 and none of the 9 evaders.

**The six-condition ranking replicates.** Running all six gating conditions of §5.4 — including the two paid LLM arms — on a 152-item subset of this corpus (88 valid, 64 broken including 2 property-evaders) reproduced the ordering of Table 3 (Table 4): the full execution gate delivered zero harmful fixes and caught both evaders, was statistically indistinguishable from frontier review (McNemar b = 3, c = 1, p = 0.62), and differed significantly from affordable review (p = 7.6 × 10⁻⁵), the simulated-student paradigm (p = 6.1 × 10⁻²⁰), and ungated delivery (p = 3.6 × 10⁻¹⁸). Affordable review again over-blocked, delivering only 83 of 88 valid fixes while missing 13 broken ones; the simulated student, artifact-blind by construction, delivered 48 of 64 broken fixes. This independent replication — on a corpus authored after the framework was fixed, spanning fourteen design classes, and released in full — indicates that the results of §5.4 are properties of the gating mechanism rather than of the primary corpus.

**Table 4.** Six gating conditions on the 152-item subset of the public expansion corpus (88 valid, 64 broken incl. 2 property-evading). *Note:* McNemar exact, two-sided, versus the full execution gate; Wilson 95% CIs.

| Gating condition | Catch broken | Pass valid | Evaders caught | Harmful delivered | McNemar vs. full gate |
|---|---|---|---|---|---|
| Ungated | 0/64 | 88/88 | 0/2 | 64 | b=64, c=1, p=3.6e-18 |
| Simulated student | 16/64 | 66/88 | 1/2 | 48 | b=70, c=1, p=6.1e-20 |
| Affordable review | 51/64 | 83/88 | 1/2 | 13 | b=18, c=1, p=7.6e-05 |
| Frontier review | 61/64 | 88/88 | 0/2 | 3 | b=3, c=1, p=0.62 |
| Test-only execution | 62/64 | 88/88 | 0/2 | 2 | b=2, c=1, p=1.0 |
| Full execution gate (this work) | 64/64 | 87/88 | 2/2 | 0 | — |

### 5.6 External validity: a cross-domain check in Python

The mechanism we advance — routing correctness claims through execution — is not specific to hardware. To probe how far it transfers, and to situate it honestly against LLM reviewers on a domain where those reviewers are strong, we repeated the grader/reviewer comparison on an open programming-education dataset, MBPP (Austin et al., 2021), which pairs 974 introductory Python problems with reference solutions and assertion tests. Using the construction procedure of §5.1 we built 478 candidates from 150 problems — 300 correct (reference solutions plus semantics-preserving reformattings, each verified to pass the tests) and 178 buggy (abstract-syntax-tree mutations confirmed buggy by the tests failing). The Python execution backbone runs each candidate against the problem's tests in an isolated subprocess with a watchdog, the direct analog of the property testbench. We compared it with token similarity and with two LLM reviewers performing static correctness review — an affordable model (DeepSeek-chat) and a frontier model (Claude), each given room to reason before a verdict, neither permitted to execute.

Two results matter, and one caveat frames them. The **caveat** is that on MBPP the correct/buggy labels are *defined* by the same tests the execution backbone runs, so here the backbone is the oracle rather than a competitor; the informative contrast is among the static methods measured against it (Table 5). First, **a frontier LLM reviewer nearly matches execution on common Python**: Claude passed 299 of 300 correct solutions and caught all 178 bugs — these are textbook patterns a frontier model has seen exhaustively, and its one disagreement was a reformatting it argued was genuinely mis-indented. Second, **an affordable LLM reviewer over-rejects heavily**: even with reasoning enabled, DeepSeek passed only 171 of 300 correct solutions (a 43% over-rejection rate) while catching most bugs — the same over-blocking failure it exhibited on the HDL corpus. Token similarity was again unfit (1 of 178 bugs caught).

The comparison thus sharpens rather than universalizes the claim. On simple, heavily-represented tasks a frontier reviewer suffices and execution's advantage over it is small; the advantage is largest in specialized, sparsely-represented domains such as HDL, where §5.4 showed frontier review still missing property-evading fixes that the execution gate catches. In both regimes the execution gate is reliable at near-zero marginal cost, and in both regimes affordable review — the only LLM option that scales to under-resourced settings — is the least safe. Where an executable oracle exists, the architectural rule holds across domains; the size of its dividend depends on how well the domain is represented in the reviewer's training.

**Table 5.** Cross-domain comparison on MBPP Python (478 candidates: 300 correct, 178 buggy). *Note:* the execution backbone defines the labels here (oracle); McNemar exact vs. the backbone; Wilson 95% CIs.

| Method | Catch buggy (178) | Pass correct (300) | Harmful delivered | McNemar vs. execution |
|---|---|---|---|---|
| Execution backbone (ours) | 178/178 | 300/300 | 0 | — (oracle) |
| Token similarity | 1/178 | 300/300 | 177 | p ≈ 1e-53 |
| Affordable LLM review (DeepSeek) | 168/178 | 171/300 | 10 | p ≈ 2.9e-42 |
| Frontier LLM review (Claude) | 178/178 | 299/300 | 1 | p = 1.0 |

---

## 6. Discussion

### 6.1 Principal findings

Returning to the research questions: the executing backbone graded 96% of submissions with verifier-backed verdicts at 99.5% accuracy while accepting every valid alternative solution (RQ1); the gate reduced harmful-feedback delivery from a construction-guaranteed 100% (ungated) to 0% across three adversarial failure modes at ≈3% over-conservatism and ≈71 ms (RQ2); scaffold validation delivered only steps that compile, pass, and provably reach a correct endpoint (RQ3); and the six-condition comparison located execution gating on the accuracy frontier at near-zero cost, with the affordable-LLM alternative failing in both directions at once (RQ4). Read through §3.5's lens, the system makes the three feedback questions of Hattie and Timperley checkable: "How am I going?" is answered with verified verdicts and named invariants, "Where to next?" with fixes and scaffold steps that demonstrably work.

### 6.2 Relation to prior evidence

Three connections deserve emphasis. First, our results give the hybrid-architecture recommendation of Yasir et al. (2026b) a working existence proof in a verifiable discipline: the high over-validation of incorrect solutions they report is precisely the failure class our Table 2 shows the gate eliminating by construction. Second, the negative result of Yasir et al. (2026a) — verification *hurting* strong tutors — does not contradict our findings but confirms our P3: their harm pathway runs through an LLM judge's rewrites; a gate with a validate-or-withhold action space has no such pathway, and our authentic-tutor stream shows the corresponding cost is bounded (one over-conservative interception in 35). Third, the affordable-reviewer arm empirically instantiates the self-correction literature's warning (Gou et al., 2024; Gu et al., 2024): review-based gating inherits the reviewer's competence, and at accessible price points that competence is insufficient — while execution gating is competence-invariant. Fourth, the simulated-student condition exposes an artifact-type boundary: validation of an explanation's usefulness — sound for hint-only delivery as in GPT4Hints — approves nearly every message once the explanation is correct (69/70 here), regardless of the state of the attached code; feedback that carries an artifact requires a gate that executes the artifact.

### 6.3 Implications for practice

For system builders in verifiable disciplines, the results support a concrete architectural rule: *route every correctness-bearing claim through an executing check, and let the LLM do everything else.* For institutions, the six-condition comparison carries an equity implication: guardrail quality in LLM-reviewed designs scales with model budget, so the institutions least able to pay frontier prices would field the least-safe tutors; an execution gate decouples feedback safety from spend, running on open-source simulators and commodity hardware. For assessment designers, P4 shows that contract-based grading is not merely safer but *fairer* — the 0/101 false-rejection rate on alternative solutions addresses a documented harm of both reference-matching autograders and LLM tutors (Yasir et al., 2026b), which matters for exactly the divergent, creative solutions engineering education aims to encourage.

### 6.4 Boundary conditions

We resist overclaiming on three fronts. The guarantee is bounded by the contract: property sets are never complete (the 4.1% escalation band and the single backbone error measure the current budget), and enlarging coverage — longer differential runs, formal property checking for clock-domain-crossing classes — buys tighter bounds at known cost. The frontier-review condition shows that institutions able to pay frontier prices per message can currently match the gate's empirical accuracy, though without determinism, auditability, or immunity to model drift; the cross-domain check (§5.6) sharpens this into a boundary — on textbook-familiar tasks a frontier reviewer nearly matches execution, so the gate's detection dividend, as opposed to its cost and determinism dividend, is largest precisely in specialized, sparsely-represented domains like HDL. And the approach transfers only where artifacts have machine-checkable semantics; it says nothing about essay feedback.

---

## 7. Limitations and future work

First, this is a technical and adversarial evaluation, not a classroom study: no claims are made about learning outcomes, trust calibration, or usability. The natural next steps are an expert panel study (instructors blind-rating gated versus ungated feedback streams) followed by a course pilot; the framework's measurable constructs (§3.5) were designed to survive that transition. Second, ground truth is constructed rather than harvested: construction gives exact labels and controlled coverage but under-represents the long tail of authentic student error; replication on real submission logs — including compilation-adjacent errors our L0 handles trivially but students find opaque — is planned. Third, on transfer beyond the primary corpus we now have two forms of evidence rather than an argument alone: an independently-authored 130-objective, fourteen-class HDL corpus reproduces the findings (§5.5), and a cross-domain check on introductory Python demonstrates the mechanism transfers while bounding its dividend (§5.6, where a frontier reviewer nearly matches execution on textbook tasks); formal-methods disciplines beyond simulation semantics — e.g. clock-domain-crossing classes needing model checking rather than differential testing — remain future work. Fourth, the scaffold evaluation covers 12 objectives with a single generator configuration; hint quality (as distinct from checkpoint validity) is unmeasured and requires expert rating. Fifth, single-run LLM arms: the frontier reviewer's κ = 1.0 across two passes mitigates but does not eliminate run-to-run variance concerns for the LLM baselines; the execution gate, being deterministic, has no such variance.

---

## 8. Conclusion

Deployed LLM tutors deliver wrong feedback at rates that published audits document and that formative-feedback theory identifies as actively harmful (Kazemitabaar et al., 2024; Azaiz et al., 2024; Yasir et al., 2026b), and the prevailing mitigations either erode, fail to scale, or inherit the fallibility they were meant to contain. This paper demonstrated that in disciplines with executable semantics the problem admits an engineering solution: a framework in which executing verifiers hold authority and LLMs hold the pen, and a reference system in which 96% of verdicts arrive verifier-backed at 99.5% accuracy, 100% of adversarially injected harmful feedback is intercepted at 71 milliseconds and near-zero cost, and every delivered scaffold step provably leads to a correct solution. The comparison that matters most for practice is the one on identical items: execution gating matches frontier-model review while an affordable reviewer fails in both directions — so the choice is between safety that must be purchased per message and safety that is a property of the architecture. For hardware-design education, strategically starved of trustworthy tooling, and for AI-in-education research seeking hybrid architectures with provable components, verification-gated tutoring offers a template whose guarantees are inspectable, auditable, and free at the margin.

---

## Declarations

**Ethics.** The study used no human participants and no student data; all submissions were synthesized or instructor-authored. (Ethics approval: not applicable.)
**CRediT.** [To be completed at submission.]
**Data and code availability.** The reference implementation of the framework and system — the assessment backbone, the feedback gate, the scaffold validator, the six gating-paradigm reviewers, the evaluation statistics, the verbatim prompts of Appendix A, and the worked arbiter example — is publicly available at **https://github.com/cyuanlong/trustgrade** (MIT-licensed), together with an end-to-end test suite and a provenance note. The **public expansion corpus of §5.5** (130 objectives across fourteen design classes, with the six-arm verdicts) and the **Python cross-domain corpus and code of §5.6** are released in full at the same repository. The primary evaluation corpus (37 objectives, the 221-item ground-truth corpus and its generators — alpha-equivalence checker, mutation injectors, differential oracle — and the 222-item anonymized faulty-feedback corpus with all six conditions' verdicts) is derived from course assignments and will be released there on acceptance.
**Funding.** [To be completed.]
**Declaration of generative-AI use.** LLMs were used as experimental subjects and components of the system under study, as described throughout; manuscript preparation was assisted by an LLM under full author direction and verification.

---

## Appendix A. Prompts (verbatim, as used in the evaluation)

**A.1 Tutor prompt** (frontier LLM; produces `m = (v_t, e, f)`):
> You are an AI programming tutor helping a student in a Verilog / hardware-design course. [...] For EACH submission provide: "verdict": "CORRECT" or "BUGGY" (does the student code meet the spec?); "explanation": <= 25 words on what is wrong (or why it's correct); "corrected_rtl": a COMPLETE, COMPILABLE Verilog module that fixes the bug (same module name and ports as the student's). If you judge it CORRECT, return the student's code unchanged. Do static review only (no simulator). Give your genuine best tutoring feedback.

**A.2 Reviewer-gate prompt** (identical for the frontier and affordable arms; §5.7):
> You are the quality-review layer of an AI tutoring system for a Verilog course. A tutor (another AI) proposed a fix for a student's buggy code. Decide by careful STATIC review only (no simulator) whether the proposed fix is safe to deliver to the student. [Input: assignment spec + interface; tutor's explanation; proposed corrected code.] Verdict: "APPROVE" (fix correctly implements the spec — safe to deliver) or "REJECT" (fix is functionally wrong — must not reach the student). Judge the fix on its own merits; some fixes are fine, others contain subtle errors.

**A.3 Scaffold-generator prompt** (authoring time; §4.4):
> You are the scaffolding generator inside an intelligent tutoring system for a Verilog/HDL course. For each assignment, decompose the design task into 3–4 ordered learning steps a student can complete incrementally, each with a verifiable checkpoint. [Each step:] "goal": one-sentence student-facing goal; "hint": one Socratic hint (a question, never the answer); "step_rtl": a COMPLETE COMPILABLE Verilog module representing the reference state after this step; "step_tb": a SELF-CHECKING testbench that tests ONLY what this step should achieve, printing exactly "PASS" if satisfied and "FAIL ..." otherwise, with a timeout. The FINAL step's step_rtl must be the complete correct solution. Steps must be cumulative.

## Appendix B. Example property testbench (round-robin arbiter; corpus-verbatim)

```verilog
`timescale 1ns/1ps
// Property-based testbench: asserts INVARIANTS only, never compares to a golden model.
// Properties:
//   P1 mutex:      grant is onehot0 (at most one bit high)
//   P2 no-empty:   (grant & ~req) == 0  (never grant an idle line)
//   P3 fairness:   a line whose req is held high continuously must get a grant
//                  within FAIR_BOUND (=6) cycles, else starvation -> FAIL.
module property_tb;
  localparam integer N          = 4;
  localparam integer FAIR_BOUND = 6;   // N+2

  reg                clk;
  reg                rst_n;
  reg  [3:0]         req;
  wire [3:0]         grant;

  integer            i;
  integer            errors;
  // per-line consecutive cycles that req has been held high without being granted
  integer            wait_cnt [0:3];
  reg  [3:0]         req_prev;

  // DUT
  arbiter_rr dut (.clk(clk), .rst_n(rst_n), .req(req), .grant(grant));

  // 10ns clock
  initial clk = 1'b0;
  always #5 clk = ~clk;

  // ---- helper: onehot0 check (at most one bit set) ----
  function automatic is_onehot0;
    input [3:0] v;
    begin
      is_onehot0 = ((v & (v - 4'b0001)) == 4'b0000); // clears lowest set bit; 0 => <=1 bit
    end
  endfunction

  // ---- property checks, evaluated every cycle on sampled grant ----
  task check_properties;
    begin
      // P1 mutual exclusion
      if (!is_onehot0(grant)) begin
        $display("FAILED: P1 mutex violated at time %0t, grant=%b", $time, grant);
        errors = errors + 1;
      end
      // P2 no empty grant
      if ((grant & ~req) != 4'b0000) begin
        $display("FAILED: P2 empty-grant violated at time %0t, req=%b grant=%b",
                 $time, req, grant);
        errors = errors + 1;
      end
      // P3 fairness bookkeeping: update per-line wait counters
      for (i = 0; i < N; i = i + 1) begin
        if (req[i] === 1'b1 && (req_prev[i] === 1'b1)) begin
          // req held high across this cycle
          if (grant[i] === 1'b1) begin
            wait_cnt[i] = 0;               // served -> reset
          end else begin
            wait_cnt[i] = wait_cnt[i] + 1; // still waiting
            if (wait_cnt[i] > FAIR_BOUND) begin
              $display("FAILED: P3 fairness/starvation on line %0d at time %0t (waited %0d cycles), req=%b grant=%b",
                       i, $time, wait_cnt[i], req, grant);
              errors = errors + 1;
            end
          end
        end else begin
          // req not continuously held -> restart the window, count this cycle if granted
          wait_cnt[i] = (grant[i] === 1'b1) ? 0 : 0;
        end
      end
      req_prev = req;
    end
  endtask

  // sample slightly after the rising edge so registered grant is settled
  always @(posedge clk) begin
    #1;
    if (rst_n) check_properties;
  end

  // ---- stimulus ----
  integer k;
  integer seed;
  initial begin
    errors   = 0;
    req      = 4'b0000;
    req_prev = 4'b0000;
    rst_n    = 1'b0;
    seed     = 32'hC0FFEE;
    for (i = 0; i < N; i = i + 1) wait_cnt[i] = 0;

    // hold reset a few cycles
    repeat (3) @(posedge clk);
    @(negedge clk);
    rst_n = 1'b1;

    // ---- Directed 1: all req high held long -> exercises rotation & fairness ----
    req = 4'b1111;
    repeat (20) @(negedge clk);

    // ---- Directed 2: only high-index lines held (kills fixed-priority arbiters) ----
    req = 4'b1110;   // lines 1,2,3 held; a low-prio-first fixed arbiter starves 2,3
    repeat (20) @(negedge clk);

    req = 4'b1010;   // lines 1,3 held
    repeat (20) @(negedge clk);

    req = 4'b1000;   // only line 3 held; fixed-priority-low would starve it vs others? single line must be served
    repeat (12) @(negedge clk);

    // ---- Directed 3: rotating single requests ----
    req = 4'b0001; repeat (4) @(negedge clk);
    req = 4'b0010; repeat (4) @(negedge clk);
    req = 4'b0100; repeat (4) @(negedge clk);
    req = 4'b1000; repeat (4) @(negedge clk);

    // ---- Directed 4: pairs and gaps ----
    req = 4'b0110; repeat (16) @(negedge clk);
    req = 4'b1100; repeat (16) @(negedge clk);
    req = 4'b0101; repeat (16) @(negedge clk);

    // ---- Random stimulus (with stretches of held requests for fairness) ----
    for (k = 0; k < 400; k = k + 1) begin
      // bias toward holding requests so fairness window can build up
      if (($random(seed) % 3) == 0)
        req = $random(seed);            // change request set
      // else keep same req (held) -> stresses starvation detection
      @(negedge clk);
    end

    // ---- Random held-high bursts: pick a fixed mask and hold many cycles ----
    for (k = 0; k < 8; k = k + 1) begin
      req = $random(seed) & 4'b1111;
      if (req == 4'b0000) req = 4'b1111;
      repeat (12) @(negedge clk);
    end

    req = 4'b0000;
    repeat (5) @(negedge clk);

    if (errors == 0)
      $display("PASSED: all properties (mutex, no-empty-grant, fairness) held over the run.");
    else
      $display("FAILED: %0d property violation(s) detected.", errors);

    $finish;
  end

  // safety timeout
  initial begin
    #200000;
    $display("FAILED: timeout (simulation did not finish)");
    $finish;
  end
endmodule
```

## Appendix C. The 37 assignment objectives

| Objective | Class | Assertion sites | Valid items | Buggy items |
|---|---|---|---|---|
| `async_fifo` | CDC | 6 | 4 | 3 |
| `async_fifo#2` | CDC | 6 | 4 | 2 |
| `async_fifo#3` | CDC | 2 | 4 | 1 |
| `cdc_cfg_handshake` | CDC | 6 | 4 | 2 |
| `cdc_cfg_reg` | CDC | 5 | 4 | 2 |
| `cdc_pulse_sync_f2s` | CDC | 2 | 4 | 2 |
| `pulse_sync_f2s` | CDC | 2 | 4 | 2 |
| `barrel_shifter` | combinational | 2 | 4 | 2 |
| `gray_codec` | combinational | 4 | 2 | 2 |
| `hamming74_decoder` | combinational | 3 | 4 | 2 |
| `mux4` | combinational | 3 | 2 | 2 |
| `prio_enc` | combinational | 4 | 4 | 2 |
| `priority_encoder_msb` | combinational | 6 | 4 | 2 |
| `credit_flow_ctrl` | protocol/flow | 4 | 4 | 4 |
| `credit_flow_ctrl#2` | protocol/flow | 2 | 4 | 3 |
| `handshake_fsm` | protocol/flow | 4 | 4 | 3 |
| `handshake_fsm#2` | protocol/flow | 2 | 4 | 2 |
| `rr_arb4` | protocol/flow | 5 | 4 | 1 |
| `rr_arbiter` | protocol/flow | 5 | 4 | 1 |
| `rr_arbiter` | protocol/flow | 6 | 3 | 2 |
| `skid_buffer` | protocol/flow | 4 | 4 | 2 |
| `skid_buffer#2` | protocol/flow | 6 | 4 | 2 |
| `skid_buffer#3` | protocol/flow | 6 | 4 | 2 |
| `skid_buffer#4` | protocol/flow | 11 | 4 | 3 |
| `sync_fifo` | protocol/flow | 7 | 4 | 2 |
| `clk_div_even` | sequential | 2 | 4 | 3 |
| `debounce_pulse` | sequential | 5 | 4 | 2 |
| `debouncer` | sequential | 3 | 4 | 3 |
| `edge_detector` | sequential | 5 | 4 | 1 |
| `gated_reg_bank` | sequential | 3 | 4 | 2 |
| `lfsr16` | sequential | 9 | 4 | 2 |
| `lifo_stack` | sequential | 1 | 4 | 3 |
| `pwm_gen` | sequential | 2 | 4 | 3 |
| `reg_en` | sequential | 2 | 2 | 2 |
| `sat_updown_counter` | sequential | 3 | 2 | 3 |
| `sat_updown_counter#2` | sequential | 6 | 4 | 4 |
| `up_counter` | sequential | 2 | 2 | 3 |

*Assertion sites are counted as distinct FAIL/VIOLATION/MISMATCH emission points in the property testbench; valid/buggy item counts are the per-objective ground-truth corpus of §5.2.*

## References

Austin, J., Odena, A., Nye, M., et al. (2021). Program synthesis with large language models (MBPP). arXiv:2108.07732.
Azaiz, I., Kiesler, N., & Seidel, S. (2024). Feedback-generation for programming exercises with GPT-4. *Proceedings of ITiCSE 2024*.
Chen, X., et al. (2025). Revisit self-debugging with self-generated tests. arXiv:2501.12793.
Daheim, N., et al. (2024). Stepwise verification and remediation of student reasoning errors with LLM tutors. *Proceedings of EMNLP 2024*.
Gou, Z., et al. (2024). CRITIC: Large language models can self-correct with tool-interactive critiquing. *Proceedings of ICLR 2024*.
Gu, A., et al. (2024). The counterfeit conundrum: Can code language models grasp the nuances of their incorrect generations? *Findings of ACL 2024*.
Hattie, J., & Timperley, H. (2007). The power of feedback. *Review of Educational Research, 77*(1), 81–112.
Hou, X., Wu, Z., Wang, X., & Ericson, B. J. (2024). CodeTailor: LLM-powered personalized Parsons puzzles for engaging support while learning programming. *Proceedings of L@S 2024*.
Huang, J., et al. (2024). Large language models cannot self-correct reasoning yet. *Proceedings of ICLR 2024*.
Kamoi, R., et al. (2024). When can LLMs actually correct their own mistakes? A critical survey of self-correction of LLMs. *Transactions of the ACL, 12*.
Kazemitabaar, M., et al. (2024). CodeAid: Evaluating a classroom deployment of an LLM-based programming assistant that balances student and educator needs. *Proceedings of CHI 2024*.
Liffiton, M., Sheese, B., Savelka, J., & Denny, P. (2023). CodeHelp: Using large language models with guardrails for scalable support in programming classes. *Proceedings of Koli Calling 2023*.
Liu, M., et al. (2023). VerilogEval: Evaluating large language models for Verilog code generation. *Proceedings of ICCAD 2023*.
Liu, R., et al. (2024). Teaching CS50 with AI: Leveraging generative artificial intelligence in computer science education. *Proceedings of SIGCSE 2024*.
Liu, R., et al. (2025). Improving AI in CS50: Leveraging human feedback for better learning. *Proceedings of SIGCSE TS 2025*.
Lu, Y., et al. (2024). RTLLM: An open-source benchmark for design RTL generation with large language models. *Proceedings of ASP-DAC 2024*.
Nicol, D., & Macfarlane-Dick, D. (2006). Formative assessment and self-regulated learning: A model and seven principles of good feedback practice. *Studies in Higher Education, 31*(2), 199–218.
Nongkhai, L. N., Wang, J., Wynn, A., & Mendori, T. (2026). Evaluating adaptive and generative AI-based feedback and recommendations in a knowledge-graph-integrated programming learning system. *Computers and Education: Artificial Intelligence, 10*, 100526.
Phung, T., et al. (2023). Generating high-precision feedback for programming syntax errors using large language models. *Proceedings of EDM 2023*.
Phung, T., et al. (2024). Automating human tutor-style programming feedback: Leveraging GPT-4 tutor model for hint generation and GPT-3.5 student model for hint validation. *Proceedings of LAK 2024*.
Pozdniakov, S., et al. (2024). Large language models meet user interfaces: The case of provisioning feedback. *Computers and Education: Artificial Intelligence, 7*, 100289.
Shute, V. J. (2008). Focus on formative feedback. *Review of Educational Research, 78*(1), 153–189.
Tan, S., et al. (2025). JudgeBench: A benchmark for evaluating LLM-based judges. *Proceedings of ICLR 2025*.
Yasir, T., et al. (2026a). When verification hurts: Asymmetric effects of multi-agent feedback in logic proof tutoring. arXiv:2603.27076.
Yasir, T., et al. (2026b). Confirming correct, missing the rest: LLM tutoring agents struggle where feedback matters most. arXiv:2605.16207.
Ye, J., et al. (2025). Justice or prejudice? Quantifying biases in LLM-as-a-judge. *Proceedings of ICLR 2025*.
RTL-SMARTIE: An AI-assisted tutor for RTL design education. (2026). *Proceedings of GLSVLSI 2026*. https://doi.org/10.1145/3787109.3816047
LeanTutor: Towards a verified AI mathematical proof tutor. (2026). arXiv:2506.08321.
VPLAS: A Verilog programming learning assistant system with a guided learning method. (2025). *Future Internet, 17*(8), 333.
Dean of LLM tutors: Evaluating LLM-generated tutoring feedback before delivery. (2025). arXiv:2508.05952.
VeriReason: Reinforcement learning with testbench feedback for Verilog generation. (2026). *Proceedings of GLSVLSI 2026*. https://doi.org/10.1145/3787109.3815310
Terry, M., Kulkarni, C., Wattenberg, M., Dixon, L., & Morris, M. R. (2023). Interactive AI alignment: Specification, process, and evaluation alignment. arXiv:2311.00710.
