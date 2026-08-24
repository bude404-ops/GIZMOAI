"""Database access layer for Historia Phase 1."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Iterable

from .schema import DDL, INDEXES, SCHEMA_VERSION


class HistoriaDatabase:
    """Small sqlite3 wrapper with idempotent migrations and typed helpers."""

    def __init__(self, db_path: str | Path = "historia.db") -> None:
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys = ON")

    def close(self) -> None:
        self.conn.close()

    def migrate(self) -> None:
        for statement in DDL:
            self.conn.execute(statement)
        for statement in INDEXES:
            self.conn.execute(statement)
        self.conn.execute(
            "INSERT OR IGNORE INTO schema_migrations(version) VALUES (?)",
            (SCHEMA_VERSION,),
        )
        self.conn.commit()

    def execute(self, sql: str, params: Iterable[Any] = ()) -> sqlite3.Cursor:
        cur = self.conn.execute(sql, tuple(params))
        self.conn.commit()
        return cur

    def query(self, sql: str, params: Iterable[Any] = ()) -> list[dict[str, Any]]:
        return [dict(row) for row in self.conn.execute(sql, tuple(params)).fetchall()]

    def one(self, sql: str, params: Iterable[Any] = ()) -> dict[str, Any] | None:
        row = self.conn.execute(sql, tuple(params)).fetchone()
        return dict(row) if row else None

    def upsert_historical_figure(self, record: dict[str, Any]) -> int:
        required = ["slug", "full_name", "historical_period", "region", "culture_civilization", "occupation_title"]
        missing = [k for k in required if not record.get(k)]
        if missing:
            raise ValueError(f"missing required historical figure fields: {missing}")
        cur = self.conn.execute(
            """
            INSERT INTO historical_figures (
              slug, full_name, birth_date, death_date, historical_period, region,
              culture_civilization, occupation_title, adult_status, research_status,
              appearance_certainty, summary, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(slug) DO UPDATE SET
              full_name=excluded.full_name,
              birth_date=excluded.birth_date,
              death_date=excluded.death_date,
              historical_period=excluded.historical_period,
              region=excluded.region,
              culture_civilization=excluded.culture_civilization,
              occupation_title=excluded.occupation_title,
              adult_status=excluded.adult_status,
              research_status=excluded.research_status,
              appearance_certainty=excluded.appearance_certainty,
              summary=excluded.summary,
              updated_at=CURRENT_TIMESTAMP
            """,
            (
                record["slug"], record["full_name"], record.get("birth_date"), record.get("death_date"),
                record["historical_period"], record["region"], record["culture_civilization"], record["occupation_title"],
                record.get("adult_status", "ADULT_CONFIRMED"), record.get("research_status", "DISCOVERED"),
                record.get("appearance_certainty", "UNKNOWN_ARTISTIC_RECONSTRUCTION"), record.get("summary", ""),
            ),
        )
        self.conn.commit()
        row = self.one("SELECT id FROM historical_figures WHERE slug=?", (record["slug"],))
        return int(row["id"])

    def add_source(self, figure_id: int, source: dict[str, Any]) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO historical_sources (figure_id, title, author, publisher, url, source_type, reliability_score, notes, accessed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                figure_id, source["title"], source.get("author"), source.get("publisher"), source.get("url"),
                source.get("source_type", "OTHER"), float(source.get("reliability_score", 0.5)), source.get("notes", ""),
                source.get("accessed_at"),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_fact(self, figure_id: int, fact: dict[str, Any], source_ids: list[int] | None = None) -> int:
        source_ids = source_ids or []
        if fact.get("classification") == "VERIFIED_FACT" and not source_ids:
            raise ValueError("VERIFIED_FACT requires at least one source")
        cur = self.conn.execute(
            """
            INSERT INTO historical_facts (figure_id, claim, classification, evidence_strength, source_count, notes)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                figure_id, fact["claim"], fact.get("classification", "HISTORICAL_INTERPRETATION"),
                fact.get("evidence_strength", "MODERATE"), len(source_ids), fact.get("notes", ""),
            ),
        )
        fact_id = int(cur.lastrowid)
        for sid in source_ids:
            self.conn.execute("INSERT OR IGNORE INTO fact_sources(fact_id, source_id) VALUES (?, ?)", (fact_id, sid))
        self.conn.commit()
        return fact_id

    def add_uncertainty(self, figure_id: int, item: dict[str, Any]) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO historical_uncertainties (figure_id, topic, description, confidence_level, handling_rule)
            VALUES (?, ?, ?, ?, ?)
            """,
            (figure_id, item["topic"], item["description"], item.get("confidence_level", "LOW"), item.get("handling_rule", "FLAG_FOR_REVIEW")),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_visual_reference(self, figure_id: int, item: dict[str, Any], source_id: int | None = None) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO visual_references (figure_id, reference_type, description, source_id, confidence_level, usage_rule)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (figure_id, item["reference_type"], item["description"], source_id, item.get("confidence_level", "LOW"), item.get("usage_rule", "LABEL_AS_ARTISTIC_RECONSTRUCTION")),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_scene(self, figure_id: int, scene: dict[str, Any]) -> int:
        cur = self.conn.execute(
            """
            INSERT INTO scene_concepts (figure_id, name, historical_environment, story_purpose, visual_appeal_notes, camera_direction, accuracy_notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (figure_id, scene["name"], scene["historical_environment"], scene["story_purpose"], scene["visual_appeal_notes"], scene["camera_direction"], scene.get("accuracy_notes", "")),
        )
        self.conn.commit()
        return int(cur.lastrowid)

    def add_character_bible(self, figure_id: int, bible: dict[str, Any]) -> int:
        cur = self.conn.execute(
            """
            INSERT OR REPLACE INTO character_bibles (
              figure_id, name, classification, era, age_status, personality, appearance,
              hair, eyes, facial_characteristics, body_build, fashion, jewelry, makeup,
              voice, accent, confidence_level, humor, speaking_style, interests,
              historical_knowledge, approved_outfits, approved_environments, content_history
            ) VALUES (?, ?, 'HISTORICAL', ?, 'ADULT', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                figure_id, bible["name"], bible["era"], bible.get("personality", ""), bible.get("appearance", ""),
                bible.get("hair", ""), bible.get("eyes", ""), bible.get("facial_characteristics", ""), bible.get("body_build", ""),
                bible.get("fashion", ""), bible.get("jewelry", ""), bible.get("makeup", ""), bible.get("voice", ""), bible.get("accent", ""),
                int(bible.get("confidence_level", 7)), bible.get("humor", ""), bible.get("speaking_style", ""), bible.get("interests", ""),
                bible.get("historical_knowledge", ""), json.dumps(bible.get("approved_outfits", [])), json.dumps(bible.get("approved_environments", [])), json.dumps([]),
            ),
        )
        self.conn.commit()
        return int(cur.lastrowid)
