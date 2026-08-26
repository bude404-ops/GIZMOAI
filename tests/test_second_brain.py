from pathlib import Path

from gizmo.core.store import JsonStore
from gizmo.memory.memory_system import MemorySystem
from gizmo.second_brain.command_router import SecondBrainCommandRouter
from gizmo.second_brain.context_indexer import RepoContextIndexer
from gizmo.tasks.task_engine import TaskEngine


def build_router(tmp_path: Path, repo_path: Path):
    store = JsonStore(tmp_path)
    memory = MemorySystem(store)
    tasks = TaskEngine(store)
    indexer = RepoContextIndexer(repo_path)
    return SecondBrainCommandRouter(memory, tasks, indexer), memory


def test_context_indexer_finds_core_files():
    indexer = RepoContextIndexer(Path.cwd())
    index = indexer.build_index()
    paths = {item["path"] for item in index["files"]}
    assert "README.md" in paths
    assert "gizmo/orchestrator/orchestrator.py" in paths
    assert index["file_count"] >= 10


def test_context_pack_focuses_by_query():
    indexer = RepoContextIndexer(Path.cwd())
    pack = indexer.context_pack("approval policy github", limit=8)
    joined = "\n".join(item["path"] for item in pack["files"])
    assert "approval" in joined or "github" in joined
    assert pack["selected_count"] > 0


def test_router_ignores_non_gizmo_comments(tmp_path: Path):
    router, _ = build_router(tmp_path, Path.cwd())
    result = router.route("hello")
    assert result.status == "IGNORED"


def test_router_status_context_remember_recall_and_plan(tmp_path: Path):
    router, memory = build_router(tmp_path, Path.cwd())
    status = router.route("/gizmo status")
    context = router.route("/gizmo context github policy")
    remembered = router.route("/gizmo remember Policy gates protect GitHub execution", actor="owner")
    recalled = router.route("/gizmo recall GitHub execution")
    plan = router.route("/gizmo plan Answer issue comments from repo memory")
    assert status.status == "OK"
    assert context.artifacts["context_pack"]["selected_count"] > 0
    assert remembered.status == "OK"
    assert recalled.status == "OK"
    assert plan.status == "OK"
    assert len(plan.artifacts["tasks"]) == 3
    assert memory.search("Policy gates", limit=1)


def test_router_unknown_command_returns_guidance(tmp_path: Path):
    router, _ = build_router(tmp_path, Path.cwd())
    result = router.route("/gizmo dance")
    assert result.status == "UNKNOWN"
    assert "/gizmo help" in result.response_markdown
