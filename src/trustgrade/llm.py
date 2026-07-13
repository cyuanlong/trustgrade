"""Thin LLM client used by the review / simulated-student / tutor arms.

The client isolates the two model tiers the paper uses — an *affordable*
reviewer (DeepSeek-chat, OpenAI-compatible API) and a *frontier* reviewer
(Claude). Only the arms that place an LLM inside the loop need this; the
execution gate itself is model-free.

Design notes
------------
* No provider SDK is imported at module load, so the deterministic arms and the
  backbone run with zero extra dependencies. `DeepSeekClient` uses the stdlib
  HTTP client against the OpenAI-compatible endpoint.
* Set the API key via environment (`DEEPSEEK_API_KEY` / `ANTHROPIC_API_KEY`);
  never hard-code keys.
* `EchoClient` is a deterministic stub for offline tests: it approves iff the
  tutor's own verdict claims the fix is correct, so the LLM-arm plumbing can be
  exercised without network access (it is NOT a model of reviewer accuracy).
"""
from __future__ import annotations

import json
import os
import re
import urllib.request
from typing import Optional, Protocol


class LLMClient(Protocol):
    def review(self, prompt: str, *, spec: str, explanation: str, fix: str) -> str:
        """Return a verdict string beginning with APPROVE or REJECT."""
        ...

    def repair_from_explanation(
        self, spec: str, buggy_code: str, explanation: str
    ) -> Optional[str]:
        """Simulated-student repair: return a full module, or None on failure."""
        ...


def _extract_module(text: str) -> Optional[str]:
    """Pull the first `module ... endmodule` block out of a model response."""
    m = re.search(r"\bmodule\b.*?\bendmodule\b", text, re.DOTALL)
    return m.group(0) if m else None


class DeepSeekClient:
    """Affordable reviewer / simulated student via the OpenAI-compatible API."""

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        base_url: str = "https://api.deepseek.com/v1/chat/completions",
        temperature: float = 0.0,
        timeout: float = 60.0,
    ):
        self.model = model
        self.api_key = api_key or os.environ.get("DEEPSEEK_API_KEY", "")
        self.base_url = base_url
        self.temperature = temperature
        self.timeout = timeout

    def _chat(self, system: str, user: str) -> str:
        if not self.api_key:
            raise RuntimeError("DEEPSEEK_API_KEY not set")
        body = json.dumps({
            "model": self.model,
            "temperature": self.temperature,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }).encode()
        req = urllib.request.Request(
            self.base_url, data=body,
            headers={"Content-Type": "application/json",
                     "Authorization": f"Bearer {self.api_key}"},
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as r:
            payload = json.loads(r.read())
        return payload["choices"][0]["message"]["content"]

    def review(self, prompt: str, *, spec: str, explanation: str, fix: str) -> str:
        user = (f"Assignment spec + interface:\n{spec}\n\n"
                f"Tutor's explanation:\n{explanation}\n\n"
                f"Proposed corrected code:\n{fix}\n\nVerdict:")
        return self._chat(prompt, user)

    def repair_from_explanation(self, spec, buggy_code, explanation) -> Optional[str]:
        system = ("You are a student in a Verilog course. Using ONLY the tutor's "
                  "explanation, rewrite the module to fix the bug. Output one "
                  "complete compilable module, same name and ports.")
        user = (f"Spec:\n{spec}\n\nYour buggy code:\n{buggy_code}\n\n"
                f"Tutor's explanation of what to fix:\n{explanation}\n\n"
                f"Your corrected module:")
        return _extract_module(self._chat(system, user))


class EchoClient:
    """Deterministic offline stub — plumbing only, not an accuracy model."""

    def __init__(self, approve: bool = True):
        self.approve = approve

    def review(self, prompt: str, *, spec: str, explanation: str, fix: str) -> str:
        return "APPROVE" if self.approve else "REJECT"

    def repair_from_explanation(self, spec, buggy_code, explanation) -> Optional[str]:
        return buggy_code  # a student who learns nothing from the explanation
