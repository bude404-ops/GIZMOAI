"""Sandbox-first agent factory."""
from __future__ import annotations

from gizmo.core.models import AgentDefinition


class AgentFactory:
    def propose_specialist(self, specialty: str, reason: str) -> AgentDefinition:
        slug = "".join(ch.lower() if ch.isalnum() else "-" for ch in specialty).strip("-")
        return AgentDefinition(
            id=f"sandbox-{slug}",
            name=f"{specialty} Specialist",
            role=reason,
            objectives=[f"Provide specialized {specialty} expertise", "Run in sandbox until validation passes"],
            allowed_tools=["memory.search", "memory.add", "sandbox.run"],
            memory_namespace=f"sandbox-{slug}",
            task_types=[slug],
            evaluation_criteria=["Improves task success", "Does not require unrestricted permissions", "Passes sandbox validation"],
            trusted=False,
            sandbox_required=True,
        )

    def validate_for_promotion(self, agent: AgentDefinition, test_results: list[dict]) -> bool:
        if not agent.sandbox_required or agent.trusted:
            return False
        return bool(test_results) and all(result.get("passed") for result in test_results)
