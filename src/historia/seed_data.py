"""Seed records for Phase 1 smoke/integrity tests.

The seed set is intentionally small. It validates schema and workflow, not final
editorial coverage. Later research cycles should add richer source records.
"""

SEED_RECORDS = [
    {
        "figure": {
            "slug": "hatshepsut",
            "full_name": "Hatshepsut",
            "birth_date": "c. 1507 BCE",
            "death_date": "1458 BCE",
            "historical_period": "New Kingdom Egypt, 18th Dynasty",
            "region": "Egypt",
            "culture_civilization": "Ancient Egyptian",
            "occupation_title": "Pharaoh",
            "adult_status": "ADULT_CONFIRMED",
            "research_status": "DISCOVERED",
            "appearance_certainty": "SCULPTURE",
            "summary": "One of ancient Egypt's most successful female pharaohs, associated with major building projects and trade expeditions.",
        },
        "sources": [
            {"title": "Hatshepsut", "publisher": "Encyclopaedia Britannica", "source_type": "ENCYCLOPEDIA", "reliability_score": 0.82},
            {"title": "Hatshepsut and Thutmose III", "publisher": "The Metropolitan Museum of Art", "source_type": "MUSEUM", "reliability_score": 0.9},
        ],
        "facts": [
            {"claim": "Hatshepsut ruled Egypt as pharaoh before Cleopatra VII and commissioned major monuments including work at Deir el-Bahri.", "classification": "VERIFIED_FACT", "evidence_strength": "STRONG"},
            {"claim": "Her reign is often interpreted as a period of relative prosperity and ambitious state presentation.", "classification": "HISTORICAL_INTERPRETATION", "evidence_strength": "MODERATE"},
        ],
        "uncertainties": [
            {"topic": "Public self-presentation", "description": "Some representations use pharaonic male regalia; content must explain this as royal iconography, not disguise fantasy.", "confidence_level": "MEDIUM", "handling_rule": "ALLOW_IF_LABELED"}
        ],
        "visual_references": [
            {"reference_type": "SCULPTURE", "description": "Statues and reliefs from temple contexts support royal regalia and ceremonial styling.", "confidence_level": "HIGH", "usage_rule": "USE_AS_PRIMARY_VISUAL_REFERENCE"},
            {"reference_type": "ARCHITECTURE", "description": "Deir el-Bahri terraces and New Kingdom temple architecture.", "confidence_level": "HIGH"},
        ],
        "scenes": [
            {"name": "Temple Reveal", "historical_environment": "Deir el-Bahri inspired temple terrace", "story_purpose": "Show political authority and monumental legacy", "visual_appeal_notes": "Regal gold details, linen, lapis jewelry, strong sun-shadow contrast", "camera_direction": "Low-angle slow push-in as banners move in desert wind", "accuracy_notes": "Keep regalia ceremonial and avoid modern fantasy armor."},
            {"name": "Nile Procession", "historical_environment": "Royal Nile procession", "story_purpose": "Frame prosperity and state power", "visual_appeal_notes": "Golden-hour water reflections, formal profile, elegant movement", "camera_direction": "Tracking shot from river surface to direct eye contact"},
        ],
        "character_bible": {"name": "Hatshepsut", "era": "New Kingdom Egypt", "personality": "Controlled, regal, strategically confident", "appearance": "Artistic reconstruction guided by royal sculpture and ceremonial regalia", "fashion": "Fine linen, broad collar jewelry, pharaonic royal elements", "jewelry": "Gold and lapis-inspired collar pieces", "voice": "Low, precise, commanding", "accent": "Neutral English narration; avoid fake ancient accent", "confidence_level": 10, "speaking_style": "Measured authority", "approved_outfits": ["ceremonial linen regalia", "temple procession robe"], "approved_environments": ["temple terrace", "Nile procession", "throne room"]},
    },
    {
        "figure": {
            "slug": "boudica",
            "full_name": "Boudica",
            "birth_date": "c. 1st century CE",
            "death_date": "c. 60/61 CE",
            "historical_period": "Roman Britain",
            "region": "Britain",
            "culture_civilization": "Iceni / Celtic Britain",
            "occupation_title": "Queen and rebellion leader",
            "adult_status": "ADULT_CONFIRMED",
            "research_status": "DISCOVERED",
            "appearance_certainty": "TEXTUAL_DESCRIPTION_SUPPORTED",
            "summary": "Iceni queen associated with a major revolt against Roman rule in Britain.",
        },
        "sources": [
            {"title": "Boudica", "publisher": "Encyclopaedia Britannica", "source_type": "ENCYCLOPEDIA", "reliability_score": 0.8},
            {"title": "Annals", "author": "Tacitus", "publisher": "Classical primary tradition", "source_type": "PRIMARY_TEXT", "reliability_score": 0.65, "notes": "Roman literary source; hostile perspective possible."},
        ],
        "facts": [
            {"claim": "Boudica led a revolt against Roman authority in Britain around 60/61 CE.", "classification": "VERIFIED_FACT", "evidence_strength": "STRONG"},
            {"claim": "Roman sources frame her as physically striking and rhetorically powerful, but those descriptions reflect Roman literary agendas.", "classification": "HISTORICAL_INTERPRETATION", "evidence_strength": "MODERATE"},
        ],
        "uncertainties": [
            {"topic": "Exact appearance", "description": "Known mainly through Roman textual description; all visuals require reconstruction labeling.", "confidence_level": "LOW", "handling_rule": "ALLOW_IF_LABELED"}
        ],
        "visual_references": [
            {"reference_type": "TEXTUAL_DESCRIPTION", "description": "Roman descriptions support imposing presence but not exact facial identity.", "confidence_level": "MEDIUM"},
            {"reference_type": "CLOTHING", "description": "Iron Age British textile and torc references should guide wardrobe.", "confidence_level": "MEDIUM"},
        ],
        "scenes": [
            {"name": "War Council", "historical_environment": "Celtic camp at dusk", "story_purpose": "Show leadership before revolt", "visual_appeal_notes": "Powerful posture, braided red hair interpretation, torc, firelight", "camera_direction": "Handheld orbit into direct stare", "accuracy_notes": "Avoid fantasy leather bikini armor."},
            {"name": "Chariot Storm", "historical_environment": "Muddy road and tribal movement", "story_purpose": "Capture motion and defiance", "visual_appeal_notes": "Wind, cloak movement, battle standard silhouette", "camera_direction": "Fast foreground pass then slow-motion reveal"},
        ],
        "character_bible": {"name": "Boudica", "era": "Roman Britain", "personality": "Fierce, defiant, charismatic", "appearance": "Adult artistic reconstruction from Roman textual cues", "hair": "Long red/auburn interpretation, clearly labeled uncertain", "fashion": "Wool cloak, tunic, torc, practical war-leader styling", "voice": "Forceful and grave", "accent": "Neutral English narration", "confidence_level": 10, "speaking_style": "Rallying, direct", "approved_outfits": ["wool cloak and torc", "war council dress"], "approved_environments": ["Celtic camp", "forest road", "battlefield edge"]},
    },
    {
        "figure": {
            "slug": "ada-lovelace",
            "full_name": "Ada Lovelace",
            "birth_date": "1815-12-10",
            "death_date": "1852-11-27",
            "historical_period": "Victorian Britain",
            "region": "Britain",
            "culture_civilization": "Victorian British",
            "occupation_title": "Mathematician and writer",
            "adult_status": "ADULT_CONFIRMED",
            "research_status": "DISCOVERED",
            "appearance_certainty": "PORTRAIT_SUPPORTED",
            "summary": "Mathematician known for her notes on Charles Babbage's Analytical Engine.",
        },
        "sources": [
            {"title": "Ada Lovelace", "publisher": "Encyclopaedia Britannica", "source_type": "ENCYCLOPEDIA", "reliability_score": 0.82},
            {"title": "Ada Lovelace Collection", "publisher": "Computer History Museum", "source_type": "MUSEUM", "reliability_score": 0.88},
        ],
        "facts": [
            {"claim": "Ada Lovelace wrote influential notes on Babbage's Analytical Engine, including an algorithmic description for Bernoulli numbers.", "classification": "VERIFIED_FACT", "evidence_strength": "STRONG"},
            {"claim": "Calling her the first computer programmer is common but debated depending on definitions and credit assigned to Babbage and Lovelace.", "classification": "HISTORICAL_INTERPRETATION", "evidence_strength": "MODERATE"},
        ],
        "uncertainties": [
            {"topic": "First programmer label", "description": "Use as an interpretation, not an uncontested fact.", "confidence_level": "MEDIUM", "handling_rule": "ALLOW_IF_LABELED"}
        ],
        "visual_references": [
            {"reference_type": "KNOWN_PORTRAIT", "description": "Portraits support Victorian styling and general facial reference.", "confidence_level": "HIGH"},
            {"reference_type": "ENVIRONMENT", "description": "Victorian study, mathematical papers, mechanical computing references.", "confidence_level": "HIGH"},
        ],
        "scenes": [
            {"name": "Mechanical Study", "historical_environment": "Victorian study with mathematical notes and brass mechanical forms", "story_purpose": "Show intellectual glamour and machine imagination", "visual_appeal_notes": "Elegant dress, candlelight, close-up writing hand, confident glance", "camera_direction": "Macro on ink, rack focus to face"},
            {"name": "London Salon", "historical_environment": "Victorian salon", "story_purpose": "Frame her as socially connected and intellectually bold", "visual_appeal_notes": "Velvet, pearls, polished wood, sharp eyes", "camera_direction": "Slow dolly through salon to seated reveal"},
        ],
        "character_bible": {"name": "Ada Lovelace", "era": "Victorian Britain", "personality": "Brilliant, imaginative, analytically confident", "appearance": "Portrait-supported adult reconstruction", "fashion": "Elegant Victorian dress", "jewelry": "Tasteful period jewelry", "voice": "Clear, intelligent, lightly amused", "accent": "Refined British narration", "confidence_level": 8, "speaking_style": "Precise but vivid", "approved_outfits": ["Victorian evening dress", "study dress"], "approved_environments": ["study", "salon", "mechanical demonstration room"]},
    },
    {
        "figure": {
            "slug": "cleopatra-vii",
            "full_name": "Cleopatra VII Philopator",
            "birth_date": "69 BCE",
            "death_date": "30 BCE",
            "historical_period": "Ptolemaic Egypt / Late Roman Republic",
            "region": "Egypt and Eastern Mediterranean",
            "culture_civilization": "Ptolemaic Greek Egyptian",
            "occupation_title": "Queen",
            "adult_status": "ADULT_CONFIRMED",
            "research_status": "DISCOVERED",
            "appearance_certainty": "COIN",
            "summary": "Last active ruler of the Ptolemaic Kingdom of Egypt, central to Roman political history.",
        },
        "sources": [
            {"title": "Cleopatra", "publisher": "Encyclopaedia Britannica", "source_type": "ENCYCLOPEDIA", "reliability_score": 0.82},
            {"title": "Ptolemaic coin portraits", "publisher": "Museum numismatic collections", "source_type": "MUSEUM", "reliability_score": 0.75},
        ],
        "facts": [
            {"claim": "Cleopatra VII was the last active ruler of the Ptolemaic Kingdom of Egypt and was politically connected with Julius Caesar and Mark Antony.", "classification": "VERIFIED_FACT", "evidence_strength": "STRONG"},
            {"claim": "Modern glamour portrayals often exaggerate certainty about her appearance; surviving coin portraits are stylized political images.", "classification": "HISTORICAL_INTERPRETATION", "evidence_strength": "MODERATE"},
        ],
        "uncertainties": [
            {"topic": "Exact appearance", "description": "Coin portraits are stylized; all photoreal visuals must be labeled reconstruction.", "confidence_level": "LOW", "handling_rule": "ALLOW_IF_LABELED"}
        ],
        "visual_references": [
            {"reference_type": "COIN", "description": "Coin portraits provide stylized profile references, not photographic certainty.", "confidence_level": "MEDIUM"},
            {"reference_type": "ARCHITECTURE", "description": "Alexandrian and Hellenistic Egyptian environment references.", "confidence_level": "MEDIUM"},
        ],
        "scenes": [
            {"name": "Alexandria Balcony", "historical_environment": "Hellenistic Alexandria palace balcony", "story_purpose": "Show political charisma, not generic seduction", "visual_appeal_notes": "Regal silhouette, sea light, gold jewelry, intelligent eye contact", "camera_direction": "Crane-like reveal from harbor light to face", "accuracy_notes": "Avoid anachronistic fantasy costume."},
            {"name": "Royal Banquet", "historical_environment": "Ptolemaic royal banquet", "story_purpose": "Frame diplomacy and danger", "visual_appeal_notes": "Candlelit gold, linen, controlled smile, tension", "camera_direction": "Slow lateral glide past guests to direct look"},
        ],
        "character_bible": {"name": "Cleopatra VII Philopator", "era": "Ptolemaic Egypt", "personality": "Politically agile, educated, theatrical, controlled", "appearance": "Coin-guided artistic reconstruction; exact appearance uncertain", "fashion": "Hellenistic Egyptian royal styling", "jewelry": "Gold and gemstone royal jewelry", "voice": "Calm, strategic, charismatic", "accent": "Neutral narration; avoid fake ancient accent", "confidence_level": 10, "speaking_style": "Elegant, pointed, dangerous", "approved_outfits": ["royal linen gown", "formal banquet styling"], "approved_environments": ["Alexandria balcony", "royal banquet", "temple interior"]},
    },
]
