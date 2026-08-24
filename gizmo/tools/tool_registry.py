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
]


class ToolRegistry:
    def __init__(self, tools: list[ToolDefinition] | None = None) -> None:
        self.tools = {tool.name: tool for tool in (tools or DEFAULT_TOOLS)}

    def allowed_for(self, agent_id: str) -> list[ToolDefinition]:
        return [tool for tool in self.tools.values() if "*" in tool.allowed_agents or agent_id in tool.allowed_agents]

    def get(self, name: str) -> ToolDefinition:
        return self.tools[name]
