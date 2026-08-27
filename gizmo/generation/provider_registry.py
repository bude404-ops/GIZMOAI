"""Provider-neutral AI generation registry for text, image, video, audio, 3D, voice, and code."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


@dataclass
class GenerationProvider:
    name: str
    modalities: list[str]
    models: list[str]
    permission_mode: str
    cost_model: str = "unknown"
    license_notes: str = "record per generation"
    reliability: float = 0.5

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class GenerationRequestRecord:
    modality: str
    prompt: str
    provider: str | None
    model: str | None
    project: str
    status: str
    result_artifacts: list[str] = field(default_factory=list)
    cost_estimate: str = "unknown"
    quality_score: float = 0.0
    license_notes: str = "unknown"
    created_at: str = field(default_factory=now_iso)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


DEFAULT_PROVIDERS = [
    GenerationProvider("text", ["TEXT", "CODE"], ["provider-selected"], "AUTO", reliability=0.8),
    GenerationProvider("image", ["IMAGE"], ["provider-selected"], "APPROVAL_REQUIRED", reliability=0.65),
    GenerationProvider("video", ["VIDEO"], ["provider-selected"], "APPROVAL_REQUIRED", cost_model="high-variable", reliability=0.55),
    GenerationProvider("audio", ["AUDIO", "VOICE"], ["provider-selected"], "APPROVAL_REQUIRED", reliability=0.6),
    GenerationProvider("3d", ["3D"], ["provider-selected"], "APPROVAL_REQUIRED", cost_model="high-variable", reliability=0.5),
]


class GenerationProviderRegistry:
    def __init__(self, store: JsonStore, providers: list[GenerationProvider] | None = None) -> None:
        self.store = store
        self.providers = providers or DEFAULT_PROVIDERS
        self.persist()

    def persist(self) -> None:
        self.store.write({"generated_at": now_iso(), "providers": [p.to_dict() for p in self.providers]}, "generation", "providers.json")

    def select(self, modality: str) -> GenerationProvider | None:
        target = modality.upper()
        return next((provider for provider in self.providers if target in provider.modalities), None)

    def record_request(self, modality: str, prompt: str, *, project: str = "Gizmo", provider: str | None = None, model: str | None = None, status: str = "PLANNED") -> GenerationRequestRecord:
        selected = self.select(modality) if provider is None else None
        record = GenerationRequestRecord(modality.upper(), prompt, provider or (selected.name if selected else None), model or (selected.models[0] if selected else None), project, status)
        self.store.write(record.to_dict(), "generation", "requests", f"generation-{now_iso().replace(':','').replace('.','').replace('-','')}.json")
        self.store.write(record.to_dict(), "generation", "latest_request.json")
        return record

    def export_status(self) -> dict[str, Any]:
        return {"generated_at": now_iso(), "providers": [p.to_dict() for p in self.providers]}
