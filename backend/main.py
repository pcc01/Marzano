"""
Marzano Assessment API
FastAPI backend — handles multi-modal artifact submission and AI feedback generation.
"""

import os
import json
import uuid
import base64
import asyncio
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from marzano_framework import build_system_prompt, build_artifact_prompt, TAXONOMY, PASSION_MATH_CONNECTIONS
from ai_provider import call_ai, get_provider_info
from haystack_pipeline import rag

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------
app = FastAPI(
    title="Marzano Assessment API",
    description="AI-powered educational assessment grounded in Marzano's New Taxonomy",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Simple file-based storage (swap for PostgreSQL via DATABASE_URL in production)
DATA_DIR = Path(os.getenv("DATA_DIR", "/data/assessments"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------
class TeacherEdit(BaseModel):
    assessment_id: str
    teacher_comments: str
    edited_level: Optional[str] = None
    edited_sublevel: Optional[str] = None
    approved: bool = False


class AssessmentSummary(BaseModel):
    id: str
    student_name: str
    subject: str
    passion: str
    grade_level: str
    created_at: str
    overall_level: str
    approved: bool


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ai": get_provider_info(),
        "rag_loaded": rag._loaded,
    }


@app.get("/taxonomy")
async def get_taxonomy():
    """Return the full Marzano taxonomy for the frontend to display."""
    result = {}
    for key, level in TAXONOMY.items():
        result[key] = {
            "id": level.id,
            "name": level.name,
            "description": level.description,
            "bloom_equivalent": getattr(level, "bloom_equivalent", ""),
            "sublevels": [
                {
                    "name": s.name,
                    "description": s.description,
                    "verbs": s.verbs,
                    "question_stems": s.question_stems,
                }
                for s in level.sublevels
            ],
        }
    return result


@app.get("/passions")
async def get_passions():
    return PASSION_MATH_CONNECTIONS


@app.post("/assess")
async def create_assessment(
    student_name: str = Form(...),
    subject: str = Form(...),
    grade_level: str = Form(...),
    student_passion: str = Form(...),
    artifact_description: str = Form(...),
    student_reflection: str = Form(""),
    artifact_file: Optional[UploadFile] = File(None),
):
    """
    Main assessment endpoint. Accepts text + optional file artifact.
    Returns structured Marzano feedback draft for teacher review.
    """
    assessment_id = str(uuid.uuid4())

    # --- Handle file artifact ---
    image_b64 = None
    image_media_type = "image/jpeg"
    file_summary = ""

    if artifact_file and artifact_file.filename:
        content = await artifact_file.read()
        ext = Path(artifact_file.filename).suffix.lower()

        if ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            image_b64 = base64.standard_b64encode(content).decode()
            image_media_type = artifact_file.content_type or "image/jpeg"
            file_summary = f"\n[Image artifact uploaded: {artifact_file.filename}]"

        elif ext == ".pdf":
            # For PDFs without Haystack, include filename note
            # With Haystack, you'd extract text here
            file_summary = f"\n[PDF artifact uploaded: {artifact_file.filename} — text extraction requires Haystack]"

        else:
            file_summary = f"\n[File artifact uploaded: {artifact_file.filename}]"

    # --- Build prompts ---
    system_prompt = build_system_prompt(subject, student_passion, grade_level)

    # Inject RAG context if available
    rag_query = f"{subject} {student_passion} {artifact_description[:200]}"
    rag_context = rag.format_context_block(rag_query)
    if rag_context:
        system_prompt += rag_context

    full_description = artifact_description + file_summary
    user_prompt = build_artifact_prompt(full_description, student_reflection)

    # --- Call AI ---
    try:
        raw_response = await call_ai(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_b64=image_b64,
            image_media_type=image_media_type,
            max_tokens=2500,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI provider error: {str(e)}")

    # --- Parse JSON from AI response ---
    feedback = _extract_json(raw_response)
    if not feedback:
        feedback = {
            "overall_level": "Unable to parse",
            "overall_sublevel": "",
            "strength_summary": raw_response[:500],
            "growth_summary": "",
            "taxonomy_breakdown": [],
            "next_level_prompt": "",
            "standards_connections": [],
            "passion_integration": "",
            "ai_reasoning": "Raw response — JSON parsing failed",
        }

    # --- Persist ---
    record = {
        "id": assessment_id,
        "student_name": student_name,
        "subject": subject,
        "grade_level": grade_level,
        "student_passion": student_passion,
        "artifact_description": artifact_description,
        "student_reflection": student_reflection,
        "has_image": image_b64 is not None,
        "created_at": datetime.utcnow().isoformat(),
        "feedback": feedback,
        "teacher_comments": "",
        "teacher_edited_level": None,
        "approved": False,
        "raw_ai_response": raw_response,
    }

    _save_assessment(assessment_id, record)

    return {
        "assessment_id": assessment_id,
        **record,
    }


@app.get("/assessments")
async def list_assessments() -> List[AssessmentSummary]:
    summaries = []
    for path in sorted(DATA_DIR.glob("*.json"), reverse=True):
        try:
            data = json.loads(path.read_text())
            summaries.append(AssessmentSummary(
                id=data["id"],
                student_name=data["student_name"],
                subject=data["subject"],
                passion=data["student_passion"],
                grade_level=data["grade_level"],
                created_at=data["created_at"],
                overall_level=data["feedback"].get("overall_level", ""),
                approved=data.get("approved", False),
            ))
        except Exception:
            continue
    return summaries


@app.get("/assessments/{assessment_id}")
async def get_assessment(assessment_id: str):
    record = _load_assessment(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")
    return record


@app.patch("/assessments/{assessment_id}")
async def update_assessment(assessment_id: str, edit: TeacherEdit):
    """Teacher saves their edits and approval."""
    record = _load_assessment(assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Assessment not found")

    record["teacher_comments"] = edit.teacher_comments
    record["teacher_edited_level"] = edit.edited_level
    record["approved"] = edit.approved
    record["teacher_updated_at"] = datetime.utcnow().isoformat()

    _save_assessment(assessment_id, record)
    return {"status": "saved", "assessment_id": assessment_id}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _save_assessment(assessment_id: str, data: dict):
    path = DATA_DIR / f"{assessment_id}.json"
    path.write_text(json.dumps(data, indent=2))


def _load_assessment(assessment_id: str) -> Optional[dict]:
    path = DATA_DIR / f"{assessment_id}.json"
    if not path.exists():
        return None
    return json.loads(path.read_text())


def _extract_json(text: str) -> Optional[dict]:
    """Pull JSON object out of AI response, even if wrapped in markdown."""
    text = text.strip()
    # Strip markdown code fences
    for fence in ["```json", "```"]:
        if fence in text:
            text = text.split(fence, 1)[-1]
            text = text.rsplit("```", 1)[0]
            break
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        return json.loads(text[start:end])
    except (ValueError, json.JSONDecodeError):
        return None
