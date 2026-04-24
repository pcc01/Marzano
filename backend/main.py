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
from haystack_pipeline import rag, ingest_document, prewarm, HAYSTACK_AVAILABLE, INDEX_PATH
from curriculum import api_response as curriculum_api, build_curriculum_context, grade_band_for_level
from international import api_response as international_api, build_international_context, COUNTRIES, GRADE_LEVEL_MAP
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

    # Recover jobs that were mid-flight when the server last restarted.
    # Without this they remain stuck in "processing" state forever.
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(IngestionJob).where(IngestionJob.status == "processing")
        )
        stuck = result.scalars().all()
        if stuck:
            for job in stuck:
                job.status = "error"
                job.error_message = (
                    "Server restarted while this job was running — please re-upload."
                )
            await session.commit()
            print(f"[APP] Recovered {len(stuck)} stuck ingestion job(s).")

    # Load persisted RAG index (fast synchronous disk read)
    rag.load()

    # Pre-warm embedding model in the background so the first /ingest
    # does not stall waiting for the model to download.
    asyncio.create_task(prewarm())

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


@app.get("/curriculum")
async def get_curriculum():
    """Full curriculum registry — grade bands and subjects with Marzano targets."""
    return curriculum_api()


@app.get("/curriculum/{grade_band}")
async def get_curriculum_band(grade_band: str):
    """Subjects for a specific grade band, formatted for the assessment form."""
    from curriculum import get_subjects_for_band, GRADE_BANDS
    band = GRADE_BANDS.get(grade_band)
    if not band:
        raise HTTPException(status_code=404, detail=f"Grade band '{grade_band}' not found")
    subjects = get_subjects_for_band(grade_band)
    return {
        "grade_band": grade_band,
        "label": band.label,
        "grade_levels": band.grade_levels,
        "subjects": [
            {
                "name": s.name,
                "strands": s.strands,
                "marzano_entry_point": s.marzano_entry_point,
                "marzano_target": s.marzano_target,
                "common_passions": s.common_passions,
                "description": s.description,
                "standards_framework": s.standards_framework,
            }
            for s in subjects
        ],
    }


@app.get("/international/grades/{us_grade}")
async def get_grade_equivalents(us_grade: str):
    """Return international equivalents for a specific US grade level."""
    equivalents = GRADE_LEVEL_MAP.get(us_grade, {})
    if not equivalents:
        raise HTTPException(status_code=404, detail=f"Grade '{us_grade}' not found")
    return {"us_grade": us_grade, "equivalents": equivalents}

@app.get("/international/marzano/{level}")
async def get_marzano_international_mapping(level: str):
    """Return international framework equivalencies for a Marzano level."""
    from international import MARZANO_TO_INTERNATIONAL
    mapping = MARZANO_TO_INTERNATIONAL.get(level)
    if not mapping:
        raise HTTPException(status_code=404, detail=f"Marzano level '{level}' not found")
    return {"level": level, "mapping": mapping}

@app.get("/international")
async def get_international():
    """
    International grade-level and Marzano taxonomy mapping data.
    Used by the v0.4.0 international classroom feature.
    Returns roadmap data structure while that feature is in development.
    """
    return international_api()


# ─────────────────────────────────────────────────────────────
# Document ingestion (Haystack RAG)
# ─────────────────────────────────────────────────────────────
@app.post("/ingest")
async def ingest_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    doc_type:     str = Form("marzano_reference"),
    state:        str = Form(""),
    grade_band:   str = Form(""),
    subject_area: str = Form(""),
    session: AsyncSession = Depends(get_session),
):
    """
    Upload a PDF/document to the Marzano knowledge base.
    doc_type: "marzano_reference" (general) or "standards" (state/grade specific).
    For "standards" documents, provide state, grade_band, and subject_area tags.
    Returns a job_id immediately; progress arrives via SSE.
    """
    content_bytes = await file.read()
    job_id = str(uuid.uuid4())

    tags = {
        "doc_type":    doc_type,
        "state":       state or None,
        "grade_band":  grade_band or None,
        "subject_area": subject_area or None,
    }

    job = IngestionJob(
        id=job_id,
        filename=file.filename,
        original_size_bytes=len(content_bytes),
        status="pending",
        doc_type=doc_type,
        state=state or None,
        grade_band=grade_band or None,
        subject_area=subject_area or None,
    )
    session.add(job)
    await session.commit()

    background_tasks.add_task(
        _run_ingestion, content_bytes, file.filename, job_id, tags
    )

    return {
        "job_id": job_id,
        "filename": file.filename,
        "size_bytes": len(content_bytes),
        "status": "pending",
        "doc_type": doc_type,
        "tags": tags,
        "message": "Indexing started. Watch SSE stream for progress.",
    }


async def _run_ingestion(content: bytes, filename: str, job_id: str, tags: dict = None):
    tags = tags or {}
    async with AsyncSessionLocal() as session:
        await ingest_document(
            file_bytes=content,
            filename=filename,
            job_id=job_id,
            notify=notif_manager.broadcast,
            db_session=session,
            doc_type=tags.get("doc_type", "marzano_reference"),
            state=tags.get("state"),
            grade_band=tags.get("grade_band"),
            subject_area=tags.get("subject_area"),
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
# Ingestion — additional management endpoints
# ─────────────────────────────────────────────────────────────
@app.post("/ingest/jobs/{job_id}/retry")
async def retry_ingest_job(
    job_id: str,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
):
    """
    Re-queue a failed or stuck job using the same file that was originally
    stored. If the original temp file is gone (normal), instruct the user
    to re-upload. This endpoint primarily resets the DB status and emits
    a clear error notification so the UI reflects reality.
    """
    job = await get_job(session, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status == "processing":
        raise HTTPException(
            status_code=409,
            detail="Job is currently processing. Wait for it to complete or restart the server to recover stuck jobs."
        )
    # Reset status so it shows as actionable in the UI
    await session.execute(
        update(IngestionJob)
        .where(IngestionJob.id == job_id)
        .values(status="pending", error_message=None, chunks_done=0, chunks_total=0)
    )
    await session.commit()
    await notif_manager.broadcast(
        "ingestion_started",
        "Job reset",
        f"'{job.filename}' has been reset to pending. Please re-upload the file to index it.",
        {"job_id": job_id, "filename": job.filename, "progress": 0},
    )
    return {"status": "reset", "job_id": job_id, "message": "Re-upload the file to re-index."}


@app.delete("/ingest/index")
async def clear_index(session: AsyncSession = Depends(get_session)):
    """
    Delete the entire vector index. Useful when starting fresh or after
    indexing the wrong document. Jobs table is NOT cleared.
    """
    try:
        if INDEX_PATH.exists():
            INDEX_PATH.unlink()
        rag._texts   = []
        rag._sources = []
        rag._matrix  = None
        rag.loaded    = False
        rag.doc_count = 0
        await notif_manager.broadcast(
            "ingestion_complete",
            "Index cleared",
            "The knowledge base index has been deleted. Re-upload documents to rebuild it.",
            {"progress": 0, "index_total": 0},
        )
        return {"status": "cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# ─────────────────────────────────────────────────────────────
# Assessments — create
# ─────────────────────────────────────────────────────────────
@app.post("/assess")
async def create_assessment(
    student_name: str = Form(...),
    subject: str = Form(...),
    grade_level: str = Form(...),
    grade_band: str = Form(""),
    student_state: str = Form(""),
    student_passion: str = Form(...),
    artifact_description: str = Form(...),
    student_reflection: str = Form(""),
    submitted_by: str = Form("teacher"),
    country_code: str = Form(""),
    local_grade: str = Form(""),
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

    # Build prompts with curriculum + standards context
    resolved_band = grade_band or grade_band_for_level(grade_level)
    curriculum_ctx = build_curriculum_context(resolved_band, subject)
    system_prompt = build_system_prompt(
        subject, student_passion, grade_level,
        state=student_state or None,
        curriculum_context=curriculum_ctx,
    )
    # International context (if country provided)
    intl_context = ""
    if country_code:
        # Determine Marzano target level from curriculum for framework mapping
        from curriculum import get_subject as _get_subject
        _subj = _get_subject(resolved_band, subject)
        marzano_target = _subj.marzano_target if _subj else None
        intl_context = build_international_context(
            grade_level, country_code, marzano_target=marzano_target
        )
        if local_grade:
            intl_context += f"Student's local grade designation: {local_grade}\n"
        system_prompt += intl_context

    rag_query = f"{subject} {student_passion} {grade_level} {artifact_description[:200]}"
    rag_context = await rag.context_block(
        rag_query,
        state=student_state or None,
        grade_band=resolved_band or None,
        subject_area=subject or None,
    )
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

    # FEATURE 1: Store original AI draft (immutable)
    original_draft = raw

    # FEATURE 2: Generate teacher-only competency assessment
    # This analyzes evidence of meeting state standards (visible ONLY to teachers)
    competency_assessment = await _generate_competency_assessment(
        artifact_description=full_description,
        subject=subject,
        grade_level=grade_level,
        student_reflection=student_reflection,
        feedback=feedback,
        country_code=country_code,
        curriculum_context=curriculum_ctx,
    )

    record = Assessment(
        id=assessment_id,
        student_name=student_name,
        subject=subject,
        grade_level=grade_level,
        student_passion=student_passion,
        artifact_description=artifact_description,
        student_reflection=student_reflection or None,
        country_code=country_code or None,
        local_grade=local_grade or None,
        has_image=has_image,
        has_video=has_video,
        artifact_filename=artifact_filename,
        feedback=feedback,
        raw_ai_response=raw,
        original_ai_draft=original_draft,  # NEW: Store original draft
        competency_assessment=competency_assessment,  # NEW: Store competency assessment
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
        "created_at": record.created_at.isoformat() if record.created_at else datetime.datetime.utcnow().isoformat(),
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
        "country_code": r.country_code,
        "local_grade": r.local_grade,
            "overall_level": (r.feedback or {}).get("overall_level", ""),
            "approved": r.approved,
            "has_video": r.has_video,
            "country_code": r.country_code,
            "local_grade": r.local_grade,
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
    # Teachers can see all fields including competency_assessment and original_ai_draft
    return _assessment_to_dict(record, include_teacher_data=True)


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
    grade_band: str = Form(""),
    student_state: str = Form(""),
    student_passion: str = Form(...),
    artifact_description: str = Form(...),
    student_reflection: str = Form(""),
    country_code: str = Form(""),
    local_grade: str = Form(""),
    artifact_file: Optional[UploadFile] = File(None),
    session: AsyncSession = Depends(get_session),
):
    """
    Student-facing submission endpoint.
    Accepts all the same fields as /assess — including grade_band,
    student_state, country_code, and local_grade — so student submissions
    benefit from the same curriculum context, standards filtering, and
    international context injection as teacher submissions.
    """
    return await create_assessment(
        student_name=student_name,
        subject=subject,
        grade_level=grade_level,
        grade_band=grade_band,
        student_state=student_state,
        student_passion=student_passion,
        artifact_description=artifact_description,
        student_reflection=student_reflection,
        submitted_by="student",
        country_code=country_code,
        local_grade=local_grade,
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
async def _generate_competency_assessment(
    artifact_description: str,
    subject: str,
    grade_level: str,
    student_reflection: Optional[str],
    feedback: dict,
    country_code: Optional[str] = None,
    curriculum_context: Optional[str] = None,
) -> dict:
    """
    FEATURE 2: Generate teacher-only competency assessment.
    
    This parallel AI analysis identifies specific evidence of competency
    regarding state standards. Output is visible ONLY to teachers.
    
    Returns a dict with:
      - standards_evidence: Specific evidence of meeting state standards
      - grade_alignment: How well artifact meets grade-level expectations
      - competency_areas: Key areas of demonstrated competency
      - growth_recommendations: Targeted recommendations for growth
    """
    try:
        # Build competency-specific prompt
        competency_prompt = f"""
You are an expert educator analyzing student work for evidence of competency against state standards.

SUBJECT: {subject}
GRADE LEVEL: {grade_level}
{f'COUNTRY: {country_code}' if country_code else 'COUNTRY: United States'}

STUDENT ARTIFACT:
{artifact_description[:1500]}

{f'STUDENT REFLECTION:\\n{student_reflection}' if student_reflection else ''}

CURRICULUM CONTEXT:
{curriculum_context or 'Standard US curriculum framework'}

PREVIOUS AI FEEDBACK:
Overall Level: {feedback.get('overall_level', 'Unknown')}
Strengths: {feedback.get('strength_summary', '')[:500]}

Your task: Analyze the submission for specific evidence of competency regarding state standards for the defined Grade and Subject.

Provide analysis in JSON format with these fields:
{{
    "standards_evidence": ["List specific evidence items aligned to grade-level standards"],
    "grade_alignment": "Assessment of how well artifact aligns with grade-level expectations",
    "competency_areas": ["Key demonstrated competencies"],
    "growth_recommendations": ["Specific, actionable recommendations for advancing to next level"],
    "rigor_analysis": "Assessment of cognitive demand and rigor",
    "teacher_notes": "Summary notes for teacher review"
}}
"""
        
        # Call AI for competency analysis
        competency_raw = await call_ai(
            system_prompt="You are an expert K-12 educator analyzing student competency against state standards.",
            user_prompt=competency_prompt,
            image_b64=None,
            max_tokens=1500,
        )
        
        # Parse competency assessment
        competency_data = _extract_json(competency_raw) or {
            "standards_evidence": ["Unable to analyze standards evidence"],
            "grade_alignment": "Analysis pending",
            "competency_areas": [],
            "growth_recommendations": ["Please review student work manually"],
            "rigor_analysis": "Analysis pending",
            "teacher_notes": "Competency assessment generation encountered an error",
        }
        
        return competency_data
        
    except Exception as e:
        # Return graceful error state
        return {
            "standards_evidence": [],
            "grade_alignment": f"Error: {str(e)[:200]}",
            "competency_areas": [],
            "growth_recommendations": [],
            "rigor_analysis": "Error in analysis",
            "teacher_notes": f"Competency assessment failed: {str(e)[:300]}",
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


def _assessment_to_dict(r: Assessment, include_teacher_data: bool = False) -> dict:
    """
    Convert Assessment to dict.
    
    Args:
        r: Assessment record
        include_teacher_data: If True, include teacher-only fields like competency_assessment.
                             If False (default), these fields are excluded for student API responses.
    
    Returns:
        Dictionary with assessment data, filtered by role.
    """
    data = {
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
    
    # FEATURE 1: Include original AI draft for teachers (for comparison with edited version)
    if include_teacher_data:
        data["original_ai_draft"] = r.original_ai_draft
    
    # FEATURE 2: Include competency assessment ONLY for teachers
    if include_teacher_data and r.competency_assessment:
        data["competency_assessment"] = r.competency_assessment
    
    return data
