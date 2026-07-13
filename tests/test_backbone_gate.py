"""End-to-end tests for the backbone, gate, and scaffold on the arbiter example.

These require Icarus Verilog on PATH (`iverilog`, `vvp`) and are skipped if it is
absent. Run: `PYTHONPATH=src python -m pytest tests/ -v`
"""
import os
import shutil

import pytest

from trustgrade import Objective, Verdict, assess, TutorMessage, gate
from trustgrade.scaffold import ScaffoldStep, validate_scaffold

EX = os.path.join(os.path.dirname(__file__), "..", "examples", "arbiter")
HAS_IVERILOG = shutil.which(os.environ.get("IVERILOG", "iverilog")) is not None
pytestmark = pytest.mark.skipif(not HAS_IVERILOG, reason="Icarus Verilog not installed")


@pytest.fixture
def arbiter():
    return Objective(
        name="round_robin_arbiter_4",
        module="arbiter_rr",
        reference=os.path.join(EX, "reference.v"),
        property_tb=os.path.join(EX, "property_tb.v"),
        harness=None,
        spec="4-way round-robin arbiter with a fairness bound.",
    )


def test_reference_accepted(arbiter):
    assert assess(os.path.join(EX, "reference.v"), arbiter).verdict == Verdict.ACC


def test_valid_alternative_accepted(arbiter):
    # P4: a structurally distinct valid implementation must not be rejected.
    assert assess(os.path.join(EX, "alt_token.v"), arbiter).verdict == Verdict.ACC


def test_buggy_rejected_with_actionable_diagnosis(arbiter):
    a = assess(os.path.join(EX, "buggy_starvation.v"), arbiter)
    assert a.verdict == Verdict.REJ
    # delta names the violated property and witnessing values (not a bare summary)
    assert "fairness" in a.diagnosis.lower() or "starvation" in a.diagnosis.lower()


def test_gate_delivers_honest_message(arbiter):
    student = os.path.join(EX, "buggy_starvation.v")
    m = TutorMessage("BUGGY", "pointer fails to rotate; use gidx+1",
                     os.path.join(EX, "reference.v"))
    d = gate(m, student, arbiter)
    assert d.delivered and d.reason == "verified"


def test_gate_withholds_false_correct(arbiter):
    # C1: tutor claims CORRECT on buggy work -> withheld, learner gets delta(s).
    student = os.path.join(EX, "buggy_starvation.v")
    m = TutorMessage("CORRECT", "looks fine", student)
    d = gate(m, student, arbiter)
    assert not d.delivered and d.reason.startswith("C1")


def test_gate_withholds_unsound_fix(arbiter):
    # C2: tutor correctly says BUGGY but its 'fix' is still broken -> withheld.
    student = os.path.join(EX, "buggy_starvation.v")
    m = TutorMessage("BUGGY", "try this", student)  # 'fix' == the buggy code
    d = gate(m, student, arbiter)
    assert not d.delivered and d.reason.startswith("C2")


def test_scaffold_final_step_must_meet_contract(arbiter):
    # A one-step 'scaffold' whose endpoint is the buggy module must fail s3.
    tb = _trivial_pass_tb()
    step = ScaffoldStep("build the arbiter", "which line has priority next?",
                        os.path.join(EX, "buggy_starvation.v"), tb)
    res = validate_scaffold([step], arbiter)
    assert not res.ok and res.failed_step == 1


def _trivial_pass_tb():
    """A checkpoint testbench that always prints PASS (isolates the s3 check)."""
    import tempfile
    fd, path = tempfile.mkstemp(suffix="_tb.v")
    with open(fd, "w") as fh:
        fh.write('module step_tb; initial begin $display("PASS"); $finish; end '
                 'arbiter_rr d(.clk(1\'b0),.rst_n(1\'b1),.req(4\'b0),.grant()); endmodule\n')
    return path
