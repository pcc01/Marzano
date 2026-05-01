# Copyright (c) 2026 Paul Christopher Cerda
# This source code is licensed under the Business Source License 1.1
# found in the LICENSE.md file in the root directory of this source tree.

"""
Unit tests — marzano_framework.py
Tests taxonomy completeness, prompt generation, and JSON extraction.
"""

import json
import pytest
from marzano_framework import (
    TAXONOMY,
    PASSION_MATH_CONNECTIONS,
    build_system_prompt,
    build_artifact_prompt,
)


class TestTaxonomyStructure:
    """Marzano taxonomy must have all expected levels and sublevels."""

    EXPECTED_LEVELS = {
        "self_system", "metacognitive", "retrieval",
        "comprehension", "analysis", "knowledge_utilization",
    }

    EXPECTED_SUBLEVELS = {
        "self_system": {"Examining Importance", "Examining Efficacy",
                        "Examining Emotional Response", "Examining Overall Motivation"},
        "metacognitive": {"Goal Specification", "Process Monitoring",
                          "Monitoring Clarity", "Monitoring Accuracy"},
        "retrieval": {"Recognizing", "Recalling", "Executing"},
        "comprehension": {"Integrating", "Symbolizing"},
        "analysis": {"Matching", "Classifying", "Analyzing Errors",
                     "Generalizing", "Specifying"},
        "knowledge_utilization": {"Decision Making", "Problem Solving",
                                   "Experimenting", "Investigating"},
    }

    def test_all_levels_present(self):
        assert set(TAXONOMY.keys()) == self.EXPECTED_LEVELS

    def test_each_level_has_sublevels(self):
        for level_id, level in TAXONOMY.items():
            assert len(level.sublevels) > 0, f"{level_id} has no sublevels"

    def test_sublevels_match_expected(self):
        for level_id, expected_names in self.EXPECTED_SUBLEVELS.items():
            level = TAXONOMY[level_id]
            actual_names = {s.name for s in level.sublevels}
            assert actual_names == expected_names, (
                f"{level_id}: expected {expected_names}, got {actual_names}"
            )

    def test_every_sublevel_has_verbs(self):
        for level_id, level in TAXONOMY.items():
            for sub in level.sublevels:
                assert sub.verbs, f"{level_id}/{sub.name} has no verbs"
                assert len(sub.verbs) >= 3, f"{level_id}/{sub.name} has fewer than 3 verbs"

    def test_every_sublevel_has_question_stems(self):
        for level_id, level in TAXONOMY.items():
            for sub in level.sublevels:
                assert sub.question_stems, f"{level_id}/{sub.name} has no question stems"

    def test_every_sublevel_has_student_indicators(self):
        for level_id, level in TAXONOMY.items():
            for sub in level.sublevels:
                assert sub.student_indicators, f"{level_id}/{sub.name} has no student indicators"

    def test_levels_have_descriptions(self):
        for level_id, level in TAXONOMY.items():
            assert level.description, f"{level_id} has no description"
            assert len(level.description) > 20, f"{level_id} description too short"

    def test_cognitive_levels_have_bloom_equivalent(self):
        cognitive_levels = {"retrieval", "comprehension", "analysis", "knowledge_utilization"}
        for level_id in cognitive_levels:
            level = TAXONOMY[level_id]
            assert hasattr(level, "bloom_equivalent"), f"{level_id} missing bloom_equivalent"
            assert level.bloom_equivalent, f"{level_id} bloom_equivalent is empty"

    def test_self_and_meta_have_no_bloom(self):
        """Self and metacognitive systems are unique to Marzano — no Bloom equivalent."""
        for level_id in ("self_system", "metacognitive"):
            level = TAXONOMY[level_id]
            bloom = getattr(level, "bloom_equivalent", "")
            assert bloom == "", f"{level_id} should not have bloom_equivalent"


class TestPassionMapping:
    """Passion-to-curriculum mapping completeness."""

    EXPECTED_PASSIONS = {
        "architecture", "astronomy", "barrel_making",
        "photography", "music", "cooking",
    }

    def test_all_passions_present(self):
        assert self.EXPECTED_PASSIONS.issubset(set(PASSION_MATH_CONNECTIONS.keys()))

    def test_each_passion_has_concepts(self):
        for passion, data in PASSION_MATH_CONNECTIONS.items():
            assert "concepts" in data, f"{passion} missing 'concepts'"
            assert len(data["concepts"]) >= 2, f"{passion} has fewer than 2 concepts"

    def test_each_passion_has_marzano_entry(self):
        for passion, data in PASSION_MATH_CONNECTIONS.items():
            assert "marzano_entry_point" in data, f"{passion} missing marzano_entry_point"
            entry = data["marzano_entry_point"]
            # Entry point may be a top-level taxonomy key OR a sublevel name (lowercase)
            valid_top = set(TAXONOMY.keys())
            valid_sub = {
                sub.name.lower().replace(" ", "_")
                for level in TAXONOMY.values()
                for sub in level.sublevels
            }
            valid_all = valid_top | valid_sub
            assert entry in valid_all or any(entry in k for k in valid_all), \
                f"{passion} entry_point '{entry}' not a recognised taxonomy term"


class TestPromptGeneration:
    """build_system_prompt and build_artifact_prompt correctness."""

    def test_system_prompt_contains_subject(self):
        prompt = build_system_prompt("Mathematics", "photography", "Grade 10")
        assert "Mathematics" in prompt

    def test_system_prompt_contains_passion(self):
        prompt = build_system_prompt("Mathematics", "photography", "Grade 10")
        assert "photography" in prompt

    def test_system_prompt_contains_grade(self):
        prompt = build_system_prompt("Mathematics", "photography", "Grade 10")
        assert "Grade 10" in prompt

    def test_system_prompt_references_all_three_systems(self):
        prompt = build_system_prompt("Science", "astronomy", "Grade 8")
        assert "Self System" in prompt or "self system" in prompt.lower()
        assert "Metacognitive" in prompt or "metacognitive" in prompt.lower()
        assert "Cognitive" in prompt or "cognitive" in prompt.lower()

    def test_system_prompt_requests_json(self):
        prompt = build_system_prompt("Science", "astronomy", "Grade 8")
        assert "JSON" in prompt or "json" in prompt.lower()

    def test_system_prompt_with_state(self):
        prompt = build_system_prompt("Mathematics", "architecture", "Grade 9", state="California")
        assert "California" in prompt
        assert "standard" in prompt.lower()

    def test_system_prompt_with_curriculum_context(self):
        ctx = "\nCURRICULUM CONTEXT:\nSubject: Geometry\n"
        prompt = build_system_prompt("Mathematics", "architecture", "Grade 9",
                                     curriculum_context=ctx)
        assert "Geometry" in prompt

    def test_system_prompt_specifies_json_fields(self):
        prompt = build_system_prompt("ELA", "music", "Grade 11")
        required_fields = [
            "overall_level", "strength_summary", "growth_summary",
            "taxonomy_breakdown", "next_level_prompt", "ai_reasoning",
        ]
        for field in required_fields:
            assert field in prompt, f"JSON field '{field}' missing from system prompt"

    def test_artifact_prompt_contains_description(self):
        desc = "Student built a scale model of the solar system"
        prompt = build_artifact_prompt(desc, "")
        assert "solar system" in prompt

    def test_artifact_prompt_includes_reflection_when_provided(self):
        desc = "Photography depth-of-field project"
        reflection = "I learned that aperture controls what is in focus"
        prompt = build_artifact_prompt(desc, reflection)
        assert "aperture" in prompt

    def test_artifact_prompt_handles_empty_reflection(self):
        prompt = build_artifact_prompt("Some artifact", "")
        assert "No reflection provided" in prompt or "No reflection" in prompt

    def test_system_prompt_returns_string(self):
        result = build_system_prompt("Math", "cooking", "Grade 6")
        assert isinstance(result, str)
        assert len(result) > 500  # substantive prompt


class TestJsonExtraction:
    """Validate the JSON extraction helper that parses AI responses."""

    def _extract(self, text):
        """Mirror the _extract_json logic from main.py."""
        text = text.strip()
        for fence in ["```json", "```"]:
            if fence in text:
                text = text.split(fence, 1)[-1].rsplit("```", 1)[0]
                break
        try:
            start = text.index("{")
            end = text.rindex("}") + 1
            return json.loads(text[start:end])
        except (ValueError, json.JSONDecodeError):
            return None

    def test_plain_json(self):
        raw = '{"overall_level": "Analysis", "strength_summary": "Good work"}'
        result = self._extract(raw)
        assert result is not None
        assert result["overall_level"] == "Analysis"

    def test_json_in_markdown_fence(self):
        raw = '```json\n{"overall_level": "Comprehension"}\n```'
        result = self._extract(raw)
        assert result is not None
        assert result["overall_level"] == "Comprehension"

    def test_json_with_leading_text(self):
        raw = 'Here is my assessment:\n{"overall_level": "Retrieval"}'
        result = self._extract(raw)
        assert result is not None
        assert result["overall_level"] == "Retrieval"

    def test_returns_none_on_invalid(self):
        result = self._extract("This is not JSON at all.")
        assert result is None

    def test_nested_json(self):
        raw = '{"overall_level": "Analysis", "taxonomy_breakdown": [{"level": "Analysis", "rating": "proficient"}]}'
        result = self._extract(raw)
        assert result is not None
        assert isinstance(result["taxonomy_breakdown"], list)
