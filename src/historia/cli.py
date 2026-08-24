"""Command-line entry points for Phase 1."""
from __future__ import annotations

import argparse
from pathlib import Path

from .database import HistoriaDatabase
from .research_engine import ResearchEngine
from .seed_data import SEED_RECORDS
from .visual_identity import VisualIdentityEngine


def build_seed(db_path: str) -> None:
    db = HistoriaDatabase(db_path)
    db.migrate()
    engine = ResearchEngine(db)
    for record in SEED_RECORDS:
        engine.ingest_research_record(record)
    idea_ids = engine.generate_ideas_for_ready_figures(limit_per_figure=2)
    visual_plans = VisualIdentityEngine(db).build_for_all_character_bibles()
    print(f"seeded_figures={len(SEED_RECORDS)} generated_ideas={len(idea_ids)} visual_identities={len(visual_plans)} db={db_path}")
    db.close()


def build_visual_identities(db_path: str) -> None:
    db = HistoriaDatabase(db_path)
    db.migrate()
    plans = VisualIdentityEngine(db).build_for_all_character_bibles()
    print(f"visual_identities={len(plans)} db={db_path}")
    db.close()


def summary(db_path: str) -> None:
    db = HistoriaDatabase(db_path)
    db.migrate()
    rows = db.query(
        """
        SELECT f.full_name, f.research_status, COUNT(DISTINCT s.id) AS sources,
               COUNT(DISTINCT hf.id) AS facts, COUNT(DISTINCT ci.id) AS ideas,
               COUNT(DISTINCT vip.id) AS visual_identities,
               COUNT(DISTINCT wo.id) AS wardrobe_options,
               COUNT(DISTINCT eo.id) AS environments
        FROM historical_figures f
        LEFT JOIN historical_sources s ON s.figure_id=f.id
        LEFT JOIN historical_facts hf ON hf.figure_id=f.id
        LEFT JOIN content_ideas ci ON ci.figure_id=f.id
        LEFT JOIN character_bibles cb ON cb.figure_id=f.id
        LEFT JOIN visual_identity_profiles vip ON vip.character_bible_id=cb.id
        LEFT JOIN wardrobe_options wo ON wo.character_bible_id=cb.id
        LEFT JOIN environment_options eo ON eo.character_bible_id=cb.id
        GROUP BY f.id
        ORDER BY f.full_name
        """
    )
    for row in rows:
        print(
            f"{row['full_name']} | {row['research_status']} | sources={row['sources']} "
            f"facts={row['facts']} ideas={row['ideas']} visual_identities={row['visual_identities']} "
            f"wardrobe={row['wardrobe_options']} environments={row['environments']}"
        )
    db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Historia research/database CLI")
    parser.add_argument("command", choices=["build-seed", "build-visual-identities", "summary"])
    parser.add_argument("--db", default=str(Path("data") / "historia.db"))
    args = parser.parse_args()
    if args.command == "build-seed":
        build_seed(args.db)
    elif args.command == "build-visual-identities":
        build_visual_identities(args.db)
    elif args.command == "summary":
        summary(args.db)


if __name__ == "__main__":
    main()
