"""Core data models for GIZMO bootstrap v0."""
from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from uuid import uuid4


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class TaskStatus(str, Enum):
    QUEUED = "QUEUED"
    PAUSED = "PAUSED"
    PLANNING = "PLANNING"
    RUNNING = "RUNNING"
    WAITING = "WAITING"
    BLOCKED = "BLOCKED"
    TESTING = "TESTING"
    REVIEW = "REVIEW"
    FAILED = "FAILED"
    RETRYING = "RETRYING"
    COMPLETED = "COMPLETED"
    ESCALATED = "ESCALATED"
    CANCELLED = "CANCELLED"


class OperatingMode(str, Enum):
    MANUAL = "MANUAL"
    ASSISTED = "ASSISTED"
    AUTONOMOUS = "AUTONOMOUS"
    EMERGENCY = "EMERGENCY"


class MemoryKind(str, Enum):
    SHORT_TERM = "SHORT_TERM"
    EPISODIC = "EPISODIC"
    PROCEDURAL = "PROCEDURAL"
    SEMANTIC = "SEMANTIC"
    AGENT = "AGENT"
    ORGANIZATIONAL = "ORGANIZATIONAL"
    PROJECT = "PROJECT"


@dataclass
class AgentDefinition:
    id: str
    name: str
    role: str
    objectives: list[str]
    allowed_tools: list[str]
    memory_namespace: str
    task_types: list[str]
    evaluation_criteria: list[str]
    trusted: bool = True
    sandbox_required: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Task:
    project: str
    objective: str
    assigned_agent: str
    priority: int = 5
    dependencies: list[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.QUEUED
    id: str = field(default_factory=lambda: f"task-{uuid4().hex[:12]}")
    created_at: str = field(default_factory=now_iso)
    execution_history: list[dict[str, Any]] = field(default_factory=list)
    artifacts: list[str] = field(default_factory=list)
    tests: list[str] = field(default_factory=list)
    result: str = ""
    lessons_learned: list[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries: int = 2

    def record(self, action: str, result: str, **extra: Any) -> None:
        self.execution_history.append({"timestamp": now_iso(), "action": action, "result": result, **extra})

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["status"] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Task":
        data = dict(data)
        data["status"] = TaskStatus(data["status"])
        return cls(**data)


@dataclass
class StructuredMessage:
    sender: str
    recipient: str
    message_type: str
    payload: dict[str, Any]
    correlation_id: str | None = None
    id: str = field(default_factory=lambda: f"msg-{uuid4().hex[:12]}")
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ToolDefinition:
    name: str
    description: str
    permissions: list[str]
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    allowed_agents: list[str]
    security_level: str
    logging_required: bool = True

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
