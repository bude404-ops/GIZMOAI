from pathlib import Path
import zipfile

from gizmo.brain.cloud_vault import CloudMemoryVault
from gizmo.control.telegram_control import TelegramControlLayer
from gizmo.orchestrator.orchestrator import GizmoOrchestrator
from gizmo.telegram.config import TelegramConfig
from gizmo.telegram.router import TelegramCommandRouter
from gizmo.telegram.security import TelegramAuthorizer


def _seed_memory(orchestrator: GizmoOrchestrator) -> None:
    orchestrator.brain_core.record_fact(
        "Cloud vault seed",
        "GIZMO should preserve Markdown memory notes, graph files, manifests, and restore archives across cloud runs.",
        source="test",
        source_agent="agent-26",
        project="Gizmo",
        importance=8,
        confidence=0.9,
        tags=["cloud-vault", "obsidian", "memory"],
    )


def test_cloud_memory_vault_creates_obsidian_archive_and_manifest(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    _seed_memory(orchestrator)

    report = CloudMemoryVault(orchestrator.brain_core, orchestrator.store).sync()

    assert report.restore_ready is True
    assert report.markdown_notes >= 1
    assert report.graph_files >= 1
    assert report.archive_bytes > 0
    assert len(report.archive_sha256) == 64
    assert (tmp_path / "cloud_vault" / "latest_sync.json").exists()
    assert (tmp_path / "cloud_vault" / "latest_manifest.json").exists()
    archive = tmp_path / "cloud_vault" / "archives" / report.archive_name
    assert archive.exists()
    with zipfile.ZipFile(archive) as zf:
        names = set(zf.namelist())
    assert "manifest.json" in names
    assert "vault/README.md" in names
    assert any(name.startswith("vault/graph/") for name in names)
    assert any(name.endswith("Memory Index.md") for name in names)


def test_telegram_can_sync_cloud_memory_vault(tmp_path: Path):
    orchestrator = GizmoOrchestrator(tmp_path)
    orchestrator.bootstrap()
    _seed_memory(orchestrator)
    config = TelegramConfig(bot_token="", admin_ids={"101"}, github_repository="owner/repo", reaper_auth_secret_available=True)
    control = TelegramControlLayer(orchestrator, config=config)
    router = TelegramCommandRouter(orchestrator.store, TelegramAuthorizer(config.admin_ids), control)

    result = router.route_text("101", "201", "obsidian vault")

    assert result.ok is True
    assert result.intent["intent"] == "cloud_vault"
    assert "CLOUD MEMORY VAULT SYNCED" in result.message
    assert (tmp_path / "cloud_vault" / "latest_sync.json").exists()
