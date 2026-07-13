"""TrustGrade — an execution-gated framework for trustworthy LLM tutoring.

Reference implementation of the verification backbone (Algorithm 1), the
feedback gate (Algorithm 2), the scaffold validator (Algorithm 3), the six
gating-paradigm reviewers (§5.4), and the evaluation statistics (§5.3) from:

    "Verify Before You Teach: An Execution-Gated Framework and System for
     Trustworthy LLM Tutoring in Digital Hardware Design Education."

The backbone / gate / scaffold / stats are deterministic and require only Icarus
Verilog. The LLM-in-the-loop arms additionally require an `LLMClient`.
"""
from .backbone import Assessment, Objective, Verdict, assess
from .gate import GateDecision, TutorMessage, gate
from .scaffold import ScaffoldResult, ScaffoldStep, validate_scaffold
from . import arms, stats, prompts, llm

__all__ = [
    "Verdict", "Objective", "Assessment", "assess",
    "TutorMessage", "GateDecision", "gate",
    "ScaffoldStep", "ScaffoldResult", "validate_scaffold",
    "arms", "stats", "prompts", "llm",
]

__version__ = "1.0.0"
