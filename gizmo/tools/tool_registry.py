"""Central least-privilege tool registry."""
from __future__ import annotations

from gizmo.core.models import ToolDefinition


DEFAULT_TOOLS = [
    ToolDefinition("file.read", "Read project files", ["read"], {"path": "string"}, {"content": "string"}, ["*"], "LOW"),
    ToolDefinition("file.write", "Write sandbox/project files", ["write"], {"path": "string", "content": "string"}, {"path": "string"}, ["agent-01", "agent-06", "agent-07", "agent-09", "agent-10", "agent-11", "agent-23"], "MEDIUM"),
    ToolDefinition("code.test", "Run approved test commands", ["execute", "test"], {"command": "string"}, {"exit_code": "integer"}, ["agent-09", "agent-11", "agent-24", "agent-27"], "MEDIUM"),
    ToolDefinition("git.branch", "Create isolated branches", ["git"], {"name": "string"}, {"branch": "string"}, ["agent-10"], "MEDIUM"),
    ToolDefinition("github.pr", "Create pull requests", ["external_write"], {"branch": "string"}, {"pr": "string"}, ["agent-10"], "HIGH"),
    ToolDefinition("memory.search", "Search persistent memory", ["read"], {"query": "string"}, {"matches": "array"}, ["*"], "LOW"),
    ToolDefinition("memory.add", "Write non-secret memory", ["memory_write"], {"content": "string"}, {"id": "string"}, ["*"], "LOW"),
    ToolDefinition("sandbox.run", "Run code in sandbox", ["execute"], {"command": "string"}, {"result": "string"}, ["agent-09", "agent-11", "agent-13"], "MEDIUM"),
    ToolDefinition("web.search", "Search public internet sources", ["external_read", "research"], {"query": "string"}, {"results": "array"}, ["agent-02", "agent-20", "agent-21", "agent-22", "agent-23", "agent-27"], "LOW"),
    ToolDefinition("web.read", "Read public source documents", ["external_read", "research"], {"url": "string"}, {"content": "string", "provenance": "object"}, ["agent-02", "agent-20", "agent-21", "agent-22", "agent-23", "agent-27"], "LOW"),
    ToolDefinition("generation.request", "Create provider-neutral generation requests", ["external_write", "generation"], {"modality": "string", "prompt": "string"}, {"asset_manifest": "object"}, ["agent-13", "agent-14", "agent-15", "agent-16", "agent-17", "agent-18", "agent-19", "agent-27"], "HIGH"),
    ToolDefinition("unreal.bridge", "Operate a controlled Unreal automation bridge when available", ["execute", "unreal"], {"project": "string", "script": "string"}, {"logs": "array", "artifacts": "array"}, ["agent-05", "agent-14", "agent-16", "agent-17", "agent-27"], "HIGH"),
    ToolDefinition("print.get_asset", "Read Solana token data through Print World", ["external_read", "trading"], {"mint": "string"}, {"asset": "object"}, ["agent-02", "agent-20", "agent-21", "agent-27"], "LOW"),
    ToolDefinition("print.trade", "Execute approval-gated Solana trades through Print World", ["trade_execute"], {"mint": "string", "side": "string", "amount": "number"}, {"transaction": "string"}, ["agent-21", "agent-27"], "CRITICAL"),
]


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self.tools = {tool.name: tool for tool in (tools or DEFAULT_TOOLS)}

    def allowed_for(self, agent_id: str) -> list[ToolDefinition]:
        return [tool for tool in self.tools.values() if "*" in tool.allowed_agents or agent_id in tool.allowed_agents]

    def get(self, name: str) -> ToolDefinition:
        return self.tools[name]
