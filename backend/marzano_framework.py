"""
Marzano's New Taxonomy Framework
Core definitions used to build prompts and parse AI feedback.
"""

from dataclasses import dataclass, field
from typing import List, Dict


@dataclass
class MarzanoSubLevel:
    name: str
    description: str
    verbs: List[str]
    question_stems: List[str]
    student_indicators: List[str]  # what to look for in student work


@dataclass
class MarzanoLevel:
    id: str
    name: str
    description: str
    sublevels: List[MarzanoSubLevel]
    bloom_equivalent: str = ""


TAXONOMY = {
    "self_system": MarzanoLevel(
        id="self_system",
        name="Self System",
        description=(
            "The self system decides whether to engage with a new task. "
            "It examines importance, efficacy, emotional response, and motivation. "
            "This system fires FIRST before any cognitive processing begins."
        ),
        sublevels=[
            MarzanoSubLevel(
                name="Examining Importance",
                description="Student evaluates why the task matters to them personally",
                verbs=["value", "prioritize", "connect", "relate", "justify importance"],
                question_stems=[
                    "How important is this to you and why?",
                    "How does this connect to your goals?",
                    "Why might this knowledge matter beyond school?",
                ],
                student_indicators=[
                    "Student makes explicit connections to personal goals",
                    "Student articulates real-world relevance",
                    "Student questions provided with personal framing",
                ],
            ),
            MarzanoSubLevel(
                name="Examining Efficacy",
                description="Student assesses their own capability to succeed at the task",
                verbs=["assess ability", "reflect confidence", "self-evaluate", "gauge readiness"],
                question_stems=[
                    "How confident are you in your ability to do this?",
                    "What prior knowledge supports your approach?",
                    "Where do you anticipate difficulty?",
                ],
                student_indicators=[
                    "Student identifies prior knowledge applied",
                    "Student acknowledges limitations and seeks help",
                    "Student adjusts approach based on difficulty",
                ],
            ),
            MarzanoSubLevel(
                name="Examining Emotional Response",
                description="Student recognizes how feelings affect engagement",
                verbs=["reflect", "acknowledge feelings", "manage affect", "express interest"],
                question_stems=[
                    "What drew you to this particular project?",
                    "How did your interest evolve while working on this?",
                    "What frustrated or excited you and how did you respond?",
                ],
                student_indicators=[
                    "Student chose a passion-driven topic",
                    "Evidence of sustained engagement despite difficulty",
                    "Student reflects on emotional experience in work",
                ],
            ),
            MarzanoSubLevel(
                name="Examining Overall Motivation",
                description="Synthesis of importance, efficacy, and emotional response",
                verbs=["motivate", "persist", "sustain engagement", "self-direct"],
                question_stems=[
                    "What kept you going when this got hard?",
                    "How did your motivation change through the project?",
                ],
                student_indicators=[
                    "Project shows sustained effort over time",
                    "Evidence of iteration and revision",
                    "Student sought additional resources independently",
                ],
            ),
        ],
    ),

    "metacognitive": MarzanoLevel(
        id="metacognitive",
        name="Metacognitive System",
        description=(
            "The metacognitive system sets goals, monitors progress, and regulates thinking. "
            "It is the 'mission control' that directs cognitive resources. "
            "This system fires SECOND, after the self system decides to engage."
        ),
        sublevels=[
            MarzanoSubLevel(
                name="Goal Specification",
                description="Student sets clear, actionable learning goals",
                verbs=["plan", "set goals", "specify objectives", "define success criteria"],
                question_stems=[
                    "What did you intend to learn or demonstrate?",
                    "How did you define success for this project?",
                    "What was your plan before you started?",
                ],
                student_indicators=[
                    "Explicit statement of learning goals in work",
                    "Evidence of planning (drafts, outlines, notes)",
                    "Project scope matches stated intentions",
                ],
            ),
            MarzanoSubLevel(
                name="Process Monitoring",
                description="Student tracks their own progress and adjusts strategies",
                verbs=["monitor", "track", "adjust", "reflect on process", "evaluate strategy"],
                question_stems=[
                    "How did you know when your approach wasn't working?",
                    "What did you change mid-project and why?",
                    "How did you check your own understanding?",
                ],
                student_indicators=[
                    "Evidence of revision and iteration in artifacts",
                    "Student identifies pivot points in their process",
                    "Multiple drafts or versions present",
                ],
            ),
            MarzanoSubLevel(
                name="Monitoring Clarity",
                description="Student identifies gaps in their own understanding",
                verbs=["clarify", "question", "identify confusion", "seek understanding"],
                question_stems=[
                    "Where were you unclear or confused?",
                    "What questions did you need to answer to proceed?",
                    "What would you need to learn next?",
                ],
                student_indicators=[
                    "Student explicitly flags uncertainty",
                    "Evidence of research to resolve confusion",
                    "Questions embedded in reflection notes",
                ],
            ),
            MarzanoSubLevel(
                name="Monitoring Accuracy",
                description="Student verifies correctness of their work",
                verbs=["verify", "check", "validate", "error-check", "confirm"],
                question_stems=[
                    "How did you verify your results are correct?",
                    "What did you do when you found a mistake?",
                    "How confident are you in your accuracy?",
                ],
                student_indicators=[
                    "Calculations checked or cross-validated",
                    "Sources cited to support claims",
                    "Student acknowledges and corrects errors",
                ],
            ),
        ],
    ),

    "retrieval": MarzanoLevel(
        id="retrieval",
        name="Cognitive: Retrieval",
        description=(
            "The lowest level of the cognitive system. Student activates and transfers "
            "knowledge from permanent memory to working memory. Often automatic."
        ),
        bloom_equivalent="Remember",
        sublevels=[
            MarzanoSubLevel(
                name="Recognizing",
                description="Validates accuracy of information when presented",
                verbs=["identify", "match", "select", "recognize", "choose"],
                question_stems=[
                    "Which of the following is accurate?",
                    "Can you identify the correct formula here?",
                    "Which diagram matches the concept?",
                ],
                student_indicators=[
                    "Correct use of terminology",
                    "Accurate labeling of components",
                    "Correct matching of concepts to examples",
                ],
            ),
            MarzanoSubLevel(
                name="Recalling",
                description="Produces accurate information from memory on demand",
                verbs=["name", "list", "state", "define", "describe", "recall"],
                question_stems=[
                    "What is the formula for...?",
                    "Define the key terms used here.",
                    "List the steps in the process.",
                ],
                student_indicators=[
                    "Definitions stated accurately",
                    "Formulas applied correctly",
                    "Key facts present without error",
                ],
            ),
            MarzanoSubLevel(
                name="Executing",
                description="Carries out a known procedure without significant error",
                verbs=["calculate", "apply", "demonstrate", "perform", "solve", "use"],
                question_stems=[
                    "Show each step of the calculation.",
                    "Demonstrate the procedure.",
                    "Execute the algorithm correctly.",
                ],
                student_indicators=[
                    "Procedure followed in correct sequence",
                    "Arithmetic / operations accurate",
                    "No significant procedural errors",
                ],
            ),
        ],
    ),

    "comprehension": MarzanoLevel(
        id="comprehension",
        name="Cognitive: Comprehension",
        description=(
            "Student identifies the critical or defining attributes of knowledge, "
            "distinguishing essential from non-essential elements."
        ),
        bloom_equivalent="Understand",
        sublevels=[
            MarzanoSubLevel(
                name="Integrating",
                description="Articulates critical vs non-critical elements; paraphrases",
                verbs=["summarize", "paraphrase", "explain", "describe key parts", "interpret"],
                question_stems=[
                    "Explain how this works in your own words.",
                    "What are the most important elements and why?",
                    "Describe the relationship between these components.",
                ],
                student_indicators=[
                    "Explanation goes beyond restatement",
                    "Student identifies what matters vs what doesn't",
                    "Paraphrasing reflects genuine understanding",
                ],
            ),
            MarzanoSubLevel(
                name="Symbolizing",
                description="Depicts critical elements in non-linguistic or abstract form",
                verbs=["diagram", "illustrate", "model", "chart", "represent", "visualize"],
                question_stems=[
                    "Create a diagram showing how the parts relate.",
                    "Draw or model what this looks like.",
                    "Represent this concept visually.",
                ],
                student_indicators=[
                    "Diagram captures the essential relationships",
                    "Visual representation is accurate",
                    "Non-linguistic form communicates understanding",
                ],
            ),
        ],
    ),

    "analysis": MarzanoLevel(
        id="analysis",
        name="Cognitive: Analysis",
        description=(
            "Reasoned extensions of knowledge and generation of new information "
            "not already processed. Student goes beyond what was taught."
        ),
        bloom_equivalent="Analyze / Evaluate",
        sublevels=[
            MarzanoSubLevel(
                name="Matching",
                description="Identifies similarities and differences",
                verbs=["compare", "contrast", "differentiate", "relate", "create analogy"],
                question_stems=[
                    "How is this similar to or different from...?",
                    "Create an analogy for this concept.",
                    "What patterns do you see across these examples?",
                ],
                student_indicators=[
                    "Explicit comparison with specific evidence",
                    "Analogy captures essential relationship",
                    "Nuanced treatment of differences",
                ],
            ),
            MarzanoSubLevel(
                name="Classifying",
                description="Identifies superordinate and subordinate categories",
                verbs=["classify", "organize", "categorize", "group", "rank"],
                question_stems=[
                    "How would you group or classify these?",
                    "What broader category does this belong to?",
                    "What distinguishes these types from each other?",
                ],
                student_indicators=[
                    "Categories are principled, not arbitrary",
                    "Student can justify classification decisions",
                    "Hierarchy is logically consistent",
                ],
            ),
            MarzanoSubLevel(
                name="Analyzing Errors",
                description="Identifies logical or processing errors in knowledge",
                verbs=["critique", "evaluate", "identify errors", "diagnose", "revise"],
                question_stems=[
                    "What errors or problems do you see in this approach?",
                    "How would you improve or correct this?",
                    "What assumptions are flawed here?",
                ],
                student_indicators=[
                    "Student identifies and corrects their own errors",
                    "Critique is substantiated with reasoning",
                    "Student challenges given information with evidence",
                ],
            ),
            MarzanoSubLevel(
                name="Generalizing",
                description="Infers new generalizations from known information",
                verbs=["generalize", "infer", "conclude", "form a principle", "identify patterns"],
                question_stems=[
                    "What general rule can you derive from this?",
                    "What conclusion follows from your data?",
                    "What would this imply about similar cases?",
                ],
                student_indicators=[
                    "Generalization is supported by evidence",
                    "Student moves from specific to general",
                    "Principle is accurately stated",
                ],
            ),
            MarzanoSubLevel(
                name="Specifying",
                description="Makes and defends predictions about specific situations",
                verbs=["predict", "deduce", "specify", "develop argument", "defend claim"],
                question_stems=[
                    "What do you predict would happen if...?",
                    "Under what conditions would this not hold?",
                    "Defend your prediction with reasoning.",
                ],
                student_indicators=[
                    "Prediction is grounded in established principle",
                    "Student defends with logical argument",
                    "Conditions and constraints are acknowledged",
                ],
            ),
        ],
    ),

    "knowledge_utilization": MarzanoLevel(
        id="knowledge_utilization",
        name="Cognitive: Knowledge Utilization",
        description=(
            "The highest and most complex cognitive level. Application of knowledge "
            "to accomplish a specific task. Unique to Marzano's taxonomy — "
            "no direct equivalent exists in Bloom's."
        ),
        bloom_equivalent="Create (partial)",
        sublevels=[
            MarzanoSubLevel(
                name="Decision Making",
                description="Selects among alternatives that initially appear equal",
                verbs=["decide", "select best", "choose", "determine best way", "evaluate alternatives"],
                question_stems=[
                    "What criteria did you use to choose this approach?",
                    "What alternatives did you consider and reject?",
                    "How did you determine this was the best option?",
                ],
                student_indicators=[
                    "Multiple alternatives were genuinely considered",
                    "Decision criteria are explicit",
                    "Choice is defended with evidence",
                ],
            ),
            MarzanoSubLevel(
                name="Problem Solving",
                description="Overcomes a real obstacle to achieve a goal",
                verbs=["solve", "overcome", "adapt", "develop strategy", "figure out how to"],
                question_stems=[
                    "What obstacles did you encounter and how did you overcome them?",
                    "What was your strategy when you hit a dead end?",
                    "How did you verify your solution actually works?",
                ],
                student_indicators=[
                    "Genuine problem encountered (not scripted)",
                    "Multiple solution attempts evident",
                    "Solution verified against requirements",
                ],
            ),
            MarzanoSubLevel(
                name="Experimenting",
                description="Generates and tests hypotheses about phenomena",
                verbs=["experiment", "hypothesize", "test", "generate and test", "simulate"],
                question_stems=[
                    "What hypothesis were you testing?",
                    "What did you predict before running the test?",
                    "How did your results confirm or challenge your hypothesis?",
                ],
                student_indicators=[
                    "Hypothesis stated before testing",
                    "Controlled variables identified",
                    "Results interpreted against hypothesis",
                ],
            ),
            MarzanoSubLevel(
                name="Investigating",
                description="Examines past, present, or future situations using evidence",
                verbs=["investigate", "research", "take a position", "find out about", "prove"],
                question_stems=[
                    "What position are you taking and what evidence supports it?",
                    "How did you evaluate the quality of your sources?",
                    "What counterarguments did you consider?",
                ],
                student_indicators=[
                    "Multiple sources evaluated",
                    "Position supported with evidence",
                    "Counterarguments acknowledged",
                ],
            ),
        ],
    ),
}

# Passion-to-math-concept mapping for personalized learning
PASSION_MATH_CONNECTIONS = {
    "architecture": {
        "concepts": ["geometry", "ratios", "structural load", "area", "volume", "trigonometry"],
        "marzano_entry_point": "knowledge_utilization",
        "sample_prompt": "Design an arch structure and calculate the forces involved",
    },
    "astronomy": {
        "concepts": ["scientific notation", "distance", "scale", "gravity", "orbital mechanics"],
        "marzano_entry_point": "analysis",
        "sample_prompt": "Calculate scale distances in the solar system and model planetary motion",
    },
    "barrel_making": {
        "concepts": ["volume", "surface area", "geometry", "ratios", "wood properties"],
        "marzano_entry_point": "comprehension",
        "sample_prompt": "Design a barrel of a given volume and calculate the wood required",
    },
    "photography": {
        "concepts": ["ratios", "light", "geometry", "depth of field", "trigonometry", "fractions"],
        "marzano_entry_point": "analysis",
        "sample_prompt": "Explore how aperture, focal length, and distance create depth of field",
    },
    "music": {
        "concepts": ["fractions", "ratios", "frequency", "patterns", "geometry"],
        "marzano_entry_point": "matching",
        "sample_prompt": "Analyze time signatures and frequency ratios in musical intervals",
    },
    "cooking": {
        "concepts": ["ratios", "fractions", "measurement", "scaling", "chemistry"],
        "marzano_entry_point": "retrieval",
        "sample_prompt": "Scale a recipe and analyze the math behind baking chemistry",
    },
}


def build_system_prompt(subject: str, student_passion: str, grade_level: str) -> str:
    """Build the system prompt that instructs the AI to think in Marzano terms."""
    passion_context = PASSION_MATH_CONNECTIONS.get(
        student_passion.lower(), 
        {"concepts": [subject], "marzano_entry_point": "comprehension"}
    )

    return f"""You are an expert educational assessor trained in Marzano's New Taxonomy of Educational Objectives.

Your task is to evaluate student work and generate structured feedback that:
1. EXPLICITLY cites the specific Marzano taxonomy level and sublevel being assessed
2. Provides evidence-based feedback tied to student artifacts
3. Distinguishes between the three systems (Self System, Metacognitive System, Cognitive System)
4. Identifies the highest demonstrated level of thinking
5. Suggests next steps that push the student to the next taxonomy level

CONTEXT:
- Subject: {subject}
- Student passion/interest: {student_passion}
- Grade level: {grade_level}
- Relevant math concepts: {', '.join(passion_context.get('concepts', []))}

MARZANO TAXONOMY REMINDER:
The systems engage in order: Self System → Metacognitive → Cognitive (Retrieval → Comprehension → Analysis → Knowledge Utilization)

RESPONSE FORMAT:
You must return a JSON object with this exact structure:
{{
  "overall_level": "<highest Marzano level demonstrated>",
  "overall_sublevel": "<specific sublevel>",
  "strength_summary": "<2-3 sentences on what the student did well>",
  "growth_summary": "<2-3 sentences on areas for growth>",
  "taxonomy_breakdown": [
    {{
      "system": "<Self System | Metacognitive System | Cognitive System>",
      "level": "<level name>",
      "sublevel": "<sublevel name>",
      "evidence": "<direct reference to student work>",
      "rating": "<not demonstrated | emerging | developing | proficient | advanced>",
      "teacher_note": ""
    }}
  ],
  "next_level_prompt": "<specific question or challenge to push student to next level>",
  "standards_connections": ["<list of curriculum standards this work addresses>"],
  "passion_integration": "<how well the student's passion was leveraged for learning>",
  "ai_reasoning": "<explain your assessment reasoning for teacher transparency>"
}}

Be specific. Cite actual details from the student's work. Never give generic praise.
"""


def build_artifact_prompt(artifact_description: str, student_reflection: str) -> str:
    """Build the user-turn prompt for assessing a specific artifact."""
    return f"""Please assess the following student work using Marzano's New Taxonomy.

STUDENT ARTIFACT:
{artifact_description}

STUDENT REFLECTION / NOTES:
{student_reflection if student_reflection else "No reflection provided."}

Evaluate across all applicable Marzano levels. For each level where you see evidence, 
cite the specific part of the student's work that demonstrates it.
Return the JSON assessment as specified."""
