"""Diagnosis extraction delta (§4.5).

Maps a rejection to a *structured, actionable* diagnosis. The single design
choice that moved the headline actionability metric: report the **first failing
assertion line** of the simulation log — which names the violated property phi_j
and the witnessing signal values — rather than the simulator's terminal summary
line ("N violations detected"), which names nothing.
"""
from __future__ import annotations

import re

# Lines a property / self-checking testbench emits on the first violated
# invariant. We keep the whole line: it carries the property name, the time, and
# the observed signal values — exactly the "how am I going?" formative content.
_FAILLINE_RE = re.compile(
    r"^.*\b(?:FAILED|FAIL|VIOLATION|ASSERT(?:ION)?\s+FAILED|ERROR)\b[^\n]*$",
    re.IGNORECASE | re.MULTILINE,
)
# iverilog compile errors look like "path:12: error: <msg>".
_COMPILE_ERR_RE = re.compile(r"^[^\n:]*:(\d+):\s*(?:syntax )?error:\s*(.+)$",
                             re.IGNORECASE | re.MULTILINE)


def extract_compile_diagnosis(log: str) -> str:
    """delta_compile — first structural/syntactic error with its line number."""
    m = _COMPILE_ERR_RE.search(log)
    if m:
        return f"compile error at line {m.group(1)}: {m.group(2).strip()}"
    first = next((ln for ln in log.splitlines() if ln.strip()), "")
    return f"does not elaborate: {first.strip()}" if first else "does not elaborate"


def extract_invariant_diagnosis(log: str) -> str:
    """delta_invariant — the FIRST failing assertion line (named phi_j + witnesses).

    This is the actionable form. Returning `log.splitlines()[-1]` (the summary)
    instead is the ablation that dropped actionable diagnoses to ~9%.
    """
    m = _FAILLINE_RE.search(log)
    if m:
        return m.group(0).strip()
    # Fall back to the last non-empty line only if no violation line was printed.
    tail = [ln for ln in log.splitlines() if ln.strip()]
    return tail[-1].strip() if tail else "property violation (no diagnostic emitted)"


def hang_diagnosis(_log: str) -> str:
    """delta_hang — simulation exceeded the watchdog W.

    Classified as a combinational-loop / non-advancing-clock fault. The soundness
    argument: a correct synchronous design under a bounded, clock-driven property
    testbench always terminates; a timeout therefore witnesses a real defect.
    """
    return ("simulation did not terminate within the watchdog "
            "(combinational loop or non-advancing clock)")
