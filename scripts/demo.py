#!/usr/bin/env python3
"""End-to-end demo on the corpus arbiter objective (no API keys required).

Runs the executing backbone on three artifacts drawn from the paper's running
example (§4.2) and then drives the feedback gate (Algorithm 2) on a good and a
bad tutor message. Requires only Icarus Verilog (`iverilog`, `vvp`).

    PYTHONPATH=src python scripts/demo.py
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "src"))

from trustgrade import Objective, Verdict, assess, TutorMessage, gate  # noqa: E402

EX = os.path.join(HERE, "..", "examples", "arbiter")

arbiter = Objective(
    name="round_robin_arbiter_4",
    module="arbiter_rr",
    reference=os.path.join(EX, "reference.v"),
    property_tb=os.path.join(EX, "property_tb.v"),
    harness=None,  # P3 fairness leaves exact grant timing implementation-defined
    spec="4-way round-robin arbiter: one-hot grant, never grant an idle line, "
         "and no continuously-requesting line may wait more than N+2 cycles.",
)


def show(title, path):
    a = assess(path, arbiter)
    print(f"  {title:<22} -> {a.verdict.value:<3} [{a.layer}]  {a.diagnosis[:80]}")
    return a


def main():
    print("== Algorithm 1: backbone verdicts (three artifacts from the corpus) ==")
    show("reference.v", os.path.join(EX, "reference.v"))          # expect ACC
    show("alt_token.v (valid alt)", os.path.join(EX, "alt_token.v"))  # expect ACC (P4)
    show("buggy_starvation.v", os.path.join(EX, "buggy_starvation.v"))  # expect REJ

    print("\n== Algorithm 2: feedback gate on the buggy submission ==")
    student = os.path.join(EX, "buggy_starvation.v")

    # (a) an HONEST tutor message: correctly says BUGGY, proposes the real fix.
    good = TutorMessage(
        verdict="BUGGY",
        explanation="The priority pointer never advances past the served line, "
                    "so a held request can starve; rotate base to gidx+1.",
        corrected_rtl=os.path.join(EX, "reference.v"),
    )
    d = gate(good, student, arbiter)
    print(f"  honest message  -> delivered={d.delivered}  reason={d.reason}")

    # (b) a HARMFUL tutor message: wrongly says CORRECT (would validate a bug).
    harmful = TutorMessage(
        verdict="CORRECT",
        explanation="Looks good — the arbiter rotates correctly.",
        corrected_rtl=student,
    )
    d2 = gate(harmful, student, arbiter)
    print(f"  harmful message -> delivered={d2.delivered}  reason={d2.reason}")
    print(f"                     learner instead receives: {d2.payload[:90]}")

    ok = (d.delivered and not d2.delivered)
    print("\nRESULT:", "gate delivered the honest message and withheld the harmful one"
          if ok else "UNEXPECTED — check the toolchain")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
