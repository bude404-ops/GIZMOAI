"""SQLite schema for Historia Phase 1.

Migrations are idempotent and additive. This phase uses stdlib sqlite3 so the
research foundation can run locally without external services.
"""

SCHEMA_VERSION = 1

DDL = [
    """
    CREATE TABLE IF NOT EXISTS schema_migrations (
      version INTEGER PRIMARY KEY,
      applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_figures (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      slug TEXT NOT NULL UNIQUE,
      full_name TEXT NOT NULL,
      birth_date TEXT,
      death_date TEXT,
      historical_period TEXT NOT NULL,
      region TEXT NOT NULL,
      culture_civilization TEXT NOT NULL,
      occupation_title TEXT NOT NULL,
      adult_status TEXT NOT NULL DEFAULT 'ADULT_CONFIRMED',
      research_status TEXT NOT NULL DEFAULT 'DISCOVERED',
      appearance_certainty TEXT NOT NULL DEFAULT 'UNKNOWN_ARTISTIC_RECONSTRUCTION',
      summary TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CHECK (adult_status IN ('ADULT_CONFIRMED','ADULT_ASSUMED_HISTORICAL','REJECTED_MINOR_OR_UNCLEAR')),
      CHECK (research_status IN ('DISCOVERED','VERIFYING','STRUCTURED','READY_FOR_IDEAS','NEEDS_REVIEW')),
      CHECK (appearance_certainty IN ('PORTRAIT_SUPPORTED','TEXTUAL_DESCRIPTION_SUPPORTED','SCULPTURE','COIN','UNKNOWN_ARTISTIC_RECONSTRUCTION'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_sources (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER NOT NULL,
      title TEXT NOT NULL,
      author TEXT,
      publisher TEXT,
      url TEXT,
      source_type TEXT NOT NULL,
      reliability_score REAL NOT NULL DEFAULT 0.5,
      notes TEXT NOT NULL DEFAULT '',
      accessed_at TEXT,
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (figure_id) REFERENCES historical_figures(id) ON DELETE CASCADE,
      CHECK (source_type IN ('MUSEUM','UNIVERSITY','LIBRARY','ACADEMIC','ENCYCLOPEDIA','GOVERNMENT_CULTURAL','PRIMARY_TEXT','BOOK','OTHER')),
      CHECK (reliability_score >= 0 AND reliability_score <= 1)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_facts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER NOT NULL,
      claim TEXT NOT NULL,
      classification TEXT NOT NULL,
      evidence_strength TEXT NOT NULL,
      source_count INTEGER NOT NULL DEFAULT 0,
      notes TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (figure_id) REFERENCES historical_figures(id) ON DELETE CASCADE,
      CHECK (classification IN ('VERIFIED_FACT','HISTORICAL_INTERPRETATION','AI_DRAMATIZATION')),
      CHECK (evidence_strength IN ('STRONG','MODERATE','WEAK','UNSOURCED'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS fact_sources (
      fact_id INTEGER NOT NULL,
      source_id INTEGER NOT NULL,
      support_note TEXT NOT NULL DEFAULT '',
      PRIMARY KEY (fact_id, source_id),
      FOREIGN KEY (fact_id) REFERENCES historical_facts(id) ON DELETE CASCADE,
      FOREIGN KEY (source_id) REFERENCES historical_sources(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_uncertainties (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER NOT NULL,
      topic TEXT NOT NULL,
      description TEXT NOT NULL,
      confidence_level TEXT NOT NULL DEFAULT 'LOW',
      handling_rule TEXT NOT NULL DEFAULT 'FLAG_FOR_REVIEW',
      FOREIGN KEY (figure_id) REFERENCES historical_figures(id) ON DELETE CASCADE,
      CHECK (confidence_level IN ('HIGH','MEDIUM','LOW')),
      CHECK (handling_rule IN ('ALLOW_IF_LABELED','FLAG_FOR_REVIEW','DO_NOT_USE'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_myths (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER NOT NULL,
      myth TEXT NOT NULL,
      correction TEXT NOT NULL,
      use_in_content BOOLEAN NOT NULL DEFAULT 1,
      FOREIGN KEY (figure_id) REFERENCES historical_figures(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS visual_references (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER NOT NULL,
      reference_type TEXT NOT NULL,
      description TEXT NOT NULL,
      source_id INTEGER,
      confidence_level TEXT NOT NULL DEFAULT 'LOW',
      usage_rule TEXT NOT NULL DEFAULT 'LABEL_AS_ARTISTIC_RECONSTRUCTION',
      FOREIGN KEY (figure_id) REFERENCES historical_figures(id) ON DELETE CASCADE,
      FOREIGN KEY (source_id) REFERENCES historical_sources(id) ON DELETE SET NULL,
      CHECK (reference_type IN ('KNOWN_PORTRAIT','COIN','SCULPTURE','TEXTUAL_DESCRIPTION','CLOTHING','ARCHITECTURE','CULTURAL_OBJECT','ENVIRONMENT')),
      CHECK (confidence_level IN ('HIGH','MEDIUM','LOW'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS character_bibles (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER UNIQUE,
      fictional_character_id INTEGER UNIQUE,
      name TEXT NOT NULL,
      classification TEXT NOT NULL,
      era TEXT NOT NULL,
      age_status TEXT NOT NULL DEFAULT 'ADULT',
      personality TEXT NOT NULL DEFAULT '',
      appearance TEXT NOT NULL DEFAULT '',
      hair TEXT NOT NULL DEFAULT '',
      eyes TEXT NOT NULL DEFAULT '',
      facial_characteristics TEXT NOT NULL DEFAULT '',
      body_build TEXT NOT NULL DEFAULT '',
      fashion TEXT NOT NULL DEFAULT '',
      jewelry TEXT NOT NULL DEFAULT '',
      makeup TEXT NOT NULL DEFAULT '',
      voice TEXT NOT NULL DEFAULT '',
      accent TEXT NOT NULL DEFAULT '',
      confidence_level INTEGER NOT NULL DEFAULT 7,
      humor TEXT NOT NULL DEFAULT '',
      speaking_style TEXT NOT NULL DEFAULT '',
      interests TEXT NOT NULL DEFAULT '',
      historical_knowledge TEXT NOT NULL DEFAULT '',
      approved_outfits TEXT NOT NULL DEFAULT '[]',
      approved_environments TEXT NOT NULL DEFAULT '[]',
      content_history TEXT NOT NULL DEFAULT '[]',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      CHECK (classification IN ('HISTORICAL','FICTIONAL')),
      CHECK (age_status = 'ADULT'),
      CHECK (confidence_level BETWEEN 1 AND 10)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS scene_concepts (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER NOT NULL,
      name TEXT NOT NULL,
      historical_environment TEXT NOT NULL,
      story_purpose TEXT NOT NULL,
      visual_appeal_notes TEXT NOT NULL,
      camera_direction TEXT NOT NULL,
      accuracy_notes TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (figure_id) REFERENCES historical_figures(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content_ideas (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      figure_id INTEGER NOT NULL,
      fact_id INTEGER NOT NULL,
      mode TEXT NOT NULL DEFAULT 'HISTORICAL',
      hook TEXT NOT NULL,
      scene_id INTEGER,
      visual_concept TEXT NOT NULL,
      camera_movement TEXT NOT NULL,
      voiceover TEXT NOT NULL,
      caption TEXT NOT NULL,
      cta TEXT NOT NULL,
      hashtags TEXT NOT NULL DEFAULT '[]',
      visual_appeal_score REAL NOT NULL DEFAULT 0,
      curiosity_score REAL NOT NULL DEFAULT 0,
      shareability_score REAL NOT NULL DEFAULT 0,
      educational_value_score REAL NOT NULL DEFAULT 0,
      overall_prediction REAL NOT NULL DEFAULT 0,
      status TEXT NOT NULL DEFAULT 'IDEA',
      ai_generated_disclosure TEXT NOT NULL DEFAULT 'AI historical reconstruction',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (figure_id) REFERENCES historical_figures(id) ON DELETE CASCADE,
      FOREIGN KEY (fact_id) REFERENCES historical_facts(id) ON DELETE RESTRICT,
      FOREIGN KEY (scene_id) REFERENCES scene_concepts(id) ON DELETE SET NULL,
      CHECK (mode IN ('HISTORICAL','FICTIONAL')),
      CHECK (status IN ('IDEA','RANKED','APPROVED_FOR_GENERATION','REJECTED','NEEDS_REVIEW'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS historical_accuracy_checks (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      content_idea_id INTEGER NOT NULL,
      clothing_score REAL NOT NULL DEFAULT 0,
      architecture_score REAL NOT NULL DEFAULT 0,
      weapons_score REAL NOT NULL DEFAULT 0,
      geography_score REAL NOT NULL DEFAULT 0,
      timeline_score REAL NOT NULL DEFAULT 0,
      culture_score REAL NOT NULL DEFAULT 0,
      names_score REAL NOT NULL DEFAULT 0,
      events_score REAL NOT NULL DEFAULT 0,
      relationships_score REAL NOT NULL DEFAULT 0,
      language_score REAL NOT NULL DEFAULT 0,
      technology_score REAL NOT NULL DEFAULT 0,
      overall_score REAL NOT NULL DEFAULT 0,
      review_required BOOLEAN NOT NULL DEFAULT 1,
      notes TEXT NOT NULL DEFAULT '',
      created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (content_idea_id) REFERENCES content_ideas(id) ON DELETE CASCADE
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_figures_period ON historical_figures(historical_period)",
    "CREATE INDEX IF NOT EXISTS idx_figures_region ON historical_figures(region)",
    "CREATE INDEX IF NOT EXISTS idx_sources_figure ON historical_sources(figure_id)",
    "CREATE INDEX IF NOT EXISTS idx_facts_classification ON historical_facts(classification)",
    "CREATE INDEX IF NOT EXISTS idx_ideas_score ON content_ideas(overall_prediction DESC)",
    "CREATE INDEX IF NOT EXISTS idx_accuracy_review ON historical_accuracy_checks(review_required)",
]
