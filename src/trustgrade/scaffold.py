"""Verified scaffolding (Algorithm 3, VALIDATE-SCAFFOLD) — §4.4.

An LLM decomposes an assignment into 3-4 ordered steps, each a tuple
(g_i, h_i, r_i, c_i): a student-facing goal, a Socratic hint, a reference RTL
state after the step, and a *checkpoint testbench* the student's partial work
can be run against. The validator turns a *plausible* scaffold into a *verified*
one by checking three conditions before any step is delivered:

  s1  every step's reference compiles together with its checkpoint testbench;
  s2  every step's reference passes its own checkpoint;
  s3  the final step's reference satisfies the assignment contract Phi
      (i.e. earns ACC — or UNC as a valid alternative — from the full backbone).

s3 is what distinguishes a verified scaffold: the delivered sequence provably
terminates in a contract-satisfying solution. Any failure triggers regeneration
of the offending step.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from typing import Optional

from .backbone import Objective, Verdict, assess
from .backbone import _IVERILOG, _VVP, _passed  # reuse the vetted primitives


@dataclass
class ScaffoldStep:
    goal: str
    hint: str
    step_rtl: str  # path to r_i (a complete compilable module)
    step_tb: str   # path to c_i (a self-checking checkpoint testbench: prints PASS/FAIL)


@dataclass
class ScaffoldResult:
    ok: bool
    failed_step: Optional[int] = None  # 1-indexed step that must be regenerated
    reason: str = "all steps validated; endpoint meets the contract"


def _compile_and_run(rtl: str, tb: str, watchdog: float, ctimeout: float) -> bool:
    """s1+s2 for one step: compile r_i with c_i, then run and require PASS."""
    tmp = tempfile.mkdtemp(prefix="tg_scaffold_")
    try:
        r = shutil.copy(rtl, os.path.join(tmp, "step.v"))
        t = shutil.copy(tb, os.path.join(tmp, "step_tb.v"))
        img = os.path.join(tmp, "step.vvp")
        c = subprocess.run([_IVERILOG, "-g2012", "-o", img, r, t],
                           cwd=tmp, capture_output=True, text=True, timeout=ctimeout)
        if c.returncode != 0:
            return False  # s1 fails
        try:
            s = subprocess.run([_VVP, "-n", img], cwd=tmp,
                               capture_output=True, text=True, timeout=watchdog)
        except subprocess.TimeoutExpired:
            return False  # a hanging checkpoint is a failed checkpoint
        return _passed(s.stdout + s.stderr)  # s2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def validate_scaffold(
    steps: list[ScaffoldStep],
    o: Objective,
    *,
    watchdog: float = 3.0,
    compile_timeout: float = 20.0,
) -> ScaffoldResult:
    """VALIDATE-SCAFFOLD(<(g_i,h_i,r_i,c_i)>, o) — Algorithm 3.

    Returns ScaffoldResult(ok=True) only if s1-s3 all hold; otherwise names the
    1-indexed step to regenerate.
    """
    for i, st in enumerate(steps, start=1):
        if not _compile_and_run(st.step_rtl, st.step_tb, watchdog, compile_timeout):
            return ScaffoldResult(False, i, f"step {i} failed its checkpoint (s1/s2)")

    # s3 — the endpoint must satisfy the assignment contract, not merely its own
    # checkpoint. UNC (a legitimate alternative implementation) is accepted.
    endpoint = assess(steps[-1].step_rtl, o, watchdog=watchdog,
                      compile_timeout=compile_timeout)
    if endpoint.verdict not in (Verdict.ACC, Verdict.UNC):
        return ScaffoldResult(False, len(steps),
                              f"final step does not meet the contract (s3): {endpoint.diagnosis}")
    return ScaffoldResult(True)
