"""Cloud-synced Obsidian-style vault exports for GIZMO memory.

The second brain already writes Markdown notes. This layer makes those notes
self-managed in cloud runs: it rebuilds the vault, writes a manifest, creates a
portable archive, tracks revisions, and records restore metadata. It is storage-
provider neutral; GitHub Actions cache/artifacts, object storage, or any durable
volume can preserve the generated cloud_vault directory.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any
import zipfile

from gizmo.brain.memory_api import SecondBrain
from gizmo.core.models import now_iso
from gizmo.core.store import JsonStore


@dataclass
class VaultFileRecord:
    relative_path: str
    bytes: int
    sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CloudVaultSyncReport:
    generated_at: str
    files: list[dict[str, Any]]
    markdown_notes: int
    graph_files: int
    archive_name: str
    archive_sha256: str
    archive_bytes: int
    manifest_name: str
    restore_ready: bool
    vault_report: dict[str, Any] = field(default_factory=dict)
    retained_archives: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class CloudMemoryVault:
    """Export the local second-brain vault into durable cloud-ready artifacts."""

    def __init__(self, brain: SecondBrain, store: JsonStore, *, keep_archives: int = 5) -> None:
        self.brain = brain
        self.store = store
        self.keep_archives = max(1, keep_archives)
        self.root = self.store.path("cloud_vault")
        self.export_root = self.root / "current"
        self.archive_root = self.root / "archives"
        self.manifest_root = self.root / "manifests"
        self.restore_root = self.root / "restore"

    def sync(self) -> CloudVaultSyncReport:
        self.root.mkdir(parents=True, exist_ok=True)
        self.archive_root.mkdir(parents=True, exist_ok=True)
        self.manifest_root.mkdir(parents=True, exist_ok=True)
        self.restore_root.mkdir(parents=True, exist_ok=True)

        vault_report = self.brain.rebuild_vault_indexes()
        if self.export_root.exists():
            shutil.rmtree(self.export_root)
        shutil.copytree(self.brain.vault.root, self.export_root)

        files = self._scan_files(self.export_root)
        stamp = now_iso().replace(":", "-").replace(".", "-")
        manifest_name = f"vault-manifest-{stamp}.json"
        archive_name = f"gizmo-obsidian-vault-{stamp}.zip"
        manifest_path = self.manifest_root / manifest_name
        archive_path = self.archive_root / archive_name

        manifest = {
            "generated_at": now_iso(),
            "kind": "gizmo-obsidian-cloud-vault",
            "restore_ready": True,
            "root_note": "README.md",
            "files": [record.to_dict() for record in files],
            "vault_report": vault_report,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        self._write_archive(archive_path, self.export_root, manifest_path)
        archive_sha = self._sha256(archive_path)
        archive_bytes = archive_path.stat().st_size

        latest_manifest = self.root / "latest_manifest.json"
        latest_archive = self.root / "latest_archive.json"
        latest_manifest.write_text(json.dumps(manifest, indent=2, sort_keys=True))
        latest_archive.write_text(json.dumps({
            "archive_name": archive_name,
            "archive_sha256": archive_sha,
            "archive_bytes": archive_bytes,
            "generated_at": now_iso(),
            "restore_hint": "Use the archive plus manifest to restore the Obsidian-compatible vault.",
        }, indent=2, sort_keys=True))
        (self.restore_root / "RESTORE.md").write_text(self._restore_note(archive_name, archive_sha, vault_report))

        retained = self._prune_archives()
        report = CloudVaultSyncReport(
            generated_at=manifest["generated_at"],
            files=[record.to_dict() for record in files],
            markdown_notes=sum(1 for record in files if record.relative_path.endswith(".md")),
            graph_files=sum(1 for record in files if record.relative_path.startswith("graph/")),
            archive_name=archive_name,
            archive_sha256=archive_sha,
            archive_bytes=archive_bytes,
            manifest_name=manifest_name,
            restore_ready=True,
            vault_report=vault_report,
            retained_archives=retained,
        )
        self.store.write(report.to_dict(), "cloud_vault", "latest_sync.json")
        self.store.append_list(report.to_dict(), "cloud_vault", "sync_history.json")
        return report

    def latest(self) -> dict[str, Any]:
        return self.store.read("cloud_vault", "latest_sync.json", default={})

    def _scan_files(self, root: Path) -> list[VaultFileRecord]:
        records: list[VaultFileRecord] = []
        for path in sorted(root.rglob("*")):
            if path.is_file():
                records.append(VaultFileRecord(
                    relative_path=str(path.relative_to(root)),
                    bytes=path.stat().st_size,
                    sha256=self._sha256(path),
                ))
        return records

    def _write_archive(self, archive_path: Path, vault_root: Path, manifest_path: Path) -> None:
        with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(vault_root.rglob("*")):
                if path.is_file():
                    zf.write(path, arcname=f"vault/{path.relative_to(vault_root)}")
            zf.write(manifest_path, arcname="manifest.json")

    def _prune_archives(self) -> int:
        archives = sorted(self.archive_root.glob("gizmo-obsidian-vault-*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in archives[self.keep_archives:]:
            old.unlink(missing_ok=True)
        manifests = sorted(self.manifest_root.glob("vault-manifest-*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for old in manifests[self.keep_archives:]:
            old.unlink(missing_ok=True)
        return len(list(self.archive_root.glob("gizmo-obsidian-vault-*.zip")))

    @staticmethod
    def _sha256(path: Path) -> str:
        h = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                h.update(chunk)
        return h.hexdigest()

    @staticmethod
    def _restore_note(archive_name: str, archive_sha: str, vault_report: dict[str, Any]) -> str:
        return "\n".join([
            "# GIZMO Cloud Vault Restore",
            "",
            "This bundle is an Obsidian-compatible memory vault export.",
            "",
            f"- Archive: `{archive_name}`",
            f"- SHA-256: `{archive_sha}`",
            f"- Memories: **{vault_report.get('memories', 0)}**",
            f"- Active: **{vault_report.get('active', 0)}**",
            f"- Graph nodes: **{vault_report.get('graph_nodes', 0)}**",
            f"- Graph edges: **{vault_report.get('graph_edges', 0)}**",
            "",
            "Open the extracted `vault` folder in Obsidian-compatible tools.",
        ])
