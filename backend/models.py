import enum
import hashlib
from datetime import datetime, date
from sqlalchemy import (
    DateTime, Date, Integer, String, Text, Boolean, JSON, Enum as SAEnum, ForeignKey, UniqueConstraint,
)
from sqlalchemy.orm import relationship, Mapped, mapped_column
from sqlalchemy.sql import func
from backend.database import Base

class ApplicationStatus(str, enum.Enum):
    SAVED = "saved"
    APPLIED = "applied"
    INTERVIEWING = "interviewing"
    OFFER = "offer"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"

class RequirementLevel(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"
    MENTIONED = "mentioned"

class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    canonical_name: Mapped[str] = mapped_column(String(80), nullable=False, unique=True, index=True)
    aliases: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    group: Mapped[str] = mapped_column(String(60), nullable=False)
    is_ambiguous: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    requires_case_sensitive: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    job_posting_links: Mapped[list["JobPostingSkill"]] = relationship("JobPostingSkill", back_populates="skill")

class JobPosting(Base):
    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    company: Mapped[str] = mapped_column(String(120), nullable=False)
    role: Mapped[str] = mapped_column(String(180), nullable=False)
    location: Mapped[str | None] = mapped_column(String(120), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    applications: Mapped[list["Application"]] = relationship("Application", back_populates="job_posting", cascade="all, delete-orphan")
    skill_links: Mapped[list["JobPostingSkill"]] = relationship("JobPostingSkill", back_populates="job_posting", cascade="all, delete-orphan")
    analysis_runs: Mapped[list["AnalysisRun"]] = relationship("AnalysisRun", back_populates="job_posting", cascade="all, delete-orphan")

    @staticmethod
    def compute_content_hash(raw_text: str) -> str:
        return hashlib.sha256(raw_text.strip().encode("utf-8")).hexdigest()

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_posting_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_postings.id"), nullable=False)
    status: Mapped[ApplicationStatus] = mapped_column(SAEnum(ApplicationStatus), nullable=False, default=ApplicationStatus.SAVED)
    deadline: Mapped[date | None] = mapped_column(Date, nullable=True)
    date_applied: Mapped[date | None] = mapped_column(Date, nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=True)

    job_posting: Mapped["JobPosting"] = relationship("JobPosting", back_populates="applications")

class JobPostingSkill(Base):
    __tablename__ = "job_posting_skills"
    __table_args__ = (UniqueConstraint("job_posting_id", "skill_id", "extractor_source", name="uq_posting_skill_extractor"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_posting_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_postings.id"), nullable=False)
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id"), nullable=False)
    requirement_level: Mapped[RequirementLevel] = mapped_column(SAEnum(RequirementLevel), nullable=False, default=RequirementLevel.MENTIONED)
    evidence_span: Mapped[str | None] = mapped_column(Text, nullable=True)
    extractor_source: Mapped[str] = mapped_column(String(20), nullable=False)

    job_posting: Mapped["JobPosting"] = relationship("JobPosting", back_populates="skill_links")
    skill: Mapped["Skill"] = relationship("Skill", back_populates="job_posting_links")

class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    job_posting_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_postings.id"), nullable=False)
    extractor_type: Mapped[str] = mapped_column(String(20), nullable=False)
    extractor_version: Mapped[str] = mapped_column(String(20), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(60), nullable=True)
    structured_result: Mapped[dict] = mapped_column(JSON, nullable=False)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=True)

    job_posting: Mapped["JobPosting"] = relationship("JobPosting", back_populates="analysis_runs")

