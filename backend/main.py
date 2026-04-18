"""
Marzano Assessment API — full build
Features: PostgreSQL, multi-modal artifacts, video, Haystack RAG,
          SSE notifications, teacher dashboard, student portal.
"""

import asyncio
import base64
import json
import os
import uuid
import datetime
from pathlib import Path
from typing import Optional, AsyncGenerator

from fastapi import (
    FastAPI, File, Form, UploadFile, HTTPException,
    Depends, BackgroundTasks, Request
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from database import (
    init_db, get_session, AsyncSessionLocal,
    Assessment, IngestionJob, Notification,
    get_assessment, list_assessments, get_job, list_jobs,
    list_notifications,
)
from marzano_framework import (
    build_system_prompt, build_artifact_prompt,
    TAXONOMY, PASSION_MATH_CONNECTIONS,
)
from ai_provider import call_ai, get_provider_info
from haystack_pipeline import rag, ingest_document, HAYSTACK_AVAILABLE
from notifications import notif_manager, sse_event_generator
from video_handler import process_video, is_video_file

# ─────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="Marzano Assessment API",
    description="AI-powered assessment grounded in Marzano's New Taxonomy",
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup():
    await init_db()
    # Load RAG index if it exists
    rag.load()
    print("[APP] Ready.")


# ─────────────────────────────────────────────────────────────
# SSE — real-time notifications
# ─────────────────────────────────────────────────────────────
@app.get("/notifications/stream")
async def notification_stream(request: Request):
    """
    SSE endpoint. Browser connects once; server pushes events.
    Each tab gets a unique client_id.
    """
    client_id = str(uuid.uuid4())

    async def generator():
        async for chunk in sse_event_generator(client_id):
            if await request.is_disconnected():
                break
            yield chunk

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/notifications")
async def get_notifications(
    unread_only: bool = False,
    session: AsyncSession = Depends(get_session)
):
    notifs = await list_notifications(session, unread_only=unread_only)
    return [
        {
            "id": n.id,
            "type": n.type,
            "title": n.title,
            "body": n.body,
            "payload": n.payload,
            "read": n.read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifs
    ]


@app.patch("/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: str,
    session: AsyncSession = Depends(get_session),
):
    await session.execute(
        update(Notification)
        .where(Notification.id == notification_id)
        .values(read=True)
    )
    await session.commit()
    return {"status": "ok"}


@app.post("/notifications/mark-all-read")
async def mark_all_read(session: AsyncSession = Depends(get_session)):
    await session.execute(update(Notification).values(read=True))
    await session.commit()
    return {"status": "ok"}


# ─────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "ai": get_provider_info(),
        "rag": {
            "available": HAYSTACK_AVAILABLE,
            "loaded": rag.loaded,
            "doc_count": rag.doc_count,
        },
        "sse_clients": notif_manager.subscriber_count(),
        "version": "0.2.0",
    }


# ─────────────────────────────────────────────────────────────
# Taxonomy + passions reference
# ─────────────────────────────────────────────────────────────
@app.get("/taxonomy")
async def get_taxonomy():
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


# ─────────────────────────────────────────────────────────────
# Document ingestion (Haystack RAG)
# ─────────────────────────────────────────────────────────────
@app.post("/ingest")
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload a PDF/document to the Marzano knowledge base.
    Returns a job_id immediately; progress arrives via SSE.
    """
    content = await file.read()
    job_id = str(uuid.uuid4())

    job = IngestionJob(
        id=job_id,
        filename=file.filename,
        original_size_bytes=len(content),
        status="pending",
    )
    session.add(job)
    await session.commit()

    # Run ingestion as a background task so we return immediately
    background_tasks.add_task(
        _run_ingestion, content, file.filename, job_id
    )

    return {
        "job_id": job_id,
        "filename": file.filename,
        "size_bytes": len(content),
        "status": "pending",
        "message": "Indexing started. Watch SSE stream for progress.",
    }


async def _run_ingestion(content: bytes, filename: str, job_id: str):
    async with AsyncSessionLocal() as session:
        await ingest_document(
            file_bytes=content,
            filename=filename,
            job_id=job_id,
            notify=notif_manager.broadcast,
            db_session=session,
        )


@app.get("/ingest/jobs")
async def list_ingest_jobs(session: AsyncSession = Depends(get_session)):
    jobs = await list_jobs(session)
    return [
        {
            "id": j.id,
            "filename": j.filename,
            "size_kb": round(j.original_size_bytes / 1024, 1),
            "status": j.status,
            "chunks_total": j.chunks_total,
            "chunks_done": j.chunks_done,
            "error_message": j.error_message,
            "created_at": j.created_at.isoformat(),
            "completed_at": j.completed_at.isoformat() if j.completed_at else None,
        }
        for j in jobs
    ]


@app.get("/ingest/jobs/{job_id}")
async def get_ingest_job(job_id: str, session: AsyncSession = Depends(get_session)):
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return {
        "id": job.id,
        "filename": job.filename,
        "status": job.status,
        "chunks_total": job.chunks_total,
        "chunks_done": job.chunks_done,
        "error_message": job.error_message,
        "created_at": job.created_at.isoformat(),
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
    }


@app.get("/ingest/status")
async def rag_status():
    return {
        "haystack_available": HAYSTACK_AVAILABLE,
        "index_loaded": rag.loaded,
        "doc_count": rag.doc_count,
    }


# ─────────────────────────────────────────────────────────────
# Assessments — create
# ─────────────────────────────────────────────────────────────
@app.post("/assess")
async def create_assessment(
    student_name: str = Form(...),
    subject: str = Form(...),
    grade_level: str = Form(...),
    student_passion: str = Form(...),
    artifact_description: str = Form(...),
    student_reflection: str = Form(""),
    submitted_by: str = Form("teacher"),
    artifact_file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Accept a student artifact (text + optional file/video),
    generate Marzano-aligned AI feedback, persist to PostgreSQL.
    """
    assessment_id = str(uuid.uuid4())

    image_b64 = None
    image_media_type = "image/jpeg"
    file_notes = ""
    has_image = False
    has_video = False
    artifact_filename = None

    if artifact_file and artifact_file.filename:
        content = await artifact_file.read()
        filename = artifact_file.filename
        artifact_filename = filename
        ext = Path(filename).suffix.lower()

        if is_video_file(filename):
            has_video = True
            video_result = await process_video(content, filename)
            file_notes = video_result["summary_for_prompt"]
            if video_result["frames_b64"]:
                # Use the first frame as the primary image for the AI
                image_b64 = video_result["frames_b64"][0]
                image_media_type = "image/jpeg"
                has_image = True
                file_notes += f"\n[{len(video_result['frames_b64'])} frames extracted for analysis]"

        elif ext in {".jpg", ".jpeg", ".png", ".gif", ".webp"}:
            has_image = True
            image_b64 = base64.standard_b64encode(content).decode()
            image_media_type = artifact_file.content_type or "image/jpeg"
            file_notes = f"[Image: {filename}]"

        elif ext == ".pdf":
            # Use Haystack to extract text from the submitted PDF
            if HAYSTACK_AVAILABLE:
                extracted = _extract_pdf_text(content, filename)
                file_notes = f"[PDF artifact: {filename}]\n{extracted[:2000]}"
            else:
                file_notes = f"[PDF artifact uploaded: {filename}]"

        else:
            file_notes = f"[File artifact: {filename}]"

    # Build prompts
    system_prompt = build_system_prompt(subject, student_passion, grade_level)
    rag_context = rag.context_block(f"{subject} {student_passion} {artifact_description[:200]}")
    if rag_context:
        system_prompt += rag_context

    full_description = artifact_description + ("\n" + file_notes if file_notes else "")
    user_prompt = build_artifact_prompt(full_description, student_reflection)

    try:
        raw = await call_ai(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            image_b64=image_b64,
            image_media_type=image_media_type,
            max_tokens=2500,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"AI error: {e}")

    feedback = _extract_json(raw) or {
        "overall_level": "Parse error",
        "overall_sublevel": "",
        "strength_summary": raw[:500],
        "growth_summary": "",
        "taxonomy_breakdown": [],
        "next_level_prompt": "",
        "standards_connections": [],
        "passion_integration": "",
        "ai_reasoning": "JSON extraction failed — raw response shown",
    }

    record = Assessment(
        id=assessment_id,
        student_name=student_name,
        subject=subject,
        grade_level=grade_level,
        student_passion=student_passion,
        artifact_description=artifact_description,
        student_reflection=student_reflection or None,
        has_image=has_image,
        has_video=has_video,
        artifact_filename=artifact_filename,
        feedback=feedback,
        raw_ai_response=raw,
        submitted_by=submitted_by,
    )
    session.add(record)
    await session.commit()

    # Notify teacher dashboard that a new assessment is ready
    await notif_manager.broadcast(
        event_type="assessment_ready",
        title="New assessment ready",
        body=f"{student_name} ({grade_level}) — {subject} · Highest level: {feedback.get('overall_level', '?')}",
        payload={"assessment_id": assessment_id, "student_name": student_name},
    )

    return {
        "assessment_id": assessment_id,
        "student_name": student_name,
        "subject": subject,
        "grade_level": grade_level,
        "student_passion": student_passion,
        "artifact_description": artifact_description,
        "student_reflection": student_reflection,
        "has_image": has_image,
        "has_video": has_video,
        "artifact_filename": artifact_filename,
        "feedback": feedback,
        "teacher_comments": "",
        "approved": False,
        "submitted_by": submitted_by,
        "created_at": record.created_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Assessments — list / get / update
# ─────────────────────────────────────────────────────────────
@app.get("/assessments")
async def list_all_assessments(session: AsyncSession = Depends(get_session)):
    records = await list_assessments(session)
    return [
        {
            "id": r.id,
            "student_name": r.student_name,
            "subject": r.subject,
            "grade_level": r.grade_level,
            "passion": r.student_passion,
            "submitted_by": r.submitted_by,
            "overall_level": (r.feedback or {}).get("overall_level", ""),
            "approved": r.approved,
            "has_video": r.has_video,
            "created_at": r.created_at.isoformat(),
        }
        for r in records
    ]


@app.get("/assessments/{assessment_id}")
async def get_one_assessment(
    assessment_id: str,
    session: AsyncSession = Depends(get_session),
):
    record = await get_assessment(session, assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return _assessment_to_dict(record)


class TeacherEdit(BaseModel):
    assessment_id: str
    teacher_comments: str
    edited_level: Optional[str] = None
    approved: bool = False


@app.patch("/assessments/{assessment_id}")
async def update_assessment(
    assessment_id: str,
    edit: TeacherEdit,
    session: AsyncSession = Depends(get_session),
):
    record = await get_assessment(session, assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")

    record.teacher_comments = edit.teacher_comments
    record.teacher_edited_level = edit.edited_level
    record.approved = edit.approved
    record.teacher_updated_at = datetime.datetime.utcnow()
    await session.commit()

    if edit.approved:
        await notif_manager.broadcast(
            "assessment_approved",
            "Assessment approved",
            f"{record.student_name}'s assessment has been reviewed and approved.",
            {"assessment_id": assessment_id, "student_name": record.student_name},
            persist=True,
        )

    return {"status": "saved", "assessment_id": assessment_id}


# ─────────────────────────────────────────────────────────────
# Student portal — submit without teacher login
# ─────────────────────────────────────────────────────────────
@app.post("/student/submit")
async def student_submit(
    student_name: str = Form(...),
    subject: str = Form(...),
    grade_level: str = Form(...),
    student_passion: str = Form(...),
    artifact_description: str = Form(...),
    student_reflection: str = Form(""),
    artifact_file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Student-facing submission endpoint.
    Identical to /assess but sets submitted_by='student'.
    Teachers see a badge on these in the dashboard.
    """
    # Reuse the assess logic by delegating
    return await create_assessment(
        student_name=student_name,
        subject=subject,
        grade_level=grade_level,
        student_passion=student_passion,
        artifact_description=artifact_description,
        student_reflection=student_reflection,
        submitted_by="student",
        artifact_file=artifact_file,
        session=session,
    )


@app.get("/student/status/{assessment_id}")
async def student_check_status(
    assessment_id: str,
    session: AsyncSession = Depends(get_session),
):
    """Students can check if their submission has been reviewed."""
    record = await get_assessment(session, assessment_id)
    if not record:
        raise HTTPException(status_code=404, detail="Not found")
    return {
        "assessment_id": assessment_id,
        "student_name": record.student_name,
        "subject": record.subject,
        "approved": record.approved,
        "status": "reviewed" if record.approved else "pending_review",
        "submitted_at": record.created_at.isoformat(),
    }


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────
def _extract_pdf_text(content: bytes, filename: str) -> str:
    """Extract raw text from a PDF using pypdf (no embeddings)."""
    try:
        import tempfile, os
        from haystack.components.converters import PyPDFToDocument
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name
        converter = PyPDFToDocument()
        result = converter.run(sources=[tmp_path])
        os.unlink(tmp_path)
        text = " ".join(d.content for d in result["documents"])
        return text
    except Exception as e:
        return f"[PDF text extraction failed: {e}]"


def _extract_json(text: str) -> Optional[dict]:
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


def _assessment_to_dict(r: Assessment) -> dict:
    return {
        "id": r.id,
        "student_name": r.student_name,
        "subject": r.subject,
        "grade_level": r.grade_level,
        "student_passion": r.student_passion,
        "artifact_description": r.artifact_description,
        "student_reflection": r.student_reflection,
        "has_image": r.has_image,
        "has_video": r.has_video,
        "artifact_filename": r.artifact_filename,
        "feedback": r.feedback,
        "teacher_comments": r.teacher_comments or "",
        "teacher_edited_level": r.teacher_edited_level,
        "approved": r.approved,
        "submitted_by": r.submitted_by,
        "created_at": r.created_at.isoformat(),
        "teacher_updated_at": r.teacher_updated_at.isoformat() if r.teacher_updated_at else None,
    }
