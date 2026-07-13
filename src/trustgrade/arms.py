"""The six gating paradigms (§5.4, RQ4), on one interface.

Each condition operationalizes a paradigm from the tutoring literature and is
implemented as a `Reviewer`: given a tutor message, the student's submission,
and the objective, it returns APPROVE (deliver as generated) or REJECT (withhold
/ fall back). Running all six against byte-identical items is what makes the
comparison a real reimplemented-baseline experiment rather than a table of
numbers copied across papers.

    ungated          — deliver everything (CodeAid / Azaiz deployment practice)
    simulated_student— a GPT-3.5-class model attempts the repair k times from the
                       explanation alone; approve if >= threshold pass the property
                       testbench (PyFiXV / GPT4Hints paradigm)
    llm_review       — a reviewer LLM statically judges the fix vs the spec
                       (the "Dean of LLM Tutors" paradigm); affordable vs frontier
                       is just which model backs the client
    test_only        — gate on the property testbench alone (CodeTailor paradigm)
    full_gate        — Algorithm 2 (this work): C1 + C2 over the full backbone

The deterministic arms (test_only, full_gate) need only Icarus Verilog. The LLM
arms need an `LLMClient` (see llm.py); they are faithful drivers, not frozen
transcripts — reproducing the paper's exact per-item verdicts requires the
archived verdict files or re-running with API keys.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Optional, Protocol

from .backbone import Objective, Verdict, assess
from .gate import TutorMessage, gate
from .llm import LLMClient
from .prompts import REVIEWER_GATE_PROMPT


@dataclass
class ReviewOutcome:
    approve: bool
    reason: str


class Reviewer(Protocol):
    name: str

    def __call__(self, m: TutorMessage, submission: str, o: Objective) -> ReviewOutcome:
        ...


# --------------------------------------------------------------------------- #
# 1. Ungated
# --------------------------------------------------------------------------- #
class Ungated:
    name = "ungated"

    def __call__(self, m: TutorMessage, submission: str, o: Objective) -> ReviewOutcome:
        return ReviewOutcome(True, "delivered as generated (no gate)")


# --------------------------------------------------------------------------- #
# 2. Simulated student (PyFiXV / GPT4Hints validation paradigm)
# --------------------------------------------------------------------------- #
class SimulatedStudent:
    """A GPT-3.5-class model, given only the buggy code and the tutor's
    explanation (NOT the corrected code), attempts the repair `k` times; the
    message is approved iff at least `threshold` attempts pass the property
    testbench. Artifact-blind by construction — it never sees `f`."""

    name = "simulated_student"

    def __init__(self, client: LLMClient, k: int = 3, threshold: int = 2):
        self.client = client
        self.k = k
        self.threshold = threshold

    def __call__(self, m: TutorMessage, submission: str, o: Objective) -> ReviewOutcome:
        buggy = open(submission).read()
        passes = 0
        for _ in range(self.k):
            repair = self.client.repair_from_explanation(o.spec, buggy, m.explanation)
            if repair is None:
                continue
            path = _write_tmp(repair, o.module)
            if assess(path, o).verdict == Verdict.ACC:
                passes += 1
        ok = passes >= self.threshold
        return ReviewOutcome(ok, f"simulated-student repairs passing: {passes}/{self.k}")


# --------------------------------------------------------------------------- #
# 3/4. LLM review (affordable = DeepSeek-chat; frontier = Claude)
# --------------------------------------------------------------------------- #
class LLMReview:
    """Static review of the proposed fix against the spec — the reviewer never
    executes anything. `client` fixes the tier (affordable vs frontier)."""

    def __init__(self, client: LLMClient, name: str = "llm_review"):
        self.client = client
        self.name = name

    def __call__(self, m: TutorMessage, submission: str, o: Objective) -> ReviewOutcome:
        fix = open(m.corrected_rtl).read() if m.corrected_rtl else "(no fix provided)"
        verdict = self.client.review(
            REVIEWER_GATE_PROMPT, spec=o.spec, explanation=m.explanation, fix=fix
        )
        approve = verdict.strip().upper().startswith("APPROVE")
        return ReviewOutcome(approve, f"reviewer said {verdict.strip()!r}")


# --------------------------------------------------------------------------- #
# 5. Test-only (CodeTailor paradigm)
# --------------------------------------------------------------------------- #
class TestOnly:
    """Gate on the property testbench alone: approve iff the proposed fix passes
    L0+L1. Inherits the residual exposure R(Phi, {}) of Proposition 2 — fixes
    that evade the property set entirely slip through."""

    name = "test_only"

    def __call__(self, m: TutorMessage, submission: str, o: Objective) -> ReviewOutcome:
        if m.corrected_rtl is None:
            return ReviewOutcome(False, "no fix to test")
        # Assess with no differential harness -> Phi-only decision.
        phi_only = Objective(o.name, o.module, o.reference, o.property_tb,
                             harness=None, spec=o.spec)
        v = assess(m.corrected_rtl, phi_only).verdict
        return ReviewOutcome(v == Verdict.ACC, f"property-testbench verdict {v}")


# --------------------------------------------------------------------------- #
# 6. Full execution gate (this work) — Algorithm 2
# --------------------------------------------------------------------------- #
class FullGate:
    name = "full_gate"

    def __call__(self, m: TutorMessage, submission: str, o: Objective) -> ReviewOutcome:
        d = gate(m, submission, o)
        return ReviewOutcome(d.delivered, d.reason)


# --------------------------------------------------------------------------- #
def _write_tmp(source: str, module: str) -> str:
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".v", prefix=f"{module}_")
    with open(fd, "w") as fh:
        fh.write(source)
    return path
