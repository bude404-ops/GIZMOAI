"""Dynamic capability registry for the general-purpose GIZMO worker."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


@dataclass
class CapabilityRecord:
    name: str
    description: str
    tools: list[str]
    agents: list[str]
    providers: list[str]
    permissions: list[str]
    cost: str
    reliability: float
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    verification_method: str
    mode: str = "AUTO"
    domains: list[str] = field(default_factory=list)
    dangerous_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_CAPABILITIES: list[CapabilityRecord] = [
    CapabilityRecord("question_answer", "Answer questions using memory first and research when freshness or uncertainty requires it.", ["memory.search", "web.search"], ["agent-02", "agent-27"], ["memory", "web"], ["read"], "low", 0.82, {"question": "string"}, {"answer": "string", "evidence": "array"}, "answer includes confidence and sources when researched", domains=["general question", "learning"]),
    CapabilityRecord("web_research", "Search, collect, filter, read, cross-check, synthesize, cite, and store useful public knowledge.", ["web.search", "web.read", "memory.add"], ["agent-02", "agent-20", "agent-23", "agent-27"], ["internet", "memory"], ["read", "memory_write"], "low", 0.78, {"topic": "string"}, {"findings": "array", "citations": "array"}, "sources are cited and conflicts are tracked", domains=["research", "web investigation", "market research", "current events"]),
    CapabilityRecord("software_development", "Build, test, debug, document, and verify real software projects.", ["file.read", "file.write", "sandbox.run", "code.test", "git.branch", "memory.add"], ["agent-01", "agent-03", "agent-06", "agent-07", "agent-08", "agent-09", "agent-11", "agent-12", "agent-23", "agent-27"], ["terminal", "filesystem", "git"], ["read", "write", "execute", "test", "memory_write"], "medium", 0.8, {"objective": "string", "repository": "string?"}, {"artifacts": "array", "tests": "array", "verification": "object"}, "files/tests/build output must exist", domains=["coding", "application development", "debugging", "database operation", "deployment", "automation"], dangerous_actions=["deploy", "production_write"]),
    CapabilityRecord("github", "Inspect repositories, modify files, create commits/PRs, monitor CI, and preserve repo relationships in memory.", ["git.branch", "github.pr", "code.test", "memory.add"], ["agent-10", "agent-11", "agent-23", "agent-27"], ["git", "github"], ["git", "external_write", "test", "memory_write"], "medium", 0.76, {"repo": "string", "objective": "string"}, {"commits": "array", "checks": "array"}, "git status, diff, tests, and CI state logged", domains=["GitHub operation", "project management"], dangerous_actions=["merge", "force_push", "delete_repo"]),
    CapabilityRecord("unreal_engine", "Interact with real Unreal projects through project inspection, generated C++/Python automation scripts, builds, and an external editor bridge when available.", ["file.read", "file.write", "sandbox.run", "memory.add"], ["agent-04", "agent-05", "agent-14", "agent-15", "agent-16", "agent-17", "agent-27"], ["unreal_editor", "python", "c++"], ["read", "write", "execute", "memory_write"], "high", 0.62, {"project": "string", "objective": "string"}, {"project_changes": "array", "builds": "array"}, "real Unreal files/scripts/build logs or blocked bridge evidence", domains=["game development", "Unreal Engine"], dangerous_actions=["destructive_asset_delete", "shipping_build"]),
    CapabilityRecord("ai_generation", "Route text, image, video, audio, 3D, voice, and code generation through provider-neutral requests with provenance and license tracking.", ["generation.request", "memory.add"], ["agent-13", "agent-14", "agent-15", "agent-16", "agent-17", "agent-18", "agent-19", "agent-27"], ["text", "image", "video", "audio", "3d", "voice", "code"], ["external_read", "external_write", "memory_write"], "variable", 0.7, {"modality": "string", "prompt": "string"}, {"assets": "array", "license": "string"}, "asset record includes provider/model/request/result/license", domains=["image generation", "video generation", "audio generation", "3D generation", "document creation"]),
    CapabilityRecord("business_analysis", "Research competitors, markets, products, monetization, strategy, and business models.", ["web.search", "web.read", "memory.add"], ["agent-02", "agent-21", "agent-22", "agent-27"], ["internet", "memory"], ["read", "memory_write"], "low", 0.77, {"question": "string"}, {"analysis": "string", "sources": "array"}, "evidence-based conclusion with assumptions and risks", domains=["business analysis", "market research", "financial analysis", "strategic planning"]),
    CapabilityRecord("data_analysis", "Collect, clean, analyze, visualize, and verify structured data.", ["file.read", "file.write", "sandbox.run", "memory.add"], ["agent-20", "agent-24", "agent-27"], ["python", "sqlite", "charts"], ["read", "write", "execute", "memory_write"], "low", 0.82, {"dataset": "string", "question": "string"}, {"analysis": "object", "artifacts": "array"}, "reproducible script or query output", domains=["data analysis", "analytics"]),
    CapabilityRecord("system_administration", "Inspect and manage development environments, processes, dependencies, and local services under explicit permissions.", ["sandbox.run", "file.read", "memory.add"], ["agent-09", "agent-12", "agent-24", "agent-27"], ["terminal", "filesystem"], ["read", "execute", "memory_write"], "medium", 0.75, {"task": "string"}, {"commands": "array", "results": "array"}, "real command output and safety review", domains=["system administration", "external software"]),
    CapabilityRecord("trading", "Analyze and act on Solana token opportunities using Print World trading tools. This is one capability, never the core architecture.", ["print.get_asset", "print.get_token_list", "print.buy", "print.sell", "print.limit_order", "memory.add"], ["agent-02", "agent-20", "agent-21", "agent-27"], ["print_world"], ["read", "trade_execute", "orders_write", "memory_write"], "variable", 0.7, {"token": "string", "intent": "string"}, {"analysis": "object", "transaction": "string?"}, "real Print World data and confirmed transaction/order only when approved", domains=["trading", "financial analysis"], dangerous_actions=["market_buy", "market_sell", "transfer", "limit_order"]),
]


class CapabilityRegistry:
    def __init__(self, store: JsonStore, capabilities: list[CapabilityRecord] | None = None) -> None:
        self.store = store
        self._capabilities = {cap.name: cap for cap in (capabilities or DEFAULT_CAPABILITIES)}
        self.persist()

    def persist(self) -> None:
        self.store.write({"generated_at": now_iso(), "capabilities": [cap.to_dict() for cap in self._capabilities.values()]}, "capabilities", "registry.json")

    def list(self) -> list[CapabilityRecord]:
        return list(self._capabilities.values())

    def get(self, name: str) -> CapabilityRecord:
        return self._capabilities[name]

    def match(self, category: str, text: str = "") -> list[CapabilityRecord]:
        haystack = f"{category} {text}".lower()
        scored: list[tuple[int, CapabilityRecord]] = []
        for cap in self._capabilities.values():
            score = 0
            for domain in cap.domains + [cap.name, cap.description]:
                words = str(domain).lower().replace("_", " ").split()
                score += sum(1 for word in words if word and word in haystack)
            if score > 0:
                scored.append((score, cap))
        scored.sort(key=lambda item: (-item[0], item[1].name))
        return [cap for _, cap in scored] or [self._capabilities["question_answer"]]

    def export_status(self) -> dict[str, Any]:
        caps = [cap.to_dict() for cap in self.list()]
        return {
            "generated_at": now_iso(),
            "total": len(caps),
            "auto": sum(1 for c in caps if c["mode"] == "AUTO"),
            "approval_required": sum(1 for c in caps if c["mode"] == "APPROVAL_REQUIRED"),
            "disabled": sum(1 for c in caps if c["mode"] == "DISABLED"),
            "capabilities": caps,
        }
