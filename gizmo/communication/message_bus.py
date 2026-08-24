"""Structured internal message bus."""
from __future__ import annotations

from gizmo.core.models import StructuredMessage
from gizmo.core.store import JsonStore


class MessageBus:
    def __init__(self, store: JsonStore) -> None:
        self.store = store

    def send(self, message: StructuredMessage) -> StructuredMessage:
        self.store.append_list(message.to_dict(), "communication", "messages.json")
        return message

    def inbox(self, recipient: str) -> list[dict]:
        return [m for m in self.store.read("communication", "messages.json", default=[]) if m["recipient"] == recipient]
