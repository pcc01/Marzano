"""
PostgreSQL database layer — SQLAlchemy 2.0 async style.
Tables: assessments, ingestion_jobs, notifications
"""

import os
import uuid
import datetime
from typing import Optional, Any

from sqlalchemy import (
    String, Text, Boolean, Integer, DateTime, JSON,
    func, select, update
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.ext.asyncio import (
    AsyncSession, create_async_engine, async_sessionmaker
)

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://marzano:marzano@postgres:5432/marzano"
)

engine = create_async_engine(DATABASE_URL, echo=False, pool_pre_ping=True)
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────
# Assessment
# ─────────────────────────────────────────
class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_name: Mapped[str] = mapped_column(String(200))
    subject: Mapped[str] = mapped_column(String(200))
    grade_level: Mapped[str] = mapped_column(String(50))
    student_passion: Mapped[str] = mapped_column(String(100))
    artifact_description: Mapped[str] = mapped_column(Text)
    student_reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    has_image: Mapped[bool] = mapped_column(Boolean, default=False)
    has_video: Mapped[bool] = mapped_column(Boolean, default=False)
    artifact_filename: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)

    # AI feedback (stored as JSON)
    feedback: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    raw_ai_response: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # FEATURE 1: AI Artifact Retention
    # Immutable copy of the original AI-generated draft before any teacher intervention
    original_ai_draft: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # FEATURE 2: Teacher-Only Competency Assessment
    # Parallel AI assessment identifying evidence of meeting state standards (visible ONLY to teachers)
    competency_assessment: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    # Teacher review
    teacher_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    teacher_edited_level: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)

    # International classroom context
    country_code: Mapped[Optional[str]] = mapped_column(String(10),  nullable=True)
    local_grade:  Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Submission source
    submitted_by: Mapped[str] = mapped_column(String(20), default="teacher")  # teacher | student

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    teacher_updated_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )


# ─────────────────────────────────────────
# Ingestion Job (Haystack PDF/doc indexing)
# ─────────────────────────────────────────
class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename: Mapped[str] = mapped_column(String(300))
    original_size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    # pending | processing | complete | error

    chunks_total: Mapped[int] = mapped_column(Integer, default=0)
    chunks_done: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Metadata tags applied to all chunks from this document
    doc_type:     Mapped[Optional[str]] = mapped_column(String(30),  nullable=True, default="marzano_reference")
    state:        Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    grade_band:   Mapped[Optional[str]] = mapped_column(String(50),  nullable=True)
    subject_area: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )
    completed_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime, nullable=True
    )


# ─────────────────────────────────────────
# Notification (persisted for history)
# ─────────────────────────────────────────
class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type: Mapped[str] = mapped_column(String(50))   # ingestion_progress | ingestion_complete | assessment_ready | error
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=datetime.datetime.utcnow
    )


# ─────────────────────────────────────────
# DB lifecycle helpers
# ─────────────────────────────────────────
async def init_db():
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session


# ─────────────────────────────────────────
# Query helpers
# ─────────────────────────────────────────
async def get_assessment(session: AsyncSession, assessment_id: str) -> Optional[Assessment]:
    result = await session.execute(
        select(Assessment).where(Assessment.id == assessment_id)
    )
    return result.scalar_one_or_none()


async def list_assessments(session: AsyncSession, limit: int = 100) -> list[Assessment]:
    result = await session.execute(
        select(Assessment).order_by(Assessment.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def get_job(session: AsyncSession, job_id: str) -> Optional[IngestionJob]:
    result = await session.execute(
        select(IngestionJob).where(IngestionJob.id == job_id)
    )
    return result.scalar_one_or_none()


async def list_jobs(session: AsyncSession, limit: int = 50) -> list[IngestionJob]:
    result = await session.execute(
        select(IngestionJob).order_by(IngestionJob.created_at.desc()).limit(limit)
    )
    return list(result.scalars().all())


async def list_notifications(session: AsyncSession, unread_only: bool = False) -> list[Notification]:
    q = select(Notification).order_by(Notification.created_at.desc()).limit(50)
    if unread_only:
        q = q.where(Notification.read == False)
    result = await session.execute(q)
    return list(result.scalars().all())
