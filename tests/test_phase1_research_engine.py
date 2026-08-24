from pathlib import Path
import sqlite3

import pytest

from historia.database import HistoriaDatabase
from historia.research_engine import ResearchEngine
from historia.seed_data import SEED_RECORDS


def build_db(tmp_path: Path):
    db = HistoriaDatabase(tmp_path / "historia.db")
    db.migrate()
    engine = ResearchEngine(db)
    for record in SEED_RECORDS:
        engine.ingest_research_record(record)
    return db, engine


def test_seed_records_are_source_backed_and_ready(tmp_path):
    db, _ = build_db(tmp_path)
    figures = db.query("SELECT slug, research_status FROM historical_figures ORDER BY slug")
    assert len(figures) == 4
    assert {row["research_status"] for row in figures} == {"READY_FOR_IDEAS"}

    source_counts = db.query(
        "SELECT figure_id, COUNT(*) AS n FROM historical_sources GROUP BY figure_id"
    )
    assert all(row["n"] >= 2 for row in source_counts)

    verified = db.query("SELECT source_count FROM historical_facts WHERE classification='VERIFIED_FACT'")
    assert verified
    assert all(row["source_count"] >= 1 for row in verified)
    db.close()


def test_idea_generation_creates_ranked_text_only_candidates(tmp_path):
    db, engine = build_db(tmp_path)
    idea_ids = engine.generate_ideas_for_ready_figures(limit_per_figure=2)
    assert len(idea_ids) >= 4
    ideas = db.query("SELECT hook, overall_prediction, ai_generated_disclosure, status FROM content_ideas")
    assert all(row["status"] == "RANKED" for row in ideas)
    assert all(row["overall_prediction"] > 0 for row in ideas)
    assert all("AI historical" in row["ai_generated_disclosure"] for row in ideas)
    checks = db.query("SELECT COUNT(*) AS n FROM historical_accuracy_checks")
    assert checks[0]["n"] == len(ideas)
    db.close()


def test_verified_fact_without_source_is_rejected(tmp_path):
    db = HistoriaDatabase(tmp_path / "historia.db")
    db.migrate()
    figure_id = db.upsert_historical_figure({
        "slug": "test-adult",
        "full_name": "Test Adult",
        "historical_period": "Test Era",
        "region": "Test Region",
        "culture_civilization": "Test Culture",
        "occupation_title": "Test Title",
    })
    with pytest.raises(ValueError):
        db.add_fact(figure_id, {"claim": "A verified claim", "classification": "VERIFIED_FACT", "evidence_strength": "STRONG"}, [])
    db.close()


def test_adult_and_quote_safety_guards(tmp_path):
    db = HistoriaDatabase(tmp_path / "historia.db")
    db.migrate()
    engine = ResearchEngine(db)
    minor_record = dict(SEED_RECORDS[0])
    minor_record["figure"] = dict(SEED_RECORDS[0]["figure"], slug="blocked", adult_status="REJECTED_MINOR_OR_UNCLEAR")
    with pytest.raises(ValueError):
        engine.ingest_research_record(minor_record)

    quote_record = dict(SEED_RECORDS[0])
    quote_record["figure"] = dict(SEED_RECORDS[0]["figure"], slug="quote-test")
    quote_record["facts"] = [{"claim": "A quote says she ruled forever", "classification": "AI_DRAMATIZATION", "evidence_strength": "WEAK"}]
    with pytest.raises(ValueError):
        engine.ingest_research_record(quote_record)
    db.close()


def test_foreign_keys_and_indexes_exist(tmp_path):
    db, _ = build_db(tmp_path)
    fk_state = db.one("PRAGMA foreign_keys")
    assert fk_state["foreign_keys"] == 1
    indexes = {row["name"] for row in db.query("SELECT name FROM sqlite_master WHERE type='index'")}
    assert "idx_figures_period" in indexes
    assert "idx_ideas_score" in indexes
    db.close()
