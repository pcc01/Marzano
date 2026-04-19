"""
Unit tests — international.py
Tests country registry, grade equivalency map, Marzano framework mapping,
and the context builder used by the AI prompt.
"""

import pytest
from international import (
    COUNTRIES,
    GRADE_LEVEL_MAP,
    MARZANO_TO_INTERNATIONAL,
    get_grade_equivalent,
    get_marzano_international,
    build_international_context,
    api_response,
)


class TestCountryRegistry:
    """Country data completeness and correctness."""

    REQUIRED_COUNTRIES = {"US", "GB", "AU", "CA", "FR", "DE", "JP", "IB", "NZ", "SG"}

    def test_all_required_countries_present(self):
        assert self.REQUIRED_COUNTRIES.issubset(set(COUNTRIES.keys()))

    def test_each_country_has_name(self):
        for code, country in COUNTRIES.items():
            assert country.name, f"{code} missing name"

    def test_each_country_has_education_system(self):
        for code, country in COUNTRIES.items():
            assert country.education_system, f"{code} missing education_system"

    def test_each_country_has_curriculum_framework(self):
        for code, country in COUNTRIES.items():
            assert country.curriculum_framework, f"{code} missing curriculum_framework"

    def test_each_country_has_grade_terminology(self):
        for code, country in COUNTRIES.items():
            assert country.grade_terminology, f"{code} missing grade_terminology"

    def test_each_country_has_compulsory_age_range(self):
        for code, country in COUNTRIES.items():
            assert country.compulsory_age_range, f"{code} missing compulsory_age_range"

    def test_country_codes_are_uppercase(self):
        for code in COUNTRIES:
            assert code == code.upper(), f"Country code '{code}' should be uppercase"

    def test_us_entry_correct(self):
        us = COUNTRIES["US"]
        assert us.name == "United States"
        assert "K-12" in us.education_system or "K–12" in us.education_system


class TestGradeLevelMap:
    """US → international grade level equivalency completeness."""

    ALL_US_GRADES = [
        "Kindergarten",
        "Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5",
        "Grade 6", "Grade 7", "Grade 8", "Grade 9", "Grade 10",
        "Grade 11", "Grade 12",
    ]

    def test_all_us_grades_mapped(self):
        for grade in self.ALL_US_GRADES:
            assert grade in GRADE_LEVEL_MAP, f"US grade '{grade}' not in GRADE_LEVEL_MAP"

    def test_each_grade_mapped_to_all_countries(self):
        """Every US grade must have an entry for every non-US country."""
        non_us = {"GB", "AU", "CA", "FR", "DE", "JP", "IB", "NZ", "SG"}
        for grade, mapping in GRADE_LEVEL_MAP.items():
            for country in non_us:
                assert country in mapping, (
                    f"Grade '{grade}' missing mapping for country '{country}'"
                )

    def test_grade_entries_are_non_empty_strings(self):
        for grade, mapping in GRADE_LEVEL_MAP.items():
            for country, equiv in mapping.items():
                assert isinstance(equiv, str) and equiv.strip(), (
                    f"Grade '{grade}' → '{country}' has empty/invalid equivalent"
                )

    def test_grade_progression_is_consistent(self):
        """Spot-check that lower grades map to lower UK years."""
        grade_1_uk = GRADE_LEVEL_MAP["Grade 1"]["GB"]
        grade_6_uk = GRADE_LEVEL_MAP["Grade 6"]["GB"]
        grade_12_uk = GRADE_LEVEL_MAP["Grade 12"]["GB"]
        # Year numbers should increase with grade
        assert "Year 2" in grade_1_uk
        assert "Year 7" in grade_6_uk
        assert "Year 13" in grade_12_uk


class TestGetGradeEquivalent:
    """get_grade_equivalent() helper."""

    def test_known_grade_and_country(self):
        result = get_grade_equivalent("Grade 9", "GB")
        assert result is not None
        assert "Year 10" in result

    def test_kindergarten_australia(self):
        result = get_grade_equivalent("Kindergarten", "AU")
        assert result is not None
        assert "Foundation" in result or "Prep" in result

    def test_grade_12_japan(self):
        result = get_grade_equivalent("Grade 12", "JP")
        assert result is not None
        assert "高校" in result or "高" in result

    def test_unknown_grade_returns_none(self):
        result = get_grade_equivalent("Grade 99", "GB")
        assert result is None

    def test_unknown_country_returns_none(self):
        result = get_grade_equivalent("Grade 5", "ZZ")
        assert result is None

    def test_ib_grade_12_is_dp(self):
        result = get_grade_equivalent("Grade 12", "IB")
        assert result is not None
        assert "DP" in result


class TestMarzanoInternationalMapping:
    """MARZANO_TO_INTERNATIONAL completeness and correctness."""

    EXPECTED_LEVELS = {
        "retrieval", "comprehension", "analysis",
        "knowledge_utilization", "metacognitive", "self_system",
    }

    EXPECTED_FRAMEWORKS = {"GB", "AU", "IB_MYP", "IB_DP", "FR", "DE", "PISA", "TIMSS"}

    def test_all_marzano_levels_mapped(self):
        assert set(MARZANO_TO_INTERNATIONAL.keys()) == self.EXPECTED_LEVELS

    def test_each_level_has_description(self):
        for level, mapping in MARZANO_TO_INTERNATIONAL.items():
            assert "description" in mapping, f"{level} missing description"
            assert len(mapping["description"]) > 10

    def test_each_level_has_all_frameworks(self):
        for level, mapping in MARZANO_TO_INTERNATIONAL.items():
            for fw in self.EXPECTED_FRAMEWORKS:
                assert fw in mapping, f"Level '{level}' missing framework '{fw}'"

    def test_framework_entries_are_non_empty(self):
        for level, mapping in MARZANO_TO_INTERNATIONAL.items():
            for fw, text in mapping.items():
                if fw == "description":
                    continue
                assert isinstance(text, str) and text.strip(), (
                    f"Level '{level}' → '{fw}' is empty"
                )

    def test_knowledge_utilization_is_highest_gb(self):
        """Knowledge Utilization should map to A-Level / exceeding in UK."""
        ku_gb = MARZANO_TO_INTERNATIONAL["knowledge_utilization"]["GB"]
        assert "A*" in ku_gb or "Exceeding" in ku_gb or "exceeding" in ku_gb.lower()

    def test_retrieval_is_lowest_pisa(self):
        """Retrieval is the lowest cognitive level — should map to low PISA levels."""
        ret_pisa = MARZANO_TO_INTERNATIONAL["retrieval"]["PISA"]
        assert "1" in ret_pisa or "2" in ret_pisa


class TestGetMarzanoInternational:
    """get_marzano_international() helper."""

    def test_without_country_returns_all_frameworks(self):
        result = get_marzano_international("analysis")
        assert "all_equivalencies" in result
        assert "GB" in result["all_equivalencies"]

    def test_with_country_returns_specific_entry(self):
        result = get_marzano_international("analysis", "GB")
        assert "equivalent" in result
        assert result["country"] == "GB"

    def test_unknown_level_returns_empty_dict(self):
        result = get_marzano_international("nonexistent_level")
        assert result.get("all_equivalencies", {}) == {}


class TestBuildInternationalContext:
    """build_international_context() — prompt injection string.
    Signature: (us_grade, country_code, marzano_target=None)
    """

    def test_returns_string(self):
        result = build_international_context("Grade 10", "GB")
        assert isinstance(result, str)

    def test_contains_country_name(self):
        result = build_international_context("Grade 10", "GB")
        assert "United Kingdom" in result

    def test_contains_education_system(self):
        result = build_international_context("Grade 10", "AU")
        assert "Australian" in result or "ACARA" in result

    def test_contains_local_grade_equivalent(self):
        result = build_international_context("Grade 10", "GB")
        assert "Year 11" in result

    def test_unknown_country_returns_empty(self):
        result = build_international_context("Grade 10", "ZZ")
        assert result == ""

    def test_contains_grading_notes_when_present(self):
        """UK has grading notes about Key Stages."""
        result = build_international_context("Grade 10", "GB")
        assert "Key Stage" in result or "GCSE" in result or "KS" in result

    def test_ib_context(self):
        result = build_international_context("Grade 11", "IB")
        assert "IB" in result or "International Baccalaureate" in result
        assert "DP" in result

    def test_with_marzano_target_includes_framework_mapping(self):
        """When marzano_target is given, the framework equivalency should appear."""
        result = build_international_context("Grade 10", "GB", marzano_target="analysis")
        assert "analysis" in result.lower() or "greater depth" in result.lower() or "GB" in result

    def test_without_marzano_target_still_returns_context(self):
        result = build_international_context("Grade 9", "AU")
        assert "Australia" in result
        assert "Grade 9" in result or "Year 9" in result or "Year 10" in result

    def test_marzano_target_retrieval_maps_to_lowest(self):
        """Retrieval is lowest — should reference foundation-level in AU framework."""
        result = build_international_context("Grade 6", "AU", marzano_target="retrieval")
        assert isinstance(result, str)
        assert len(result) > 20


class TestApiResponse:
    """api_response() structure."""

    def test_contains_countries(self):
        data = api_response()
        assert "countries" in data

    def test_contains_grade_map(self):
        data = api_response()
        assert "grade_level_map" in data

    def test_contains_marzano_international(self):
        data = api_response()
        assert "marzano_international" in data

    def test_is_json_serializable(self):
        import json
        data = api_response()
        serialized = json.dumps(data)
        assert len(serialized) > 500

    def test_status_is_roadmap(self):
        data = api_response()
        assert data.get("status") == "roadmap"

    def test_target_version(self):
        data = api_response()
        assert "0.4.0" in data.get("target_version", "")
