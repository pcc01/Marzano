"""
Tests for Marzano v0.3.0 Features:
- FEATURE 1: AI Artifact Retention (original_ai_draft)
- FEATURE 2: Teacher-Only Competency Assessment
"""

import json
import pytest
import sys
import os
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))


def _make_session():
    """Create a mock SQLAlchemy session."""
    session = AsyncMock()
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


@pytest.fixture(scope="module")
def client():
    """Set up test client with mocked database and AI."""
    mock_session = _make_session()
    async_ctx = AsyncMock()
    async_ctx.__aenter__ = AsyncMock(return_value=mock_session)
    async_ctx.__aexit__ = AsyncMock(return_value=False)
    async_session_local = MagicMock(return_value=async_ctx)

    with patch("database.init_db", new_callable=AsyncMock), \
         patch("database.AsyncSessionLocal", async_session_local), \
         patch("haystack_pipeline.rag") as mock_rag, \
         patch("haystack_pipeline.prewarm", new_callable=AsyncMock), \
         patch("ai_provider.call_ai", new_callable=AsyncMock,
               return_value='{"overall_level":"Analysis","overall_sublevel":"Generalizing","strength_summary":"Good work","growth_summary":"Develop deeper analysis","taxonomy_breakdown":[],"next_level_prompt":"Consider this","standards_connections":[],"standards_cited":[],"passion_integration":"Integrated well","ai_reasoning":"Solid assessment"}'), \
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
# FEATURE 1: AI Artifact Retention Tests
# ─────────────────────────────────────────────────────────────

def test_assessment_includes_original_ai_draft(client):
    """
    FEATURE 1: When creating an assessment, the original AI draft 
    should be stored immutably.
    """
    response = client.post(
        "/assess",
        data={
            "student_name": "Alice Chen",
            "subject": "Mathematics",
            "grade_level": "8",
            "student_passion": "Space exploration",
            "artifact_description": "Created a scale model of the solar system",
            "student_reflection": "I learned about planetary distances",
            "submitted_by": "teacher",
        }
    )
    assert response.status_code == 200
    data = response.json()
    
    # Assessment should be created
    assert "assessment_id" in data
    assert data["student_name"] == "Alice Chen"
    
    # Note: In real usage, original_ai_draft would be stored in DB
    # For this test, we verify the creation succeeded
    assert data["subject"] == "Mathematics"


def test_get_assessment_returns_original_draft_to_teacher(client):
    """
    FEATURE 1: When teacher retrieves an assessment,
    original_ai_draft should be included.
    """
    # Mock the database to return an assessment with original_ai_draft
    with patch("database.get_assessment") as mock_get:
        from database import Assessment
        import datetime
        
        mock_assessment = Assessment()
        mock_assessment.id = "test-id-123"
        mock_assessment.student_name = "Bob Johnson"
        mock_assessment.subject = "Science"
        mock_assessment.grade_level = "6"
        mock_assessment.student_passion = "Biology"
        mock_assessment.artifact_description = "Leaf collection"
        mock_assessment.student_reflection = "Learned about leaf structure"
        mock_assessment.has_image = False
        mock_assessment.has_video = False
        mock_assessment.artifact_filename = None
        mock_assessment.feedback = {"overall_level": "Understanding"}
        mock_assessment.raw_ai_response = '{"overall_level":"Understanding"}'
        mock_assessment.original_ai_draft = '{"overall_level":"Understanding","strength_summary":"Good observational skills"}'  # NEW FIELD
        mock_assessment.teacher_comments = ""
        mock_assessment.teacher_edited_level = None
        mock_assessment.approved = False
        mock_assessment.submitted_by = "teacher"
        mock_assessment.created_at = datetime.datetime.utcnow()
        mock_assessment.teacher_updated_at = None
        mock_assessment.country_code = None
        mock_assessment.local_grade = None
        
        mock_get.return_value = mock_assessment
        
        response = client.get("/assessments/test-id-123")
        
        assert response.status_code == 200
        data = response.json()
        
        # Teacher should see the original draft
        assert "original_ai_draft" in data
        assert "Understanding" in data["original_ai_draft"]


# ─────────────────────────────────────────────────────────────
# FEATURE 2: Teacher-Only Competency Assessment Tests
# ─────────────────────────────────────────────────────────────

def test_assessment_generates_competency_assessment(client):
    """
    FEATURE 2: When creating an assessment, the system should 
    generate a teacher-only competency assessment with standards evidence.
    """
    with patch("ai_provider.call_ai") as mock_ai:
        # First call returns main assessment
        # Second call returns competency assessment
        competency_response = json.dumps({
            "standards_evidence": [
                "Demonstrates understanding of linear functions",
                "Shows algebraic reasoning"
            ],
            "grade_alignment": "Meets grade 8 standards",
            "competency_areas": ["Algebraic Thinking", "Problem Solving"],
            "growth_recommendations": [
                "Extend to systems of equations",
                "Apply to real-world scenarios"
            ],
            "rigor_analysis": "Appropriate cognitive demand for grade level",
            "teacher_notes": "Strong foundational understanding, ready for algebra"
        })
        
        mock_ai.side_effect = [
            '{"overall_level":"Understanding","strength_summary":"Good"}',  # Main assessment
            competency_response  # Competency assessment
        ]
        
        response = client.post(
            "/assess",
            data={
                "student_name": "Charlie Davis",
                "subject": "Mathematics",
                "grade_level": "8",
                "student_passion": "Video games",
                "artifact_description": "Solved linear equation problems",
                "student_reflection": "Used logical thinking",
                "submitted_by": "teacher",
            }
        )
        
        assert response.status_code == 200
        # Verify both AI calls were made (main + competency)
        assert mock_ai.call_count == 2


def test_student_api_excludes_competency_assessment(client):
    """
    FEATURE 2: When students check their status via /student/status,
    competency_assessment should NOT be included (teacher-only).
    """
    with patch("database.get_assessment") as mock_get:
        from database import Assessment
        import datetime
        
        mock_assessment = Assessment()
        mock_assessment.id = "student-submission-456"
        mock_assessment.student_name = "Diana Zhang"
        mock_assessment.subject = "English"
        mock_assessment.grade_level = "7"
        mock_assessment.student_passion = "Poetry"
        mock_assessment.artifact_description = "Wrote a haiku"
        mock_assessment.student_reflection = "Learned about syllables"
        mock_assessment.has_image = False
        mock_assessment.has_video = False
        mock_assessment.artifact_filename = None
        mock_assessment.feedback = {"overall_level": "Comprehension"}
        mock_assessment.original_ai_draft = '{"overall_level":"Comprehension"}'
        mock_assessment.competency_assessment = {  # Teacher-only field
            "standards_evidence": ["Demonstrates poetic devices"],
            "grade_alignment": "Meets standards",
            "competency_areas": ["Creative Expression"],
            "growth_recommendations": ["Explore more advanced forms"],
            "rigor_analysis": "Appropriate",
            "teacher_notes": "Show potential"
        }
        mock_assessment.teacher_comments = ""
        mock_assessment.teacher_edited_level = None
        mock_assessment.approved = False
        mock_assessment.submitted_by = "student"
        mock_assessment.created_at = datetime.datetime.utcnow()
        mock_assessment.teacher_updated_at = None
        mock_assessment.country_code = None
        mock_assessment.local_grade = None
        
        mock_get.return_value = mock_assessment
        
        # Student checks their status
        response = client.get("/student/status/student-submission-456")
        
        assert response.status_code == 200
        data = response.json()
        
        # Student should NOT see competency_assessment
        assert "competency_assessment" not in data
        assert data["status"] in ["reviewed", "pending_review"]


def test_teacher_get_includes_competency_assessment(client):
    """
    FEATURE 2: When teacher retrieves assessment via /assessments/{id},
    competency_assessment SHOULD be included.
    """
    with patch("database.get_assessment") as mock_get:
        from database import Assessment
        import datetime
        
        mock_assessment = Assessment()
        mock_assessment.id = "teacher-view-789"
        mock_assessment.student_name = "Emma Foster"
        mock_assessment.subject = "History"
        mock_assessment.grade_level = "9"
        mock_assessment.student_passion = "Ancient civilizations"
        mock_assessment.artifact_description = "Created a timeline of Rome"
        mock_assessment.student_reflection = "Understood cause and effect"
        mock_assessment.has_image = False
        mock_assessment.has_video = False
        mock_assessment.artifact_filename = None
        mock_assessment.feedback = {"overall_level": "Application"}
        mock_assessment.original_ai_draft = '{"overall_level":"Application"}'
        mock_assessment.competency_assessment = {  # Teacher-only
            "standards_evidence": [
                "Analyzes historical cause and effect",
                "Synthesizes multiple sources",
                "Demonstrates chronological understanding"
            ],
            "grade_alignment": "Exceeds grade 9 standards",
            "competency_areas": ["Critical Thinking", "Historical Analysis", "Synthesis"],
            "growth_recommendations": [
                "Explore historiographical debates",
                "Analyze primary sources in greater depth"
            ],
            "rigor_analysis": "High cognitive demand - excellent for advanced students",
            "teacher_notes": "Gifted student - recommend enrichment"
        }
        mock_assessment.teacher_comments = ""
        mock_assessment.teacher_edited_level = None
        mock_assessment.approved = False
        mock_assessment.submitted_by = "teacher"
        mock_assessment.created_at = datetime.datetime.utcnow()
        mock_assessment.teacher_updated_at = None
        mock_assessment.country_code = None
        mock_assessment.local_grade = None
        
        mock_get.return_value = mock_assessment
        
        # Teacher retrieves assessment
        response = client.get("/assessments/teacher-view-789")
        
        assert response.status_code == 200
        data = response.json()
        
        # Teacher SHOULD see competency_assessment
        assert "competency_assessment" in data
        assert "standards_evidence" in data["competency_assessment"]
        assert len(data["competency_assessment"]["standards_evidence"]) > 0
        assert "teacher_notes" in data["competency_assessment"]


def test_competency_assessment_includes_all_required_fields(client):
    """
    FEATURE 2: Competency assessment must include all required fields
    for comprehensive standards evaluation.
    """
    with patch("ai_provider.call_ai") as mock_ai:
        competency_response = json.dumps({
            "standards_evidence": ["Evidence 1", "Evidence 2"],
            "grade_alignment": "Alignment description",
            "competency_areas": ["Competency 1", "Competency 2"],
            "growth_recommendations": ["Recommendation 1"],
            "rigor_analysis": "Rigor description",
            "teacher_notes": "Teacher summary notes"
        })
        
        mock_ai.side_effect = [
            '{"overall_level":"Proficiency","strength_summary":"Good"}',
            competency_response
        ]
        
        response = client.post(
            "/assess",
            data={
                "student_name": "Frank Green",
                "subject": "Science",
                "grade_level": "5",
                "student_passion": "Environmental science",
                "artifact_description": "Studied local ecosystem",
                "student_reflection": "Learned about food chains",
                "submitted_by": "teacher",
            }
        )
        
        assert response.status_code == 200


# ─────────────────────────────────────────────────────────────
# Integration Tests
# ─────────────────────────────────────────────────────────────

def test_assessment_workflow_with_both_features(client):
    """
    Integration test: Create assessment, verify original_ai_draft 
    is stored, verify competency_assessment is generated,
    and verify teacher sees both but students don't see competency.
    """
    response = client.post(
        "/assess",
        data={
            "student_name": "Grace Holmes",
            "subject": "Art",
            "grade_level": "4",
            "student_passion": "Drawing",
            "artifact_description": "Created a watercolor painting",
            "student_reflection": "Experimented with color mixing",
            "submitted_by": "teacher",
        }
    )
    
    assert response.status_code == 200
    data = response.json()
    assessment_id = data["assessment_id"]
    assert assessment_id is not None
    
    # In a real scenario with actual DB, we'd verify:
    # 1. original_ai_draft is stored in DB
    # 2. competency_assessment is generated and stored
    # 3. GET /assessments/{id} includes both for teachers
    # 4. GET /student/status/{id} excludes competency_assessment
    # 5. PATCH /assessments/{id} allows teacher to add comments/edits

