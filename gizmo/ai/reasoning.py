"""Model-backed reasoning adapter for GIZMO agents.

The adapter uses a configured model provider when credentials exist and falls back
to deterministic local synthesis when they do not. This keeps cloud cycles safe,
testable, and never blocked by a missing key.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import os
import urllib.request
from typing import Any

from gizmo.core.models import now_iso


@dataclass
class ReasoningResult:
    ok: bool
    provider: str
    model: str
    prompt: str
    answer: str
    confidence: float
    used_memory_ids: list[str]
    created_at: str
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class ModelReasoner:
    """Small provider wrapper used by cloud agents before they act."""

    def __init__(self, *, provider: str | None = None, model: str | None = None, timeout: int = 45) -> None:
        self.provider = (provider or os.getenv("GIZMO_MODEL_PROVIDER") or os.getenv("AI_PROVIDER") or "local").lower()
        self.model = model or os.getenv("GIZMO_MODEL") or os.getenv("OPENAI_MODEL") or "local-synthesis-v1"
        self.timeout = timeout

    def reason(self, *, agent_id: str, lane: str, objective: str, context: Any, constraints: list[str] | None = None) -> ReasoningResult:
        memory_ids = self._memory_ids(context)
        prompt = self._prompt(agent_id=agent_id, lane=lane, objective=objective, context=context, constraints=constraints or [])
        if self.provider in {"openai", "gpt"} and os.getenv("OPENAI_API_KEY"):
            try:
                answer = self._openai(prompt)
                return ReasoningResult(True, "openai", self.model, prompt, answer, 0.88, memory_ids, now_iso())
            except Exception as exc:
                return ReasoningResult(False, "openai", self.model, prompt, self._fallback_answer(agent_id, lane, objective, context), 0.62, memory_ids, now_iso(), error=type(exc).__name__)
        return ReasoningResult(True, "local", "local-synthesis-v1", prompt, self._fallback_answer(agent_id, lane, objective, context), 0.68, memory_ids, now_iso())

    def _openai(self, prompt: str) -> str:
        api_key = os.environ["OPENAI_API_KEY"]
        body = {
            "model": self.model if self.model != "local-synthesis-v1" else "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a safe, concise GIZMO specialist agent. Use only public knowledge and never store secrets."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
            "max_tokens": 700,
        }
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(body).encode(),
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
        return data["choices"][0]["message"]["content"].strip()

    def _prompt(self, *, agent_id: str, lane: str, objective: str, context: Any, constraints: list[str]) -> str:
        useful = getattr(context, "useful_context", []) or []
        gaps = getattr(context, "gaps", []) or []
        lines = [
            f"Agent: {agent_id}",
            f"Lane: {lane}",
            f"Objective: {objective}",
            "Constraints:",
            *(f"- {item}" for item in constraints),
            "Relevant memory:",
            *(f"- {item.get('title')}: {item.get('summary')}" for item in useful[:6]),
            "Known gaps:",
            *(f"- {item.get('requirement') or item.get('topic')}: {item.get('priority', 'MEDIUM')}" for item in gaps[:6]),
            "Return: plan, evidence needed, safe next action, memory lesson.",
        ]
        return "\n".join(lines)

    @staticmethod
    def _memory_ids(context: Any) -> list[str]:
        useful = getattr(context, "useful_context", []) or []
        return [item.get("id") for item in useful if item.get("id")]

    @staticmethod
    def _fallback_answer(agent_id: str, lane: str, objective: str, context: Any) -> str:
        useful = getattr(context, "useful_context", []) or []
        gaps = getattr(context, "gaps", []) or []
        memory_line = f"Use {len(useful)} retrieved memories before acting."
        gap_line = f"Close {len(gaps)} detected gaps before risky execution." if gaps else "No critical gap detected; continue with safe execution."
        return (
            f"Plan: {agent_id} should improve the {lane} lane for: {objective}. "
            f"{memory_line} {gap_line} "
            "Safe next action: produce a small verified task, record the lesson, and escalate sensitive work for approval. "
            "Memory lesson: future cycles must reason from retrieved context before creating new work."
        )
