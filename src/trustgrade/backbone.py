"""Assessment backbone — the executing verifier (Algorithm 1, ASSESS).

Reference implementation of the three-layer verdict of the TrustGrade paper
(§4.2). Given a student submission `s` and a learning objective `o`, it returns
a three-valued verdict together with a structured diagnosis:

    L0  COMPILE      — does `s` elaborate?                 (REJ + delta_compile)
    L1  SIMULATE     — property testbench, watchdog W      (REJ + delta_invariant / delta_hang)
    L2  DIFFERENTIAL — observational equivalence to `r`    (ACC | UNC + delta_divergence)

The backbone is deterministic (fixed seeds inside the testbenches, a wall-clock
watchdog on every simulation) and orchestrates Icarus Verilog (`iverilog`,
`vvp`). It never inspects the *text* of the student's code — only its executed
behaviour — which is what makes the verdict model-independent (Proposition 1).

This module is the scientifically load-bearing part of the system: the safety
guarantee of the feedback gate (`gate.py`) and the termination guarantee of the
scaffold validator (`scaffold.py`) both reduce to calls into ASSESS.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .diagnosis import (
    extract_compile_diagnosis,
    extract_invariant_diagnosis,
    hang_diagnosis,
)


class Verdict(str, Enum):
    """Three-valued verdict V_B (Definition 3)."""

    ACC = "ACC"  # meets Phi and matches the reference under the observation harness
    REJ = "REJ"  # provably violates the contract (compile / invariant / hang)
    UNC = "UNC"  # meets Phi but diverges from the reference — a *candidate* alternative


@dataclass
class Objective:
    """A learning objective o = (sigma, I, r, Phi, H) (§3.1).

    Only the executable components are needed by the backbone:
      module      — the module name shared by the reference and all submissions (I)
      reference   — path to the reference RTL `r`
      property_tb — path to the property testbench encoding Phi (asserts invariants only)
      harness     — path to the differential observation harness H (optional; enables L2)
    `spec` (sigma) is carried for the LLM roles, not the backbone.
    """

    name: str
    module: str
    reference: str
    property_tb: str
    harness: Optional[str] = None
    spec: str = ""


@dataclass
class Assessment:
    """Return value of ASSESS: (V_B(s), delta(s))."""

    verdict: Verdict
    diagnosis: str
    layer: str  # "L0" | "L1" | "L2" — which layer decided
    detail: dict = field(default_factory=dict)


# ----------------------------------------------------------------------------- #
# Low-level Icarus Verilog orchestration
# ----------------------------------------------------------------------------- #

_IVERILOG = os.environ.get("IVERILOG", "iverilog")
_VVP = os.environ.get("VVP", "vvp")


def _run(cmd: list[str], cwd: str, timeout: float) -> tuple[int, str, str, bool]:
    """Run a command with a wall-clock watchdog.

    Returns (returncode, stdout, stderr, timed_out). A timeout is reported, not
    raised: a simulation that fails to terminate is a *sound rejection* (a
    combinational loop or a non-advancing clock is a real defect), so the caller
    treats `timed_out=True` as delta_hang rather than an error.
    """
    try:
        p = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return p.returncode, p.stdout, p.stderr, False
    except subprocess.TimeoutExpired as e:
        out = e.stdout or ""
        err = e.stderr or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        if isinstance(err, bytes):
            err = err.decode("utf-8", "replace")
        return 124, out, err, True


def _compile(sources: list[str], out_vvp: str, cwd: str, timeout: float) -> tuple[bool, str]:
    """L0: elaborate `sources` into a runnable image. Returns (ok, log)."""
    rc, so, se, _ = _run(
        [_IVERILOG, "-g2012", "-o", out_vvp, *sources], cwd=cwd, timeout=timeout
    )
    return rc == 0, (so + se).strip()


def _simulate(vvp_image: str, cwd: str, timeout: float) -> tuple[str, bool]:
    """Run a compiled image. Returns (stdout+stderr, timed_out)."""
    rc, so, se, to = _run([_VVP, "-n", vvp_image], cwd=cwd, timeout=timeout)
    return (so + se), to


# A property/self-checking testbench prints PASS on success and one or more
# FAIL/FAILED/VIOLATION lines on the first violated invariant.
_PASS_RE = re.compile(r"\bPASS(?:ED)?\b")
_FAIL_RE = re.compile(r"\b(?:FAIL(?:ED)?|VIOLATION|ERROR)\b")


def _passed(log: str) -> bool:
    return bool(_PASS_RE.search(log)) and not _FAIL_RE.search(log)


# ----------------------------------------------------------------------------- #
# Algorithm 1 — layered verdict
# ----------------------------------------------------------------------------- #


def assess(
    submission: str,
    o: Objective,
    *,
    watchdog: float = 3.0,
    compile_timeout: float = 20.0,
    workdir: Optional[str] = None,
) -> Assessment:
    """ASSESS(s, o) — the three-layer backbone verdict (Algorithm 1).

    Parameters
    ----------
    submission : path to the RTL file under test (the student's `s`, a proposed
                 fix `f`, or a scaffold step reference `r_i`).
    o          : the objective, supplying the module name, property testbench,
                 reference, and (optionally) the differential harness.
    watchdog   : per-simulation wall-clock bound W (seconds). A hang past W is a
                 sound rejection (delta_hang), never an exception.

    Returns an `Assessment` (verdict, diagnosis, deciding layer).
    """
    keep = workdir is not None
    tmp = workdir or tempfile.mkdtemp(prefix="tg_assess_")
    try:
        sub = shutil.copy(submission, os.path.join(tmp, "dut.v"))

        # ---- L0: compilation against the property testbench ------------------
        img = os.path.join(tmp, "sim_l1.vvp")
        ok, clog = _compile([sub, o.property_tb], img, tmp, compile_timeout)
        if not ok:
            return Assessment(Verdict.REJ, extract_compile_diagnosis(clog), "L0",
                              {"log": clog})

        # ---- L1: property simulation (invariants only, never a golden model) --
        log, timed_out = _simulate(img, tmp, watchdog)
        if timed_out:
            return Assessment(Verdict.REJ, hang_diagnosis(log), "L1", {"log": log})
        if not _passed(log):
            return Assessment(Verdict.REJ, extract_invariant_diagnosis(log), "L1",
                              {"log": log})

        # ---- L2: differential observation vs the reference under H -----------
        # If no harness is supplied the contract is Phi alone: passing L1 is ACC.
        if not o.harness:
            return Assessment(Verdict.ACC, "meets Phi (no differential harness)", "L1",
                              {"log": log})

        y_s = _observe(sub, o, tmp, "obs_s.vvp", watchdog, compile_timeout)
        y_r = _observe(o.reference, o, tmp, "obs_r.vvp", watchdog, compile_timeout)
        if y_s is None or y_r is None:
            # Harness inapplicable to this submission (e.g. port mismatch): the
            # contract Phi is already met, so it is a valid alternative (UNC),
            # not a rejection.
            return Assessment(Verdict.UNC, "meets Phi; harness inapplicable", "L2",
                              {"log": log})
        if y_s == y_r:
            return Assessment(Verdict.ACC, "meets Phi; matches r under H", "L2",
                              {"log": log})
        return Assessment(
            Verdict.UNC,
            _divergence_diagnosis(y_s, y_r),
            "L2",
            {"trace_s": y_s[:400], "trace_r": y_r[:400]},
        )
    finally:
        if not keep:
            shutil.rmtree(tmp, ignore_errors=True)


def _observe(
    rtl: str, o: Objective, cwd: str, img_name: str, watchdog: float, ctimeout: float
) -> Optional[str]:
    """Run `rtl` through the differential harness H and return its trace.

    Returns None if the harness cannot be applied (compile failure under H —
    typically an interface mismatch), which the caller reads as "Phi-valid but
    not comparable" rather than a rejection.
    """
    assert o.harness is not None
    img = os.path.join(cwd, img_name)
    ok, _ = _compile([rtl, o.harness], img, cwd, ctimeout)
    if not ok:
        return None
    trace, timed_out = _simulate(img, cwd, watchdog)
    if timed_out:
        return None
    # The harness prints an observation stream (e.g. "@<t> <signals>"); compare
    # only those lines so incidental $display noise does not cause false UNC.
    obs = [ln for ln in trace.splitlines() if ln.startswith("@")]
    return "\n".join(obs) if obs else trace.strip()


def _divergence_diagnosis(y_s: str, y_r: str) -> str:
    """First differing observation line between submission and reference."""
    ls, lr = y_s.splitlines(), y_r.splitlines()
    for i, (a, b) in enumerate(zip(ls, lr)):
        if a != b:
            return f"divergence from reference at obs {i}: got {a!r}, expected {b!r}"
    if len(ls) != len(lr):
        return f"divergence: observation length {len(ls)} vs reference {len(lr)}"
    return "divergence from reference under H"
