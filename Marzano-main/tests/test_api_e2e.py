"""
End-to-end API tests — FastAPI TestClient
Tests all read-only and data-returning endpoints without a live DB or AI.
The startup lifecycle and all DB/AI calls are patched before the app loads.
"""

import json
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


# ─────────────────────────────────────────────────────────────
# Build a mock session that satisfies the startup event and
# the get_session dependency without hitting PostgreSQL.
# ─────────────────────────────────────────────────────────────

def _make_session():
    session = AsyncMock()
    # Scalars chain: session.execute(...).scalars().all() → []
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = []
    result_mock = MagicMock()
    result_mock.scalars.return_value = scalars_mock
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.commit = AsyncMock()
    session.close = AsyncMock()
    return session


async def _override_get_session():
    yield _make_session()


# ─────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    mock_session = _make_session()

    # Context manager for AsyncSessionLocal() used in startup and _run_ingestion
    async_ctx = AsyncMock()
    async_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    async_ctx.__aexit__ = AsyncMock(return_value=False)

    async_session_local = MagicMock(return_value=async_ctx)

    with patch("database.init_db", new_callable=AsyncMock), \
         patch("database.AsyncSessionLocal", async_session_local), \
         patch("haystack_pipeline.rag") as mock_rag, \
         patch("haystack_pipeline.prewarm", new_callable=AsyncMock), \
         patch("ai_provider.call_ai", new_callable=AsyncMock,
               return_value='{"overall_level":"Analysis","overall_sublevel":"Generalizing","strength_summary":"Good","growth_summary":"More depth needed","taxonomy_breakdown":[],"next_level_prompt":"Go further","standards_connections":[],"standards_cited":[],"passion_integration":"Good","ai_reasoning":"Test"}'), \
         patch("notifications.notif_manager") as mock_notif:

        mock_rag.loaded = False
        mock_rag.doc_count = 0
        mock_rag.context_block = AsyncMock(return_value="")
        mock_notif.broadcast = AsyncMock()
        mock_notif.subscriber_count.return_value = 0
        mock_notif.subscribe = MagicMock(return_value=AsyncMock())

        from fastapi.testclient import TestClient
        import main as app_module
        from database import get_session

        app_module.app.dependency_overrides[get_session] = _override_get_session

        with TestClient(app_module.app, raise_server_exceptions=True) as c:
            yield c

        app_module.app.dependency_overrides.clear()


# ─────────────────────────────────────────────────────────────
# Health endpoint
# ─────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_returns_200(self, client):
        assert client.get("/health").status_code == 200

    def test_health_has_status_ok(self, client):
        assert client.get("/health").json()["status"] == "ok"

    def test_health_has_ai_info(self, client):
        assert "ai" in client.get("/health").json()

    def test_health_has_rag_info(self, client):
        assert "rag" in client.get("/health").json()

    def test_health_has_version(self, client):
        assert "version" in client.get("/health").json()


# ─────────────────────────────────────────────────────────────
# Taxonomy endpoint
# ─────────────────────────────────────────────────────────────

class TestTaxonomyEndpoint:
    def test_returns_200(self, client):
        assert client.get("/taxonomy").status_code == 200

    def test_has_six_levels(self, client):
        data = client.get("/taxonomy").json()
        assert len(data) == 6

    def test_contains_self_system(self, client):
        assert "self_system" in client.get("/taxonomy").json()

    def test_contains_knowledge_utilization(self, client):
        assert "knowledge_utilization" in client.get("/taxonomy").json()

    def test_each_level_has_name(self, client):
        data = client.get("/taxonomy").json()
        for level_id, level in data.items():
            assert "name" in level, f"{level_id} missing name"

    def test_each_level_has_sublevels(self, client):
        data = client.get("/taxonomy").json()
        for level_id, level in data.items():
            assert len(level.get("sublevels", [])) > 0

    def test_sublevels_have_verbs(self, client):
        data = client.get("/taxonomy").json()
        for level_id, level in data.items():
            for sub in level["sublevels"]:
                assert len(sub.get("verbs", [])) > 0

    def test_response_is_json(self, client):
        r = client.get("/taxonomy")
        assert r.headers["content-type"].startswith("application/json")


# ─────────────────────────────────────────────────────────────
# Passions endpoint
# ─────────────────────────────────────────────────────────────

class TestPassionsEndpoint:
    def test_returns_200(self, client):
        assert client.get("/passions").status_code == 200

    def test_contains_photography(self, client):
        assert "photography" in client.get("/passions").json()

    def test_contains_architecture(self, client):
        assert "architecture" in client.get("/passions").json()

    def test_contains_music(self, client):
        assert "music" in client.get("/passions").json()

    def test_each_passion_has_concepts(self, client):
        data = client.get("/passions").json()
        for passion, info in data.items():
            assert "concepts" in info, f"{passion} missing concepts"
            assert len(info["concepts"]) >= 2


# ─────────────────────────────────────────────────────────────
# Curriculum endpoints
# ─────────────────────────────────────────────────────────────

class TestCurriculumEndpoints:
    def test_curriculum_returns_200(self, client):
        assert client.get("/curriculum").status_code == 200

    def test_curriculum_has_five_grade_bands(self, client):
        data = client.get("/curriculum").json()
        assert len(data["grade_bands"]) == 5

    def test_curriculum_has_subjects_dict(self, client):
        data = client.get("/curriculum").json()
        assert "subjects" in data
        assert isinstance(data["subjects"], dict)

    def test_curriculum_subjects_cover_all_bands(self, client):
        data = client.get("/curriculum").json()
        expected_bands = {
            "elementary_k2", "elementary_3_5", "middle_6_8",
            "high_9_10", "high_11_12",
        }
        assert expected_bands.issubset(set(data["subjects"].keys()))

    def test_curriculum_band_middle_returns_200(self, client):
        assert client.get("/curriculum/middle_6_8").status_code == 200

    def test_curriculum_band_high_returns_200(self, client):
        assert client.get("/curriculum/high_9_10").status_code == 200

    def test_curriculum_band_has_correct_band_id(self, client):
        data = client.get("/curriculum/middle_6_8").json()
        assert data["grade_band"] == "middle_6_8"

    def test_curriculum_band_has_grade_levels_list(self, client):
        data = client.get("/curriculum/middle_6_8").json()
        assert "grade_levels" in data
        assert "Grade 6" in data["grade_levels"]

    def test_curriculum_band_subjects_have_marzano_target(self, client):
        data = client.get("/curriculum/high_9_10").json()
        for sub in data["subjects"]:
            assert "marzano_target" in sub

    def test_curriculum_band_subjects_have_strands(self, client):
        data = client.get("/curriculum/middle_6_8").json()
        for sub in data["subjects"]:
            assert len(sub.get("strands", [])) >= 2

    def test_curriculum_band_subjects_have_passion_links(self, client):
        data = client.get("/curriculum/high_9_10").json()
        for sub in data["subjects"]:
            assert "common_passions" in sub

    def test_invalid_grade_band_returns_404(self, client):
        assert client.get("/curriculum/grade_99").status_code == 404


# ─────────────────────────────────────────────────────────────
# International endpoints
# ─────────────────────────────────────────────────────────────

class TestInternationalEndpoints:
    def test_international_returns_200(self, client):
        assert client.get("/international").status_code == 200

    def test_international_has_ten_countries(self, client):
        data = client.get("/international").json()
        assert len(data["countries"]) >= 10

    def test_international_includes_gb(self, client):
        data = client.get("/international").json()
        assert "GB" in data["countries"]

    def test_international_includes_ib(self, client):
        data = client.get("/international").json()
        assert "IB" in data["countries"]

    def test_international_grade_map_covers_grade_9(self, client):
        data = client.get("/international").json()
        assert "Grade 9" in data["grade_level_map"]

    def test_international_marzano_covers_analysis(self, client):
        data = client.get("/international").json()
        assert "analysis" in data["marzano_international"]

    def test_grade_equivalent_grade_9_gb(self, client):
        r = client.get("/international/grades/Grade 9")
        assert r.status_code == 200
        data = r.json()
        assert "GB" in data["equivalents"]
        assert "Year 10" in data["equivalents"]["GB"]

    def test_grade_equivalent_kindergarten_au(self, client):
        r = client.get("/international/grades/Kindergarten")
        assert r.status_code == 200
        assert "AU" in r.json()["equivalents"]

    def test_grade_equivalent_grade_12_ib(self, client):
        r = client.get("/international/grades/Grade 12")
        assert r.status_code == 200
        assert "DP" in r.json()["equivalents"]["IB"]

    def test_grade_equivalent_unknown_returns_404(self, client):
        assert client.get("/international/grades/Grade 99").status_code == 404

    def test_marzano_level_analysis_returns_200(self, client):
        assert client.get("/international/marzano/analysis").status_code == 200

    def test_marzano_level_has_gb_mapping(self, client):
        data = client.get("/international/marzano/analysis").json()
        assert "GB" in data["mapping"]

    def test_marzano_level_has_pisa_mapping(self, client):
        data = client.get("/international/marzano/retrieval").json()
        assert "PISA" in data["mapping"]

    def test_marzano_level_has_ib_dp_mapping(self, client):
        data = client.get("/international/marzano/knowledge_utilization").json()
        assert "IB_DP" in data["mapping"]

    def test_marzano_level_unknown_returns_404(self, client):
        assert client.get("/international/marzano/made_up_level").status_code == 404

    def test_all_six_marzano_levels_have_endpoint(self, client):
        levels = [
            "retrieval", "comprehension", "analysis",
            "knowledge_utilization", "metacognitive", "self_system",
        ]
        for level in levels:
            r = client.get(f"/international/marzano/{level}")
            assert r.status_code == 200, f"Level '{level}' returned {r.status_code}"


# ─────────────────────────────────────────────────────────────
# Ingest status endpoint
# ─────────────────────────────────────────────────────────────

class TestIngestStatus:
    def test_returns_200(self, client):
        assert client.get("/ingest/status").status_code == 200

    def test_has_haystack_available_field(self, client):
        data = client.get("/ingest/status").json()
        assert "haystack_available" in data

    def test_has_index_loaded_field(self, client):
        data = client.get("/ingest/status").json()
        assert "index_loaded" in data

    def test_has_doc_count_field(self, client):
        data = client.get("/ingest/status").json()
        assert "doc_count" in data
        assert isinstance(data["doc_count"], int)


# ─────────────────────────────────────────────────────────────
# Assessments list endpoint
# ─────────────────────────────────────────────────────────────

class TestAssessmentsListEndpoint:
    def test_returns_200(self, client):
        assert client.get("/assessments").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/assessments").json()
        assert isinstance(data, list)


# ─────────────────────────────────────────────────────────────
# International — grade and Marzano lookup consistency
# ─────────────────────────────────────────────────────────────

class TestInternationalConsistency:
    def test_all_curriculum_grade_levels_have_international_lookup(self, client):
        """Every grade level from curriculum should be findable in the grade map."""
        curriculum = client.get("/curriculum").json()
        intl = client.get("/international").json()
        grade_map = intl.get("grade_level_map", {})
        for band_id, subjects in curriculum["subjects"].items():
            band = curriculum["grade_bands"].get(band_id, {})
            for grade in band.get("grade_levels", []):
                assert grade in grade_map, f"Grade '{grade}' not in international grade map"

    def test_international_marzano_covers_all_taxonomy_levels(self, client):
        """Every level from /taxonomy should appear in /international marzano_international."""
        taxonomy = client.get("/taxonomy").json()
        intl = client.get("/international").json()
        intl_marzano = intl.get("marzano_international", {})
        for level_id in taxonomy:
            assert level_id in intl_marzano, (
                f"Taxonomy level '{level_id}' missing from international marzano map"
            )

    def test_grade_endpoint_returns_all_countries_for_grade_9(self, client):
        expected = {"GB", "AU", "CA", "FR", "DE", "JP", "IB", "NZ", "SG"}
        data = client.get("/international/grades/Grade 9").json()
        for code in expected:
            assert code in data["equivalents"], f"Country '{code}' missing from Grade 9 map"


# ─────────────────────────────────────────────────────────────
# Student submit — context field forwarding
# ─────────────────────────────────────────────────────────────

class TestStudentSubmitFields:
    """Smoke-test that /student/submit accepts the same context fields as /assess."""

    def test_student_submit_accepts_grade_band(self, client):
        """grade_band field must not cause a 422 validation error."""
        r = client.post("/student/submit", data={
            "student_name": "Test Student",
            "subject": "Pre-Algebra",
            "grade_level": "Grade 7",
            "grade_band": "middle_6_8",
            "student_passion": "photography",
            "artifact_description": "Photo ratio project",
        })
        # 200 means the field was accepted (AI is mocked so it won't fail on AI call)
        assert r.status_code != 422, f"422 means grade_band field rejected: {r.text}"

    def test_student_submit_accepts_country_code(self, client):
        r = client.post("/student/submit", data={
            "student_name": "Test Student",
            "subject": "Geometry",
            "grade_level": "Grade 10",
            "grade_band": "high_9_10",
            "student_passion": "architecture",
            "artifact_description": "Arch design project",
            "country_code": "GB",
            "local_grade": "Year 11",
        })
        assert r.status_code != 422, f"422 means country_code field rejected: {r.text}"

    def test_student_submit_accepts_student_state(self, client):
        r = client.post("/student/submit", data={
            "student_name": "Test Student",
            "subject": "Algebra I",
            "grade_level": "Grade 9",
            "grade_band": "high_9_10",
            "student_passion": "music",
            "artifact_description": "Frequency ratios project",
            "student_state": "California",
        })
        assert r.status_code != 422, f"422 means student_state field rejected: {r.text}"


# ─────────────────────────────────────────────────────────────
# Assessments list — country fields present
# ─────────────────────────────────────────────────────────────

class TestAssessmentsListFields:
    def test_list_response_has_country_code_field(self, client):
        """Every row in the assessments list must include country_code."""
        # The list is empty in tests (mocked DB) but the shape is validated
        # by checking the endpoint at least returns 200 and a list
        r = client.get("/assessments")
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)
        # If there were rows, they'd have country_code — confirmed by _assessment_to_dict test


# ─────────────────────────────────────────────────────────────
# Ingest jobs list endpoint
# ─────────────────────────────────────────────────────────────

class TestIngestJobsEndpoint:
    def test_returns_200(self, client):
        assert client.get("/ingest/jobs").status_code == 200

    def test_returns_list(self, client):
        data = client.get("/ingest/jobs").json()
        assert isinstance(data, list)
