"""
International Classroom Mapping — v0.4.0 Roadmap Module

This module provides the architecture for mapping:
  1. US grade levels ↔ international grade equivalents
  2. Marzano's New Taxonomy ↔ international curriculum competency frameworks

STATUS: Foundational data structures and mappings are defined here.
Full UI integration is scheduled for v0.4.0.

EXTENDING THIS MODULE:
  - Add a new country: create an entry in COUNTRIES and populate
    GRADE_LEVEL_MAP and CURRICULUM_FRAMEWORK_MAP for that country code.
  - All country codes follow ISO 3166-1 alpha-2 standard.
"""

from dataclasses import dataclass, field
from typing import Optional


# ─────────────────────────────────────────────────────────────
# Country registry
# ─────────────────────────────────────────────────────────────

@dataclass
class Country:
    code: str                   # ISO 3166-1 alpha-2
    name: str
    education_system: str       # name of the national education system
    curriculum_framework: str   # primary standards framework
    grade_terminology: str      # how grades are referred to
    compulsory_age_range: str
    grading_notes: str = ""


COUNTRIES: dict[str, Country] = {
    "US": Country(
        code="US", name="United States",
        education_system="US K-12",
        curriculum_framework="Common Core / NGSS / C3",
        grade_terminology="Grade K–12",
        compulsory_age_range="5–18",
    ),
    "GB": Country(
        code="GB", name="United Kingdom (England)",
        education_system="National Curriculum (England)",
        curriculum_framework="UK National Curriculum Key Stages 1–4 + A-Levels",
        grade_terminology="Year 1–13",
        compulsory_age_range="5–16",
        grading_notes="Key Stage 1 (Yrs 1–2), KS2 (3–6), KS3 (7–9), KS4 (10–11 GCSE), KS5 (12–13 A-Level)",
    ),
    "AU": Country(
        code="AU", name="Australia",
        education_system="Australian Curriculum (ACARA)",
        curriculum_framework="Australian Curriculum v9.0",
        grade_terminology="Foundation + Year 1–12",
        compulsory_age_range="6–17",
        grading_notes="Foundation = Prep/Kindergarten. Years 11–12 vary by state (VCE, HSC, QCE, etc.)",
    ),
    "CA": Country(
        code="CA", name="Canada",
        education_system="Provincial Curricula (no federal standard)",
        curriculum_framework="Provincial — Ontario, BC, Alberta, Quebec, etc.",
        grade_terminology="Grade K–12",
        compulsory_age_range="6–16 (varies by province)",
        grading_notes="Curriculum is provincially controlled. Ontario and BC are most commonly referenced.",
    ),
    "FR": Country(
        code="FR", name="France",
        education_system="Éducation nationale",
        curriculum_framework="Programmes de l'Éducation nationale",
        grade_terminology="CP–Terminale (Cycle 1–4)",
        compulsory_age_range="3–16",
        grading_notes="Cycle 1 (PS-GS/Maternelle), Cycle 2 (CP-CE2), Cycle 3 (CM1-6e), Cycle 4 (5e-3e), Lycée (2de-Terminale)",
    ),
    "DE": Country(
        code="DE", name="Germany",
        education_system="Kultusministerkonferenz (KMK) — Länder controlled",
        curriculum_framework="KMK Bildungsstandards",
        grade_terminology="Klasse 1–13 (varies by Bundesland)",
        compulsory_age_range="6–15/18",
        grading_notes="Tracking begins at Grade 4/5 into Hauptschule, Realschule, or Gymnasium. Abitur at end of Gymnasium.",
    ),
    "JP": Country(
        code="JP", name="Japan",
        education_system="Ministry of Education (MEXT)",
        curriculum_framework="Course of Study (学習指導要領)",
        grade_terminology="小学校1–6 / 中学校1–3 / 高校1–3",
        compulsory_age_range="6–15",
        grading_notes="Elementary (小学校) 6 yrs, Middle (中学校) 3 yrs, High (高校) 3 yrs. University entrance exams (共通テスト).",
    ),
    "IB": Country(
        code="IB", name="International Baccalaureate",
        education_system="IB Continuum",
        curriculum_framework="PYP / MYP / DP / CP",
        grade_terminology="PYP (ages 3–12) / MYP (11–16) / DP & CP (16–19)",
        compulsory_age_range="3–19 (school-dependent)",
        grading_notes="PYP = Primary Years, MYP = Middle Years, DP = Diploma, CP = Career-related. Used in 150+ countries.",
    ),
    "NZ": Country(
        code="NZ", name="New Zealand",
        education_system="New Zealand Curriculum",
        curriculum_framework="The New Zealand Curriculum / Te Marautanga o Aotearoa",
        grade_terminology="Year 1–13",
        compulsory_age_range="6–16",
        grading_notes="NCEA (National Certificate of Educational Achievement) at Years 11–13.",
    ),
    "SG": Country(
        code="SG", name="Singapore",
        education_system="Ministry of Education Singapore",
        curriculum_framework="Singapore Curriculum Framework",
        grade_terminology="Primary 1–6 / Secondary 1–5 / JC 1–2",
        compulsory_age_range="6–15",
        grading_notes="PSLE at P6, O-Levels at Sec 4/5, A-Levels at JC2. Known for strong mathematics education.",
    ),
}


# ─────────────────────────────────────────────────────────────
# Grade level equivalency table
# Maps US Grade K-12 to approximate equivalents in other systems
# ─────────────────────────────────────────────────────────────

GRADE_LEVEL_MAP: dict[str, dict[str, str]] = {
    "Kindergarten": {
        "US": "Kindergarten (age 5–6)",
        "GB": "Year 1",
        "AU": "Foundation / Prep",
        "CA": "Senior Kindergarten",
        "FR": "Grande Section (GS)",
        "DE": "Vorschule / Klasse 1",
        "JP": "小学校1年 (Grade 1)",
        "IB": "PYP Year 1",
        "NZ": "Year 1",
        "SG": "Primary 1",
    },
    "Grade 1": {
        "US": "Grade 1 (age 6–7)",
        "GB": "Year 2",
        "AU": "Year 1",
        "CA": "Grade 1",
        "FR": "CP (Cours Préparatoire)",
        "DE": "Klasse 1",
        "JP": "小学校1年",
        "IB": "PYP Year 2",
        "NZ": "Year 2",
        "SG": "Primary 1",
    },
    "Grade 2": {
        "US": "Grade 2 (age 7–8)",
        "GB": "Year 3",
        "AU": "Year 2",
        "CA": "Grade 2",
        "FR": "CE1",
        "DE": "Klasse 2",
        "JP": "小学校2年",
        "IB": "PYP Year 3",
        "NZ": "Year 3",
        "SG": "Primary 2",
    },
    "Grade 3": {
        "US": "Grade 3 (age 8–9)",
        "GB": "Year 4",
        "AU": "Year 3",
        "CA": "Grade 3",
        "FR": "CE2",
        "DE": "Klasse 3",
        "JP": "小学校3年",
        "IB": "PYP Year 4",
        "NZ": "Year 4",
        "SG": "Primary 3",
    },
    "Grade 4": {
        "US": "Grade 4 (age 9–10)",
        "GB": "Year 5",
        "AU": "Year 4",
        "CA": "Grade 4",
        "FR": "CM1",
        "DE": "Klasse 4",
        "JP": "小学校4年",
        "IB": "PYP Year 5",
        "NZ": "Year 5",
        "SG": "Primary 4",
    },
    "Grade 5": {
        "US": "Grade 5 (age 10–11)",
        "GB": "Year 6",
        "AU": "Year 5",
        "CA": "Grade 5",
        "FR": "CM2",
        "DE": "Klasse 5",
        "JP": "小学校5年",
        "IB": "PYP Year 6",
        "NZ": "Year 6",
        "SG": "Primary 5",
    },
    "Grade 6": {
        "US": "Grade 6 (age 11–12)",
        "GB": "Year 7 (KS3 starts)",
        "AU": "Year 6",
        "CA": "Grade 6",
        "FR": "6ème (Collège starts)",
        "DE": "Klasse 6",
        "JP": "小学校6年 / 中学校1年",
        "IB": "MYP Year 1",
        "NZ": "Year 7",
        "SG": "Primary 6 (PSLE year)",
    },
    "Grade 7": {
        "US": "Grade 7 (age 12–13)",
        "GB": "Year 8",
        "AU": "Year 7",
        "CA": "Grade 7",
        "FR": "5ème",
        "DE": "Klasse 7",
        "JP": "中学校1年",
        "IB": "MYP Year 2",
        "NZ": "Year 8",
        "SG": "Secondary 1",
    },
    "Grade 8": {
        "US": "Grade 8 (age 13–14)",
        "GB": "Year 9",
        "AU": "Year 8",
        "CA": "Grade 8",
        "FR": "4ème",
        "DE": "Klasse 8",
        "JP": "中学校2年",
        "IB": "MYP Year 3",
        "NZ": "Year 9",
        "SG": "Secondary 2",
    },
    "Grade 9": {
        "US": "Grade 9 (age 14–15)",
        "GB": "Year 10 (GCSE starts)",
        "AU": "Year 9",
        "CA": "Grade 9",
        "FR": "3ème (Brevet year)",
        "DE": "Klasse 9",
        "JP": "中学校3年",
        "IB": "MYP Year 4",
        "NZ": "Year 10",
        "SG": "Secondary 3",
    },
    "Grade 10": {
        "US": "Grade 10 (age 15–16)",
        "GB": "Year 11 (GCSE exams)",
        "AU": "Year 10",
        "CA": "Grade 10",
        "FR": "Seconde (Lycée starts)",
        "DE": "Klasse 10",
        "JP": "高校1年",
        "IB": "MYP Year 5",
        "NZ": "Year 11 (NCEA L1)",
        "SG": "Secondary 4",
    },
    "Grade 11": {
        "US": "Grade 11 (age 16–17)",
        "GB": "Year 12 (A-Level starts)",
        "AU": "Year 11",
        "CA": "Grade 11",
        "FR": "Première",
        "DE": "Klasse 11 / Einführungsphase",
        "JP": "高校2年",
        "IB": "DP Year 1",
        "NZ": "Year 12 (NCEA L2)",
        "SG": "Junior College 1",
    },
    "Grade 12": {
        "US": "Grade 12 (age 17–18)",
        "GB": "Year 13 (A-Level exams)",
        "AU": "Year 12 (VCE/HSC/QCE)",
        "CA": "Grade 12",
        "FR": "Terminale (Baccalauréat)",
        "DE": "Klasse 12/13 / Abitur",
        "JP": "高校3年 (大学入試)",
        "IB": "DP Year 2",
        "NZ": "Year 13 (NCEA L3)",
        "SG": "Junior College 2 (A-Levels)",
    },
}


# ─────────────────────────────────────────────────────────────
# Marzano taxonomy ↔ international framework mapping
# Maps Marzano levels to approximate equivalents in major
# international curriculum competency descriptors.
# ─────────────────────────────────────────────────────────────

MARZANO_TO_INTERNATIONAL: dict[str, dict[str, str]] = {
    "retrieval": {
        "description": "Recall and recognition of facts, vocabulary, and procedures",
        "GB": "Working below expected standard / Foundation tier",
        "AU": "ACARA: Recognising and recalling facts",
        "IB_MYP": "Strand: Knowing and understanding",
        "IB_DP": "Command term: State, Identify, Recall",
        "FR": "Connaître — savoir restituer des connaissances",
        "DE": "Reproduzieren — Reproduktion von Wissen",
        "PISA": "Level 1–2: Locate explicitly stated information",
        "TIMSS": "Knowing domain",
    },
    "comprehension": {
        "description": "Identifying critical elements; paraphrasing; symbolising",
        "GB": "Working at expected standard",
        "AU": "ACARA: Understanding and interpreting",
        "IB_MYP": "Strand: Inquiring and analysing",
        "IB_DP": "Command term: Describe, Explain, Summarise",
        "FR": "Comprendre — interpréter et reformuler",
        "DE": "Verstehen — Sinnhaftes Wiedergeben",
        "PISA": "Level 2–3: Integrate and interpret",
        "TIMSS": "Applying domain (lower)",
    },
    "analysis": {
        "description": "Matching, classifying, analysing errors, generalising, specifying",
        "GB": "Working at greater depth within the expected standard",
        "AU": "ACARA: Analysing and evaluating",
        "IB_MYP": "Strand: Creating the solution / Evaluating",
        "IB_DP": "Command term: Analyse, Compare, Distinguish, Evaluate",
        "FR": "Analyser / Évaluer — décomposer et raisonner",
        "DE": "Analysieren — Sachverhalte erschließen und prüfen",
        "PISA": "Level 4–5: Reflect and evaluate",
        "TIMSS": "Reasoning domain (lower)",
    },
    "knowledge_utilization": {
        "description": "Decision making, problem solving, experimenting, investigating",
        "GB": "Exceeding expected standard / A*/A grade",
        "AU": "ACARA: Creating and applying in novel contexts",
        "IB_MYP": "Strand: Reflecting on impacts / Communicating",
        "IB_DP": "Command term: Design, Develop, Justify, Synthesise",
        "FR": "Créer / Mobiliser — produire et transférer",
        "DE": "Beurteilen / Gestalten — Transfer und Bewertung",
        "PISA": "Level 5–6: Formulate and generalise",
        "TIMSS": "Reasoning domain (higher)",
    },
    "metacognitive": {
        "description": "Goal setting, process monitoring, self-evaluation",
        "GB": "Assessed in Personal Learning & Thinking Skills (PLTS)",
        "AU": "General Capabilities: Self-management",
        "IB_MYP": "ATL Skills: Thinking & Self-management skills",
        "IB_DP": "Theory of Knowledge / Extended Essay reflection",
        "FR": "Apprendre à apprendre — compétence transversale",
        "DE": "Methodenkompetenz / Selbstkompetenz",
        "PISA": "Self-regulated learning constructs",
        "TIMSS": "Not directly assessed",
    },
    "self_system": {
        "description": "Motivation, self-efficacy, emotional engagement with learning",
        "GB": "SEAL / PSHE — Social and Emotional Aspects of Learning",
        "AU": "General Capabilities: Personal & Social Capability",
        "IB_MYP": "IB Learner Profile: Balanced, Reflective, Caring",
        "IB_DP": "IB Learner Profile attributes",
        "FR": "Parcours citoyen / bien-être de l'élève",
        "DE": "Sozialkompetenz / Persönlichkeitsentwicklung",
        "PISA": "Student well-being & motivational composites",
        "TIMSS": "Confidence in subject surveys",
    },
}


# ─────────────────────────────────────────────────────────────
# Helper functions
# ─────────────────────────────────────────────────────────────

def get_grade_equivalent(us_grade: str, country_code: str) -> Optional[str]:
    """Return the international equivalent of a US grade level."""
    mapping = GRADE_LEVEL_MAP.get(us_grade, {})
    return mapping.get(country_code)


def get_marzano_international(marzano_level: str, country_code: str = None) -> dict:
    """
    Return international equivalency descriptors for a Marzano level.
    If country_code is given, returns that country's specific mapping.
    """
    mapping = MARZANO_TO_INTERNATIONAL.get(marzano_level, {})
    if country_code and country_code in mapping:
        return {
            "marzano_level": marzano_level,
            "description": mapping.get("description", ""),
            "country": country_code,
            "equivalent": mapping[country_code],
        }
    return {
        "marzano_level": marzano_level,
        "description": mapping.get("description", ""),
        "all_equivalencies": {k: v for k, v in mapping.items() if k != "description"},
    }


def build_international_context(
    us_grade: str,
    marzano_level: str,
    country_code: str,
) -> str:
    """
    Build context string for injection into the AI prompt
    when assessing a student from an international system.
    """
    country = COUNTRIES.get(country_code)
    if not country:
        return ""

    grade_equiv = get_grade_equivalent(us_grade, country_code)
    marzano_equiv = MARZANO_TO_INTERNATIONAL.get(marzano_level, {}).get(
        country_code.replace("-", "_"), ""
    )

    lines = [
        f"\nINTERNATIONAL CONTEXT:",
        f"Country: {country.name}",
        f"Education system: {country.education_system}",
        f"Curriculum framework: {country.curriculum_framework}",
        f"Student's US grade equivalent: {us_grade}",
    ]
    if grade_equiv:
        lines.append(f"Equivalent in {country.name}: {grade_equiv}")
    if marzano_equiv:
        lines.append(
            f"Marzano '{marzano_level}' maps to {country.name} framework as: {marzano_equiv}"
        )
    if country.grading_notes:
        lines.append(f"System notes: {country.grading_notes}")

    return "\n".join(lines) + "\n"


def api_response() -> dict:
    """Structured API response for the frontend — v0.4.0 feature."""
    return {
        "status": "roadmap",
        "target_version": "0.4.0",
        "countries": {
            code: {
                "code": c.code,
                "name": c.name,
                "education_system": c.education_system,
                "curriculum_framework": c.curriculum_framework,
                "grade_terminology": c.grade_terminology,
                "compulsory_age_range": c.compulsory_age_range,
            }
            for code, c in COUNTRIES.items()
        },
        "grade_level_map": GRADE_LEVEL_MAP,
        "marzano_international": MARZANO_TO_INTERNATIONAL,
    }
