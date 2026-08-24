from pathlib import Path

import pytest

from historia.database import HistoriaDatabase
from historia.research_engine import ResearchEngine
from historia.seed_data import SEED_RECORDS
from historia.visual_identity import VisualIdentityEngine


def build_db(tmp_path: Path):
    db = HistoriaDatabase(tmp_path / "historia.db")
    db.migrate()
    research = ResearchEngine(db)
    for record in SEED_RECORDS:
        research.ingest_research_record(record)
    return db, VisualIdentityEngine(db)


def test_visual_identity_engine_builds_profiles_for_seed_characters(tmp_path):
    db, engine = build_db(tmp_path)
    plans = engine.build_for_all_character_bibles()
    assert len(plans) == 4
    assert all(plan.wardrobe_count >= 2 for plan in plans)
    assert all(plan.environment_count >= 2 for plan in plans)
    assert all(plan.prompt_template_count == 2 for plan in plans)
    assert all(plan.audit_count == 4 for plan in plans)

    profiles = db.query("SELECT * FROM visual_identity_profiles")
    assert len(profiles) == 4
    assert all("AI historical reconstruction" in row["reconstruction_disclosure"] for row in profiles)
    assert all(row["consistency_score"] >= 70 for row in profiles)
    db.close()


def test_prompt_templates_are_provider_neutral_and_safe(tmp_path):
    db, engine = build_db(tmp_path)
    engine.build_for_all_character_bibles()
    prompts = db.query("SELECT provider_family, aspect_ratio, prompt_text, negative_prompt, disclosure_text FROM visual_prompt_templates")
    assert prompts
    assert {row["provider_family"] for row in prompts} == {"GENERIC_IMAGE"}
    assert {row["aspect_ratio"] for row in prompts} == {"9:16"}
    assert all("Photorealistic cinematic" in row["prompt_text"] or "Scroll-stopping" in row["prompt_text"] for row in prompts)
    assert all("no minors" in row["negative_prompt"] for row in prompts)
    assert all("no nudity" in row["negative_prompt"] for row in prompts)
    assert all(row["disclosure_text"] == "AI historical reconstruction" for row in prompts)
    db.close()


def test_visual_identity_rejects_non_adult_or_explicit_bible(tmp_path):
    db = HistoriaDatabase(tmp_path / "historia.db")
    db.migrate()
    figure_id = db.upsert_historical_figure({
        "slug": "unsafe-test",
        "full_name": "Unsafe Test",
        "historical_period": "Test Era",
        "region": "Test Region",
        "culture_civilization": "Test Culture",
        "occupation_title": "Test Title",
    })
    bible_id = db.add_character_bible(figure_id, {
        "name": "Unsafe Test",
        "era": "Test Era",
        "appearance": "adult portrait",
        "fashion": "explicit styling",
    })
    with pytest.raises(ValueError):
        VisualIdentityEngine(db).build_for_character(bible_id)
    db.close()


def test_phase2_tables_are_additive_to_phase1_schema(tmp_path):
    db, _ = build_db(tmp_path)
    tables = {row["name"] for row in db.query("SELECT name FROM sqlite_master WHERE type='table'")}
    assert "historical_figures" in tables
    assert "content_ideas" in tables
    assert "visual_identity_profiles" in tables
    assert "wardrobe_options" in tables
    assert "environment_options" in tables
    assert "visual_prompt_templates" in tables
    assert "visual_identity_audits" in tables
    migration = db.one("SELECT MAX(version) AS version FROM schema_migrations")
    assert migration["version"] == 2
    db.close()
