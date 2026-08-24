"""Phase 1 research engine: discover -> verify -> structure -> store -> generate."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .database import HistoriaDatabase

FACT_CLASSIFICATIONS = {"VERIFIED_FACT", "HISTORICAL_INTERPRETATION", "AI_DRAMATIZATION"}


@dataclass(frozen=True)
class IdeaScores:
    hook_strength: float
    visual_appeal: float
    curiosity: float
    historical_significance: float
    emotional_response: float
    shareability: float
    character_recognition: float
    novelty: float
    x_format_compatibility: float

    @property
    def overall(self) -> float:
        weights = {
            "hook_strength": 0.16,
            "visual_appeal": 0.14,
            "curiosity": 0.15,
            "historical_significance": 0.13,
            "emotional_response": 0.10,
            "shareability": 0.11,
            "character_recognition": 0.08,
            "novelty": 0.08,
            "x_format_compatibility": 0.05,
        }
        return sum(getattr(self, k) * w for k, w in weights.items())


class ResearchEngine:
    def __init__(self, db: HistoriaDatabase) -> None:
        self.db = db

    def ingest_research_record(self, record: dict[str, Any]) -> int:
        """Validate and store a structured historical research record."""
        self._validate_record(record)
        figure_id = self.db.upsert_historical_figure(record["figure"])

        source_ids: list[int] = []
        for source in record.get("sources", []):
            source_ids.append(self.db.add_source(figure_id, source))

        for fact in record.get("facts", []):
            linked = source_ids[: max(1, min(len(source_ids), int(fact.get("source_count", len(source_ids)))))]
            self.db.add_fact(figure_id, fact, linked if fact.get("classification") == "VERIFIED_FACT" else linked)

        for item in record.get("uncertainties", []):
            self.db.add_uncertainty(figure_id, item)

        for item in record.get("visual_references", []):
            self.db.add_visual_reference(figure_id, item, source_ids[0] if source_ids else None)

        for scene in record.get("scenes", []):
            self.db.add_scene(figure_id, scene)

        if record.get("character_bible"):
            self.db.add_character_bible(figure_id, record["character_bible"])

        self._update_research_status(figure_id)
        return figure_id

    def _validate_record(self, record: dict[str, Any]) -> None:
        figure = record.get("figure", {})
        if figure.get("adult_status") == "REJECTED_MINOR_OR_UNCLEAR":
            raise ValueError("Historia only supports adult women; rejected minor/unclear record")
        if len(record.get("sources", [])) < 2:
            raise ValueError("Historical records require at least two sources")
        for fact in record.get("facts", []):
            cls = fact.get("classification")
            if cls not in FACT_CLASSIFICATIONS:
                raise ValueError(f"invalid fact classification: {cls}")
            if cls == "VERIFIED_FACT" and fact.get("evidence_strength") not in {"STRONG", "MODERATE"}:
                raise ValueError("VERIFIED_FACT must have STRONG or MODERATE evidence")
            if "quote" in fact.get("claim", "").lower() and fact.get("classification") != "VERIFIED_FACT":
                raise ValueError("Possible quote claims must be verified or omitted")

    def _update_research_status(self, figure_id: int) -> None:
        counts = self.db.one(
            """
            SELECT
              (SELECT COUNT(*) FROM historical_sources WHERE figure_id=?) AS sources,
              (SELECT COUNT(*) FROM historical_facts WHERE figure_id=? AND classification='VERIFIED_FACT') AS verified_facts,
              (SELECT COUNT(*) FROM visual_references WHERE figure_id=?) AS visual_refs,
              (SELECT COUNT(*) FROM historical_uncertainties WHERE figure_id=? AND handling_rule='DO_NOT_USE') AS blocked_uncertainties
            """,
            (figure_id, figure_id, figure_id, figure_id),
        ) or {}
        if counts.get("sources", 0) >= 2 and counts.get("verified_facts", 0) >= 1 and counts.get("visual_refs", 0) >= 1:
            status = "READY_FOR_IDEAS" if counts.get("blocked_uncertainties", 0) == 0 else "NEEDS_REVIEW"
        else:
            status = "STRUCTURED"
        self.db.execute("UPDATE historical_figures SET research_status=?, updated_at=CURRENT_TIMESTAMP WHERE id=?", (status, figure_id))

    def generate_ideas_for_ready_figures(self, limit_per_figure: int = 5) -> list[int]:
        """Generate cheap text-only content ideas from verified facts and scenes."""
        ready = self.db.query("SELECT * FROM historical_figures WHERE research_status='READY_FOR_IDEAS'")
        created: list[int] = []
        for figure in ready:
            facts = self.db.query(
                "SELECT * FROM historical_facts WHERE figure_id=? AND classification='VERIFIED_FACT' ORDER BY id LIMIT ?",
                (figure["id"], limit_per_figure),
            )
            scenes = self.db.query("SELECT * FROM scene_concepts WHERE figure_id=? ORDER BY id", (figure["id"],))
            for idx, fact in enumerate(facts):
                scene = scenes[idx % len(scenes)] if scenes else None
                score = self.score_concept(figure, fact, scene)
                hook = self._hook_for(figure, fact)
                cur = self.db.execute(
                    """
                    INSERT INTO content_ideas (
                      figure_id, fact_id, hook, scene_id, visual_concept, camera_movement,
                      voiceover, caption, cta, hashtags, visual_appeal_score, curiosity_score,
                      shareability_score, educational_value_score, overall_prediction, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'RANKED')
                    """,
                    (
                        figure["id"], fact["id"], hook, scene["id"] if scene else None,
                        self._visual_concept(figure, scene),
                        scene["camera_direction"] if scene else "Slow cinematic push-in with direct eye contact.",
                        self._voiceover(figure, fact),
                        self._caption(figure, fact),
                        "Which woman from history should come alive next?",
                        '["#AIHistory","#WomenInHistory","#CinematicAI","#History"]',
                        score.visual_appeal, score.curiosity, score.shareability,
                        score.historical_significance, score.overall,
                    ),
                )
                idea_id = int(cur.lastrowid)
                self._create_accuracy_check(idea_id, score)
                created.append(idea_id)
        return created

    def score_concept(self, figure: dict[str, Any], fact: dict[str, Any], scene: dict[str, Any] | None) -> IdeaScores:
        claim = fact["claim"].lower()
        hook_strength = 85 if any(x in claim for x in ["ruled", "defeated", "first", "war", "queen", "emperor"]) else 68
        visual_appeal = 78 if scene else 62
        curiosity = 88 if any(x in claim for x in ["before", "mystery", "forgot", "against", "first"]) else 72
        significance = 90 if fact.get("evidence_strength") == "STRONG" else 76
        recognition = 88 if figure["slug"] in {"cleopatra-vii", "ada-lovelace"} else 64
        novelty = 82 if figure["slug"] not in {"cleopatra-vii"} else 60
        return IdeaScores(
            hook_strength=hook_strength,
            visual_appeal=visual_appeal,
            curiosity=curiosity,
            historical_significance=significance,
            emotional_response=74,
            shareability=76,
            character_recognition=recognition,
            novelty=novelty,
            x_format_compatibility=84,
        )

    def _create_accuracy_check(self, idea_id: int, score: IdeaScores) -> None:
        baseline = min(92, max(60, score.historical_significance))
        review_required = baseline < 75
        self.db.execute(
            """
            INSERT INTO historical_accuracy_checks (
              content_idea_id, clothing_score, architecture_score, weapons_score, geography_score,
              timeline_score, culture_score, names_score, events_score, relationships_score,
              language_score, technology_score, overall_score, review_required, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (idea_id, baseline, baseline, baseline, baseline, baseline, baseline, baseline, baseline, baseline, baseline, baseline, baseline, review_required, "Phase 1 text-only preflight; media QC arrives in later phases."),
        )

    def _hook_for(self, figure: dict[str, Any], fact: dict[str, Any]) -> str:
        if "before cleopatra" in fact["claim"].lower():
            return "She ruled Egypt before Cleopatra."
        if "rome" in fact["claim"].lower() and "defeat" in fact["claim"].lower():
            return "Rome thought she would be easy to defeat."
        if "first" in fact["claim"].lower():
            return "History forgot how powerful she really was."
        return f"You know the name {figure['full_name']}. You may not know this."

    def _visual_concept(self, figure: dict[str, Any], scene: dict[str, Any] | None) -> str:
        environment = scene["historical_environment"] if scene else figure["region"]
        certainty = figure.get("appearance_certainty", "UNKNOWN_ARTISTIC_RECONSTRUCTION")
        return f"Adult cinematic AI historical reconstruction of {figure['full_name']} in {environment}; beauty-led but tasteful; appearance certainty: {certainty}."

    def _voiceover(self, figure: dict[str, Any], fact: dict[str, Any]) -> str:
        return f"This is an AI historical reconstruction of {figure['full_name']}. {fact['claim']}"

    def _caption(self, figure: dict[str, Any], fact: dict[str, Any]) -> str:
        return f"AI historical reconstruction. {figure['full_name']}: {fact['claim']}"
