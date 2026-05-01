# Copyright (c) 2026 Paul Christopher Cerda
# This source code is licensed under the Business Source License 1.1
# found in the LICENSE.md file in the root directory of this source tree.

"""
US Core Curriculum Registry
Structured subject list organized by grade band.
Each entry carries Marzano competency targets, content strands,
and passion domain connections.

Grade bands follow standard US K-12 groupings.
To add subjects: copy an existing entry and adjust the fields.
To add international equivalencies: see international.py.
"""

from dataclasses import dataclass, field
from typing import Optional

# ─────────────────────────────────────────────────────────────
# Data structures
# ─────────────────────────────────────────────────────────────

@dataclass
class CurriculumSubject:
    name: str
    grade_band: str
    strands: list[str]
    marzano_entry_point: str        # lowest level expected for proficiency
    marzano_target: str             # level that demonstrates strong competency
    common_passions: list[str]      # passion domain keys from marzano_framework.py
    description: str
    typical_grade_levels: list[str] # e.g. ["Grade 9", "Grade 10"]
    standards_framework: str = "Common Core / NGSS"


@dataclass
class GradeBand:
    id: str
    label: str
    description: str
    typical_ages: str
    grade_levels: list[str]


# ─────────────────────────────────────────────────────────────
# Grade bands
# ─────────────────────────────────────────────────────────────

GRADE_BANDS: dict[str, GradeBand] = {
    "elementary_k2": GradeBand(
        id="elementary_k2",
        label="Early Elementary (K–2)",
        description="Foundational literacy, numeracy, and curiosity",
        typical_ages="5–8",
        grade_levels=["Kindergarten", "Grade 1", "Grade 2"],
    ),
    "elementary_3_5": GradeBand(
        id="elementary_3_5",
        label="Upper Elementary (3–5)",
        description="Building fluency, reasoning, and content knowledge",
        typical_ages="8–11",
        grade_levels=["Grade 3", "Grade 4", "Grade 5"],
    ),
    "middle_6_8": GradeBand(
        id="middle_6_8",
        label="Middle School (6–8)",
        description="Abstract reasoning, disciplinary thinking, identity",
        typical_ages="11–14",
        grade_levels=["Grade 6", "Grade 7", "Grade 8"],
    ),
    "high_9_10": GradeBand(
        id="high_9_10",
        label="High School Early (9–10)",
        description="Core disciplinary competencies and career readiness",
        typical_ages="14–16",
        grade_levels=["Grade 9", "Grade 10"],
    ),
    "high_11_12": GradeBand(
        id="high_11_12",
        label="High School Advanced (11–12)",
        description="Advanced coursework, AP, dual enrollment, graduation requirements",
        typical_ages="16–18",
        grade_levels=["Grade 11", "Grade 12"],
    ),
}


# ─────────────────────────────────────────────────────────────
# Subject registry
# ─────────────────────────────────────────────────────────────

SUBJECTS: list[CurriculumSubject] = [

    # ── MATHEMATICS ──────────────────────────────────────────

    CurriculumSubject(
        name="Early Number Sense",
        grade_band="elementary_k2",
        strands=["Counting & cardinality", "Operations & algebraic thinking",
                 "Number & operations in base 10", "Measurement & data", "Geometry"],
        marzano_entry_point="retrieval",
        marzano_target="comprehension",
        common_passions=["cooking", "music"],
        description="Foundational number concepts, counting, basic operations, shapes",
        typical_grade_levels=["Kindergarten", "Grade 1", "Grade 2"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Elementary Mathematics",
        grade_band="elementary_3_5",
        strands=["Operations & algebraic thinking", "Number & operations — fractions",
                 "Measurement & data", "Geometry", "Place value"],
        marzano_entry_point="retrieval",
        marzano_target="analysis",
        common_passions=["cooking", "architecture", "music", "photography"],
        description="Multiplication, fractions, area, perimeter, data analysis",
        typical_grade_levels=["Grade 3", "Grade 4", "Grade 5"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Pre-Algebra",
        grade_band="middle_6_8",
        strands=["Ratios & proportional relationships", "The number system",
                 "Expressions & equations", "Geometry", "Statistics & probability"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["architecture", "photography", "cooking", "music", "astronomy"],
        description="Ratios, proportions, negative numbers, expressions, basic geometry",
        typical_grade_levels=["Grade 6", "Grade 7"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Algebra I",
        grade_band="middle_6_8",
        strands=["Linear equations & inequalities", "Functions", "Statistics",
                 "Systems of equations", "Polynomials"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["architecture", "astronomy", "photography"],
        description="Linear functions, systems of equations, introduction to polynomials",
        typical_grade_levels=["Grade 8"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Algebra I",
        grade_band="high_9_10",
        strands=["Linear equations & inequalities", "Functions", "Statistics",
                 "Systems of equations", "Quadratic functions"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["architecture", "astronomy", "photography", "music"],
        description="Linear and quadratic functions, systems of equations, data analysis",
        typical_grade_levels=["Grade 9"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Geometry",
        grade_band="high_9_10",
        strands=["Congruence", "Similarity & right triangles", "Circles",
                 "Expressing geometric properties with equations",
                 "Modeling with geometry"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["architecture", "photography", "barrel_making"],
        description="Proof, transformations, similarity, trigonometry, coordinate geometry",
        typical_grade_levels=["Grade 9", "Grade 10"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Algebra II",
        grade_band="high_9_10",
        strands=["Polynomial functions", "Rational & radical functions",
                 "Exponential & logarithmic functions", "Trigonometric functions",
                 "Statistics & probability"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["music", "astronomy", "photography"],
        description="Advanced functions, logarithms, trigonometry, probability distributions",
        typical_grade_levels=["Grade 10", "Grade 11"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Pre-Calculus",
        grade_band="high_11_12",
        strands=["Functions & their graphs", "Polynomial & rational functions",
                 "Exponential & logarithmic functions", "Trigonometry",
                 "Analytic geometry", "Sequences & series"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["astronomy", "music", "architecture"],
        description="Preparation for calculus: advanced functions, trigonometry, limits concept",
        typical_grade_levels=["Grade 11"],
        standards_framework="Common Core State Standards — Mathematics",
    ),
    CurriculumSubject(
        name="Calculus AB / AP Calculus",
        grade_band="high_11_12",
        strands=["Limits & continuity", "Derivatives", "Applications of derivatives",
                 "Integrals", "Applications of integrals"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["astronomy", "architecture", "photography"],
        description="Differential and integral calculus, related rates, optimization",
        typical_grade_levels=["Grade 12"],
        standards_framework="AP College Board",
    ),
    CurriculumSubject(
        name="Statistics / AP Statistics",
        grade_band="high_11_12",
        strands=["Exploring data", "Sampling & experimentation",
                 "Probability & simulation", "Statistical inference"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["photography", "cooking", "astronomy"],
        description="Descriptive statistics, probability, inference, experimental design",
        typical_grade_levels=["Grade 11", "Grade 12"],
        standards_framework="AP College Board",
    ),

    # ── SCIENCE ──────────────────────────────────────────────

    CurriculumSubject(
        name="Early Science",
        grade_band="elementary_k2",
        strands=["Life science", "Earth & space science", "Physical science",
                 "Engineering design"],
        marzano_entry_point="retrieval",
        marzano_target="comprehension",
        common_passions=["cooking", "astronomy"],
        description="Observing, questioning, and exploring the natural world",
        typical_grade_levels=["Kindergarten", "Grade 1", "Grade 2"],
        standards_framework="NGSS — Next Generation Science Standards",
    ),
    CurriculumSubject(
        name="Elementary Science",
        grade_band="elementary_3_5",
        strands=["Life science", "Earth & space science", "Physical science",
                 "Engineering design"],
        marzano_entry_point="retrieval",
        marzano_target="analysis",
        common_passions=["astronomy", "cooking"],
        description="Matter, ecosystems, weather, forces, and simple engineering",
        typical_grade_levels=["Grade 3", "Grade 4", "Grade 5"],
        standards_framework="NGSS",
    ),
    CurriculumSubject(
        name="Life Science",
        grade_band="middle_6_8",
        strands=["Structure & function", "Growth & development", "Matter & energy in organisms",
                 "Interdependent relationships", "Natural selection", "Heredity"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["cooking", "photography"],
        description="Cells, ecosystems, genetics, evolution, human body systems",
        typical_grade_levels=["Grade 6"],
        standards_framework="NGSS",
    ),
    CurriculumSubject(
        name="Earth Science",
        grade_band="middle_6_8",
        strands=["Earth's systems", "Earth's history", "Earth & human activity",
                 "Space systems"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["astronomy", "photography"],
        description="Plate tectonics, weather, climate, rock cycle, solar system",
        typical_grade_levels=["Grade 7"],
        standards_framework="NGSS",
    ),
    CurriculumSubject(
        name="Physical Science",
        grade_band="middle_6_8",
        strands=["Matter & its interactions", "Motion & stability: forces",
                 "Energy", "Waves & information technologies"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["architecture", "music", "photography"],
        description="Matter, motion, forces, energy, waves, and electromagnetic radiation",
        typical_grade_levels=["Grade 8"],
        standards_framework="NGSS",
    ),
    CurriculumSubject(
        name="Biology",
        grade_band="high_9_10",
        strands=["Cell biology", "Genetics & heredity", "Evolution",
                 "Ecology", "Physiology"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["cooking", "photography"],
        description="Cell structure, DNA, heredity, natural selection, ecosystems",
        typical_grade_levels=["Grade 9", "Grade 10"],
        standards_framework="NGSS",
    ),
    CurriculumSubject(
        name="Chemistry",
        grade_band="high_9_10",
        strands=["Matter & atomic structure", "Chemical bonding",
                 "Chemical reactions", "Stoichiometry", "Thermodynamics"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["cooking", "barrel_making"],
        description="Atomic theory, periodic table, reactions, stoichiometry, solutions",
        typical_grade_levels=["Grade 10", "Grade 11"],
        standards_framework="NGSS",
    ),
    CurriculumSubject(
        name="Physics",
        grade_band="high_11_12",
        strands=["Mechanics", "Waves & sound", "Electricity & magnetism",
                 "Light & optics", "Modern physics"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["astronomy", "photography", "music", "architecture"],
        description="Motion, forces, energy, waves, electricity, and modern physics",
        typical_grade_levels=["Grade 11", "Grade 12"],
        standards_framework="NGSS",
    ),
    CurriculumSubject(
        name="Environmental Science / AP",
        grade_band="high_11_12",
        strands=["Earth systems", "Populations", "Land & water use",
                 "Energy resources", "Pollution", "Global change"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["astronomy", "photography", "cooking"],
        description="Ecosystem dynamics, human impact, sustainability, climate change",
        typical_grade_levels=["Grade 11", "Grade 12"],
        standards_framework="AP College Board / NGSS",
    ),

    # ── ENGLISH LANGUAGE ARTS ────────────────────────────────

    CurriculumSubject(
        name="Foundational Literacy",
        grade_band="elementary_k2",
        strands=["Phonics & phonological awareness", "Fluency",
                 "Vocabulary", "Comprehension", "Print concepts"],
        marzano_entry_point="retrieval",
        marzano_target="comprehension",
        common_passions=["music"],
        description="Decoding, sight words, reading fluency, and basic comprehension",
        typical_grade_levels=["Kindergarten", "Grade 1", "Grade 2"],
        standards_framework="Common Core State Standards — ELA",
    ),
    CurriculumSubject(
        name="Reading & Writing",
        grade_band="elementary_3_5",
        strands=["Reading literature", "Reading informational text",
                 "Writing", "Speaking & listening", "Language"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["photography", "music"],
        description="Reading comprehension, narrative and informational writing, vocabulary",
        typical_grade_levels=["Grade 3", "Grade 4", "Grade 5"],
        standards_framework="Common Core State Standards — ELA",
    ),
    CurriculumSubject(
        name="English Language Arts",
        grade_band="middle_6_8",
        strands=["Reading literature", "Reading informational text",
                 "Argument & evidence", "Narrative writing", "Research"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["photography", "music"],
        description="Literary analysis, argument writing, research skills, grammar",
        typical_grade_levels=["Grade 6", "Grade 7", "Grade 8"],
        standards_framework="Common Core State Standards — ELA",
    ),
    CurriculumSubject(
        name="English 9 / 10",
        grade_band="high_9_10",
        strands=["Literary analysis", "Argument & rhetoric",
                 "Research writing", "Speaking & presenting", "Language conventions"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["photography", "music"],
        description="Analysis of literature, argumentative writing, research methodology",
        typical_grade_levels=["Grade 9", "Grade 10"],
        standards_framework="Common Core State Standards — ELA",
    ),
    CurriculumSubject(
        name="AP Language & Composition",
        grade_band="high_11_12",
        strands=["Rhetorical analysis", "Argumentation",
                 "Synthesis writing", "Multimodal texts"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["photography", "music"],
        description="Rhetoric, argument, synthesis; preparation for college writing",
        typical_grade_levels=["Grade 11"],
        standards_framework="AP College Board",
    ),
    CurriculumSubject(
        name="AP Literature & Composition",
        grade_band="high_11_12",
        strands=["Poetry analysis", "Fiction & drama analysis",
                 "Literary criticism", "Creative & analytical writing"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["music", "photography"],
        description="Deep literary analysis, critical theory, long-form essay writing",
        typical_grade_levels=["Grade 12"],
        standards_framework="AP College Board",
    ),

    # ── SOCIAL STUDIES ───────────────────────────────────────

    CurriculumSubject(
        name="Community & Society",
        grade_band="elementary_k2",
        strands=["Civics", "Geography basics", "History & culture", "Economics basics"],
        marzano_entry_point="retrieval",
        marzano_target="comprehension",
        common_passions=["cooking"],
        description="Family, community, rules, maps, and national symbols",
        typical_grade_levels=["Kindergarten", "Grade 1", "Grade 2"],
        standards_framework="C3 Framework for Social Studies",
    ),
    CurriculumSubject(
        name="Geography & US History",
        grade_band="elementary_3_5",
        strands=["US history", "World geography", "Economics", "Civics & government"],
        marzano_entry_point="retrieval",
        marzano_target="analysis",
        common_passions=["photography", "astronomy"],
        description="American history, world geography, map skills, economic concepts",
        typical_grade_levels=["Grade 3", "Grade 4", "Grade 5"],
        standards_framework="C3 Framework",
    ),
    CurriculumSubject(
        name="World History & Geography",
        grade_band="middle_6_8",
        strands=["Ancient civilizations", "Medieval & early modern",
                 "Colonialism & revolution", "Geography", "Cultural comparison"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["photography", "cooking", "architecture"],
        description="Ancient to modern world history, comparative cultures, geography",
        typical_grade_levels=["Grade 6", "Grade 7"],
        standards_framework="C3 Framework",
    ),
    CurriculumSubject(
        name="US History",
        grade_band="middle_6_8",
        strands=["Colonial era", "Revolution & founding", "Civil War & Reconstruction",
                 "Industrial era", "20th century"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["photography", "architecture"],
        description="American history from colonization through the 20th century",
        typical_grade_levels=["Grade 8"],
        standards_framework="C3 Framework",
    ),
    CurriculumSubject(
        name="World History",
        grade_band="high_9_10",
        strands=["Ancient civilizations", "Medieval world", "Age of exploration",
                 "Industrial revolution", "World wars", "Contemporary world"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["photography", "architecture"],
        description="Global history from ancient to contemporary, cause & effect, primary sources",
        typical_grade_levels=["Grade 9", "Grade 10"],
        standards_framework="C3 Framework",
    ),
    CurriculumSubject(
        name="US History",
        grade_band="high_9_10",
        strands=["Founding era", "Expansion & conflict", "Gilded Age",
                 "20th century", "Civil rights & social movements"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["photography", "architecture"],
        description="American history with emphasis on primary sources and historical argumentation",
        typical_grade_levels=["Grade 10", "Grade 11"],
        standards_framework="C3 Framework",
    ),
    CurriculumSubject(
        name="Government & Civics / AP",
        grade_band="high_11_12",
        strands=["Constitutional foundations", "Branches of government",
                 "Civil liberties & rights", "Political participation",
                 "Comparative government"],
        marzano_entry_point="analysis",
        marzano_target="knowledge_utilization",
        common_passions=["photography"],
        description="Constitutional democracy, political institutions, civic participation",
        typical_grade_levels=["Grade 12"],
        standards_framework="C3 Framework / AP College Board",
    ),
    CurriculumSubject(
        name="Economics / AP",
        grade_band="high_11_12",
        strands=["Microeconomics", "Macroeconomics", "International economics",
                 "Personal finance", "Economic reasoning"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["cooking", "architecture"],
        description="Supply & demand, markets, GDP, monetary policy, personal finance",
        typical_grade_levels=["Grade 11", "Grade 12"],
        standards_framework="C3 Framework / AP College Board",
    ),

    # ── ARTS & ELECTIVES ─────────────────────────────────────

    CurriculumSubject(
        name="Visual Arts",
        grade_band="middle_6_8",
        strands=["Elements of art", "Design principles", "Media & techniques",
                 "Art history & culture", "Critique & reflection"],
        marzano_entry_point="comprehension",
        marzano_target="analysis",
        common_passions=["photography", "architecture"],
        description="Drawing, painting, design, art history, and visual analysis",
        typical_grade_levels=["Grade 6", "Grade 7", "Grade 8"],
        standards_framework="National Core Arts Standards",
    ),
    CurriculumSubject(
        name="Music",
        grade_band="middle_6_8",
        strands=["Music theory", "Performance", "Composition",
                 "Music history", "Listening & analysis"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["music", "mathematics"],
        description="Music theory, performance skills, composition, and historical context",
        typical_grade_levels=["Grade 6", "Grade 7", "Grade 8"],
        standards_framework="National Core Arts Standards",
    ),
    CurriculumSubject(
        name="Computer Science",
        grade_band="high_9_10",
        strands=["Computational thinking", "Programming & algorithms",
                 "Data & analysis", "Networks & cybersecurity", "Impacts of computing"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["photography", "music", "architecture"],
        description="Programming, algorithms, data structures, and computational thinking",
        typical_grade_levels=["Grade 9", "Grade 10"],
        standards_framework="K-12 CS Framework / CSTA Standards",
    ),
    CurriculumSubject(
        name="Photography & Digital Media",
        grade_band="high_9_10",
        strands=["Camera technique", "Composition", "Lighting",
                 "Digital editing", "Visual communication"],
        marzano_entry_point="comprehension",
        marzano_target="knowledge_utilization",
        common_passions=["photography", "architecture"],
        description="Camera operation, composition, digital editing, and visual storytelling",
        typical_grade_levels=["Grade 9", "Grade 10"],
        standards_framework="National Core Arts Standards",
    ),
]


# ─────────────────────────────────────────────────────────────
# Lookup helpers
# ─────────────────────────────────────────────────────────────

def get_subjects_for_band(grade_band: str) -> list[CurriculumSubject]:
    """Return all subjects available for a given grade band."""
    return [s for s in SUBJECTS if s.grade_band == grade_band]


def get_subject(grade_band: str, name: str) -> Optional[CurriculumSubject]:
    """Look up a specific subject by band and name."""
    for s in SUBJECTS:
        if s.grade_band == grade_band and s.name == name:
            return s
    return None


def build_curriculum_context(grade_band: str, subject_name: str) -> str:
    """
    Build a structured context string for injection into the AI system prompt.
    Includes strands, competency targets, and standards framework.
    """
    subject = get_subject(grade_band, subject_name)
    if not subject:
        return ""
    band = GRADE_BANDS.get(grade_band)
    band_label = band.label if band else grade_band

    return (
        f"\nCURRICULUM CONTEXT:\n"
        f"Grade band: {band_label}\n"
        f"Subject: {subject.name}\n"
        f"Content strands: {', '.join(subject.strands)}\n"
        f"Minimum Marzano level expected: {subject.marzano_entry_point.replace('_', ' ').title()}\n"
        f"Target Marzano level for strong competency: {subject.marzano_target.replace('_', ' ').title()}\n"
        f"Standards framework: {subject.standards_framework}\n"
        f"Description: {subject.description}\n"
    )


def grade_band_for_level(grade_level: str) -> str:
    """Infer grade band from a grade level string (most-specific match first)."""
    level = grade_level.lower().strip()
    # Check higher grades first to avoid "grade 1" matching "grade 12"
    if any(level == g.lower() for g in ["Grade 11", "Grade 12"]):
        return "high_11_12"
    if any(level == g.lower() for g in ["Grade 9", "Grade 10"]):
        return "high_9_10"
    if any(level == g.lower() for g in ["Grade 6", "Grade 7", "Grade 8"]):
        return "middle_6_8"
    if any(level == g.lower() for g in ["Grade 3", "Grade 4", "Grade 5"]):
        return "elementary_3_5"
    if any(level == g.lower() for g in ["Kindergarten", "Grade 1", "Grade 2"]):
        return "elementary_k2"
    # Fuzzy fallback for partial strings
    if "11" in level or "12" in level:
        return "high_11_12"
    if "9" in level or "10" in level:
        return "high_9_10"
    if "6" in level or "7" in level or "8" in level:
        return "middle_6_8"
    if "3" in level or "4" in level or "5" in level:
        return "elementary_3_5"
    return "high_9_10"  # default


def api_response() -> dict:
    """Full curriculum data formatted for the frontend API."""
    return {
        "grade_bands": {
            bid: {
                "id": b.id,
                "label": b.label,
                "description": b.description,
                "typical_ages": b.typical_ages,
                "grade_levels": b.grade_levels,
            }
            for bid, b in GRADE_BANDS.items()
        },
        "subjects": {
            band_id: [
                {
                    "name": s.name,
                    "strands": s.strands,
                    "marzano_entry_point": s.marzano_entry_point,
                    "marzano_target": s.marzano_target,
                    "common_passions": s.common_passions,
                    "description": s.description,
                    "typical_grade_levels": s.typical_grade_levels,
                    "standards_framework": s.standards_framework,
                }
                for s in get_subjects_for_band(band_id)
            ]
            for band_id in GRADE_BANDS
        },
    }
