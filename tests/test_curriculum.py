"""
Unit tests — curriculum.py
Tests subject registry completeness, grade band coverage, and helper functions.
"""

import pytest
from curriculum import (
    GRADE_BANDS,
    SUBJECTS,
    get_subjects_for_band,
    get_subject,
    build_curriculum_context,
    grade_band_for_level,
    api_response,
    CurriculumSubject,
    GradeBand,
)
from marzano_framework import TAXONOMY


VALID_MARZANO_LEVELS = set(TAXONOMY.keys())


class TestGradeBands:
    """Grade band registry completeness."""

    EXPECTED_BANDS = {
        "elementary_k2", "elementary_3_5", "middle_6_8", "high_9_10", "high_11_12"
    }

    def test_all_expected_bands_present(self):
        assert set(GRADE_BANDS.keys()) == self.EXPECTED_BANDS

    def test_each_band_has_grade_levels(self):
        for band_id, band in GRADE_BANDS.items():
            assert band.grade_levels, f"{band_id} has no grade levels"
            assert len(band.grade_levels) >= 2

    def test_each_band_has_label_and_description(self):
        for band_id, band in GRADE_BANDS.items():
            assert band.label, f"{band_id} missing label"
            assert band.description, f"{band_id} missing description"
            assert band.typical_ages, f"{band_id} missing typical_ages"

    def test_grade_levels_are_non_overlapping(self):
        """No grade level should appear in more than one band."""
        seen = {}
        for band_id, band in GRADE_BANDS.items():
            for grade in band.grade_levels:
                assert grade not in seen, (
                    f"Grade '{grade}' appears in both '{seen.get(grade)}' and '{band_id}'"
                )
                seen[grade] = band_id


class TestSubjectRegistry:
    """Subject registry — completeness and consistency."""

    MINIMUM_SUBJECTS = 30  # We have 37; this guards against accidental deletion

    def test_minimum_subject_count(self):
        assert len(SUBJECTS) >= self.MINIMUM_SUBJECTS, (
            f"Expected at least {self.MINIMUM_SUBJECTS} subjects, got {len(SUBJECTS)}"
        )

    def test_all_subjects_have_required_fields(self):
        for s in SUBJECTS:
            assert s.name, f"Subject missing name"
            assert s.grade_band, f"{s.name} missing grade_band"
            assert s.strands, f"{s.name} missing strands"
            assert s.marzano_entry_point, f"{s.name} missing marzano_entry_point"
            assert s.marzano_target, f"{s.name} missing marzano_target"
            assert s.description, f"{s.name} missing description"
            assert s.typical_grade_levels, f"{s.name} missing typical_grade_levels"
            assert s.standards_framework, f"{s.name} missing standards_framework"

    def test_marzano_levels_are_valid(self):
        for s in SUBJECTS:
            assert s.marzano_entry_point in VALID_MARZANO_LEVELS, (
                f"{s.name}: invalid marzano_entry_point '{s.marzano_entry_point}'"
            )
            assert s.marzano_target in VALID_MARZANO_LEVELS, (
                f"{s.name}: invalid marzano_target '{s.marzano_target}'"
            )

    def test_all_subjects_reference_valid_grade_band(self):
        valid_bands = set(GRADE_BANDS.keys())
        for s in SUBJECTS:
            assert s.grade_band in valid_bands, (
                f"{s.name}: grade_band '{s.grade_band}' not in GRADE_BANDS"
            )

    def test_each_band_has_at_least_three_subjects(self):
        for band_id in GRADE_BANDS:
            subjects = get_subjects_for_band(band_id)
            assert len(subjects) >= 3, (
                f"Band '{band_id}' has only {len(subjects)} subjects (minimum 3)"
            )

    def test_every_band_has_mathematics(self):
        """Every grade band should have at least one math subject."""
        math_keywords = {"math", "algebra", "geometry", "calculus", "statistics", "number"}
        for band_id in GRADE_BANDS:
            subjects = get_subjects_for_band(band_id)
            has_math = any(
                any(kw in s.name.lower() for kw in math_keywords)
                for s in subjects
            )
            assert has_math, f"Band '{band_id}' has no mathematics subject"

    def test_every_band_has_science(self):
        """Every grade band should have at least one science subject."""
        science_keywords = {"science", "biology", "chemistry", "physics", "environmental"}
        for band_id in GRADE_BANDS:
            subjects = get_subjects_for_band(band_id)
            has_science = any(
                any(kw in s.name.lower() for kw in science_keywords)
                for s in subjects
            )
            assert has_science, f"Band '{band_id}' has no science subject"

    def test_strands_are_non_empty_list(self):
        for s in SUBJECTS:
            assert isinstance(s.strands, list), f"{s.name} strands not a list"
            assert len(s.strands) >= 2, f"{s.name} has fewer than 2 strands"

    def test_common_passions_reference_known_passion_keys(self):
        from marzano_framework import PASSION_MATH_CONNECTIONS
        valid = set(PASSION_MATH_CONNECTIONS.keys()) | {"mathematics", "custom"}
        for s in SUBJECTS:
            for passion in s.common_passions:
                assert passion in valid, (
                    f"{s.name}: unknown passion '{passion}'"
                )


class TestLookupHelpers:
    """get_subject, get_subjects_for_band, grade_band_for_level."""

    def test_get_subjects_for_band_returns_correct_band(self):
        subjects = get_subjects_for_band("middle_6_8")
        assert all(s.grade_band == "middle_6_8" for s in subjects)

    def test_get_subjects_for_band_unknown_returns_empty(self):
        assert get_subjects_for_band("nonexistent_band") == []

    def test_get_subject_hit(self):
        subjects = get_subjects_for_band("high_9_10")
        first = subjects[0]
        result = get_subject("high_9_10", first.name)
        assert result is not None
        assert result.name == first.name

    def test_get_subject_miss_returns_none(self):
        result = get_subject("middle_6_8", "Underwater Basket Weaving")
        assert result is None

    def test_grade_band_for_level_kindergarten(self):
        assert grade_band_for_level("Kindergarten") == "elementary_k2"

    def test_grade_band_for_level_grade_1(self):
        assert grade_band_for_level("Grade 1") == "elementary_k2"

    def test_grade_band_for_level_grade_4(self):
        assert grade_band_for_level("Grade 4") == "elementary_3_5"

    def test_grade_band_for_level_grade_7(self):
        assert grade_band_for_level("Grade 7") == "middle_6_8"

    def test_grade_band_for_level_grade_9(self):
        assert grade_band_for_level("Grade 9") == "high_9_10"

    def test_grade_band_for_level_grade_12(self):
        assert grade_band_for_level("Grade 12") == "high_11_12"

    def test_grade_band_for_level_case_insensitive(self):
        assert grade_band_for_level("grade 6") == "middle_6_8"


class TestCurriculumContext:
    """build_curriculum_context output quality."""

    def test_returns_string(self):
        result = build_curriculum_context("middle_6_8", "Pre-Algebra")
        assert isinstance(result, str)

    def test_contains_subject_name(self):
        result = build_curriculum_context("middle_6_8", "Pre-Algebra")
        assert "Pre-Algebra" in result

    def test_contains_marzano_target(self):
        result = build_curriculum_context("middle_6_8", "Pre-Algebra")
        assert "analysis" in result.lower() or "comprehension" in result.lower()

    def test_contains_strands(self):
        result = build_curriculum_context("middle_6_8", "Pre-Algebra")
        assert "Ratios" in result or "strand" in result.lower()

    def test_returns_empty_for_unknown_subject(self):
        result = build_curriculum_context("middle_6_8", "Unicorn Studies")
        assert result == ""

    def test_returns_empty_for_unknown_band(self):
        result = build_curriculum_context("unknown_band", "Pre-Algebra")
        assert result == ""


class TestApiResponse:
    """api_response() structure for frontend consumption."""

    def test_contains_grade_bands_key(self):
        data = api_response()
        assert "grade_bands" in data

    def test_contains_subjects_key(self):
        data = api_response()
        assert "subjects" in data

    def test_subjects_keyed_by_band(self):
        data = api_response()
        for band_id in GRADE_BANDS:
            assert band_id in data["subjects"], f"Band '{band_id}' missing from api_response"

    def test_subjects_are_serializable(self):
        import json
        data = api_response()
        # Should not raise
        serialized = json.dumps(data)
        assert len(serialized) > 100
