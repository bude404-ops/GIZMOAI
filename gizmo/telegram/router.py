"""Secure Telegram command router into the Gizmo control layer."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore
from gizmo.telegram.intents import IntentDetector, TelegramIntent
from gizmo.telegram.security import AuthorizationResult, TelegramAuthorizer, DENIAL_MESSAGE, sanitize_for_telegram

TASK_STATUSES = ["QUEUED", "PLANNING", "ASSIGNED", "RUNNING", "TESTING", "REVIEW", "COMPLETED", "FAILED", "DIAGNOSING", "RETRY", "HUMAN_REVIEW"]


@dataclass
class TelegramTaskEnvelope:
    task_id: str
    source: str
    user_id: str
    chat_id: str
    command: str
    objective: str
    priority: str
    status: str
    created_at: str
    assigned_agent: str | None = None
    requires_approval: bool = False
    intent: str = "natural_task"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TelegramRouteResult:
    ok: bool
    message: str
    task: dict[str, Any] | None = None
    intent: dict[str, Any] | None = None
    authorization: dict[str, Any] | None = None
    actions: list[dict[str, Any]] = field(default_factory=list)
    inline_buttons: list[list[dict[str, str]]] = field(default_factory=list)
    priority: str = "NORMAL"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class TelegramCommandRouter:
    def __init__(self, store: JsonStore, authorizer: TelegramAuthorizer, control_layer: Any) -> None:
        self.store = store
        self.authorizer = authorizer
        self.control = control_layer
        self.detector = IntentDetector()

    def route_update(self, update: dict[str, Any]) -> TelegramRouteResult:
        message = update.get("message") or update.get("callback_query", {}).get("message") or {}
        callback = update.get("callback_query")
        user = (callback or message).get("from", {})
        chat = message.get("chat", {})
        text = callback.get("data", "") if callback else message.get("text", "")
        return self.route_text(user.get("id"), chat.get("id", user.get("id")), text, raw_update=update)

    def route_text(self, user_id: int | str | None, chat_id: int | str | None, text: str, *, raw_update: dict[str, Any] | None = None) -> TelegramRouteResult:
        intent = self.detector.detect(text)
        auth = self.authorizer.authorize(user_id, intent.command if intent.command != "natural" else text, intent.intent)
        self._audit_request(auth, intent, chat_id, text)
        if not auth.allowed:
            return TelegramRouteResult(False, DENIAL_MESSAGE, intent=intent.to_dict(), authorization=auth.to_dict(), priority="SECURITY")
        envelope = self._create_task_envelope(auth, chat_id, intent, text, raw_update or {})
        result = self.control.handle_telegram_task(envelope, intent)
        return TelegramRouteResult(
            ok=result.get("ok", True),
            message=sanitize_for_telegram(result.get("message", "Command accepted.")),
            task=envelope.to_dict(),
            intent=intent.to_dict(),
            authorization=auth.to_dict(),
            actions=result.get("actions", []),
            inline_buttons=result.get("inline_buttons", []),
            priority=result.get("priority", "NORMAL"),
        )

    def _create_task_envelope(self, auth: AuthorizationResult, chat_id: int | str | None, intent: TelegramIntent, text: str, raw_update: dict[str, Any]) -> TelegramTaskEnvelope:
        envelope = TelegramTaskEnvelope(
            task_id=f"telegram-task-{uuid4().hex[:12]}",
            source="telegram",
            user_id=auth.user_id,
            chat_id="" if chat_id is None else str(chat_id),
            command=intent.command,
            objective=intent.objective or text,
            priority=intent.priority,
            status="QUEUED",
            created_at=now_iso(),
            requires_approval=intent.requires_approval or auth.sensitive,
            intent=intent.intent,
            metadata={"confidence": intent.confidence, "args": intent.args, "raw_text": text[:1000]},
        )
        self.store.write(envelope.to_dict(), "telegram", "tasks", f"{envelope.task_id}.json")
        return envelope

    def _audit_request(self, auth: AuthorizationResult, intent: TelegramIntent, chat_id: int | str | None, text: str) -> None:
        self.store.append_list({
            "timestamp": now_iso(),
            "user_id": auth.user_id,
            "chat_id": "" if chat_id is None else str(chat_id),
            "authorized": auth.allowed,
            "intent": intent.intent,
            "command": intent.command,
            "sensitive": auth.sensitive,
            "text_preview": text[:160],
        }, "telegram", "request_log.json")
