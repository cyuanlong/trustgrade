"""Feedback gate (Algorithm 2, GATE) — §4.3.

The gate is the delivery-time guarantee. It sits between an LLM tutor and the
learner and enforces the framework's two safety principles operationally:

  P2  verified content or verified uncertainty — nothing correctness-bearing
      reaches the learner unless an executing check has confirmed it;
  P3  validate-or-withhold, never rewrite — the gate has exactly two actions,
      DELIVER the tutor's message unchanged or FALL BACK to the backbone's own
      verified diagnosis. It never edits the explanation `e`.

A tutor message is m = (v_t, e, f): a verdict claim, a natural-language
explanation, and a proposed corrected module. The gate applies two checks:

  C1  verdict-consistency — the tutor's verdict must match the backbone's verdict
      on the student's actual submission;
  C2  fix-soundness — the proposed fix must itself earn ACC from the *full*
      backbone (not the property testbench alone; see note below).

Only if both pass is the message delivered, tagged "verified".
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .backbone import Assessment, Objective, Verdict, assess


@dataclass
class TutorMessage:
    """m = (v_t, e, f)."""

    verdict: str  # v_t : the tutor's claim, mapped to ACC/REJ/UNC (see _tutor_verdict)
    explanation: str  # e : never mutated by the gate (P3)
    corrected_rtl: Optional[str] = None  # f : path to the proposed fix module


@dataclass
class GateDecision:
    delivered: bool
    payload: str  # the verified explanation (delivered) or the backbone diagnosis (fallback)
    verdict: Verdict  # the backbone verdict on the student submission
    reason: str  # "verified" | "C1:verdict-mismatch" | "C2:fix-unsound"
    student_assessment: Assessment
    fix_assessment: Optional[Assessment] = None


# The tutor speaks in {CORRECT, BUGGY}; the backbone in {ACC, REJ, UNC}. A
# "CORRECT" claim is consistent with ACC (and, conservatively, UNC — a valid
# alternative is not wrong). "BUGGY" is consistent with REJ.
def _tutor_says_correct(v_t: str) -> bool:
    return v_t.strip().upper() in {"CORRECT", "ACC", "PASS", "OK"}


def _consistent(v_t: str, v_backbone: Verdict) -> bool:
    """C1: is the tutor's claim consistent with the backbone verdict?"""
    if _tutor_says_correct(v_t):
        return v_backbone in (Verdict.ACC, Verdict.UNC)
    return v_backbone == Verdict.REJ


def gate(
    m: TutorMessage,
    submission: str,
    o: Objective,
    *,
    watchdog: float = 3.0,
) -> GateDecision:
    """GATE(m, s, o) — Algorithm 2.

    Returns a `GateDecision`. On C1 or C2 failure the learner receives the
    backbone's verified diagnosis (`delta(s)`) instead of the tutor's message —
    harmful feedback cannot reach the learner by construction.
    """
    a = assess(submission, o, watchdog=watchdog)  # backbone verdict on student work

    # C1 — verdict consistency
    if not _consistent(m.verdict, a.verdict):
        return GateDecision(False, a.diagnosis, a.verdict, "C1:verdict-mismatch", a)

    # If the tutor (correctly) judged the work already correct, there is no fix
    # to check; deliver the explanation.
    if a.verdict in (Verdict.ACC, Verdict.UNC):
        return GateDecision(True, m.explanation, a.verdict, "verified", a)

    # C2 — the proposed fix must pass the FULL backbone.
    #
    # Why the full backbone and not the property testbench alone: a test-only
    # check inherits the residual exposure R(Phi, {}) of Proposition 2 — a fix
    # that evades the property set entirely would pass. On the paper's corpus
    # 9/84 bugs evade the property set; a test-only gate misses exactly those.
    if m.corrected_rtl is None:
        return GateDecision(False, a.diagnosis, a.verdict, "C2:no-fix-provided", a)
    af = assess(m.corrected_rtl, o, watchdog=watchdog)
    if af.verdict != Verdict.ACC:
        return GateDecision(False, a.diagnosis, a.verdict, "C2:fix-unsound", a, af)

    return GateDecision(True, m.explanation, a.verdict, "verified", a, af)
