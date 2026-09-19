import re
from datetime import datetime, date
from typing import Optional
from pydantic import BaseModel, ConfigDict, field_validator
from backend.models import ApplicationStatus, RequirementLevel, DocumentType

# shared validators
def _reject_blank(value: str, field_name: str) -> str:
    if not value or not value.strip():
        raise ValueError(f"{field_name} cannot be blank or whitespace-only")
    return value.strip()

def _validate_url(value: Optional[str]) -> Optional[str]:
    if value is None or value == "":
        return None
    if not re.match(r"^https?://", value.strip()):
        raise ValueError("must be a valid http:// or https:// URL")
    return value.strip()

# Skill
class SkillRead(BaseModel):
    id: int
    canonical_name: str
    group: str
    is_ambigous: bool
    model_config = ConfigDict(from_attributes=True)

# JobPostingSkill
class JobPostingSkillRead(BaseModel):
    skill: SkillRead
    requirement_level: RequirementLevel
    evidence_span: Optional[str] = None
    extractor_source: str
    model_config = ConfigDict(from_attributes=True)

# JobPosting
class JobPostingCreate(BaseModel):
    company: str
    role: str
    location: Optional[str] = None
    source_url: Optional[str] = None
    raw_text: str

    @field_validator("company")
    @classmethod
    def company_not_blank(cls, v: str) -> str:
        return _reject_blank(v, "company")

    @field_validator("role")
    @classmethod
    def role_not_blank(cls, v: str) -> str:
        return _reject_blank(v, "role")

    @field_validator("raw_text")
    @classmethod
    def raw_text_not_blank(cls, v: str) -> str:
        return _reject_blank(v, "raw_text")

    @field_validator("source_url")
    @classmethod
    def source_url_valid(cls, v: Optional[str]) -> Optional[str]:
        return _validate_url(v)

class JobPostingRead(BaseModel):
    id: int
    company: str
    role: str
    location: Optional[str]
    source_url: Optional[str]
    raw_text: str
    content_hash: str
    captured_at: datetime
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class JobPostingSummary(BaseModel):
    """Lightweight version for list views (omitting raw_text to keep payloads small)."""
    id: int
    company: str
    role: str
    location: Optional[str]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

# Application
class ApplicationCreate(BaseModel):
    job_posting_id: int
    status: ApplicationStatus = ApplicationStatus.SAVED
    deadline: Optional[date] = None
    date_applied: Optional[date] = None
    notes: Optional[str] = None

class ApplicationUpdate(BaseModel):
    """ Used for PATCH."""
    status: Optional[ApplicationStatus] = None
    deadline: Optional[date] = None
    date_applied: Optional[date] = None
    notes: Optional[str] = None

class ApplicationRead(BaseModel):
    id: int
    job_posting_id: int
    status: ApplicationStatus
    deadline: Optional[date]
    date_applied: Optional[date]
    notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    model_config = ConfigDict(from_attributes=True)

class ApplicationReadWithPosting(ApplicationRead):
    """Used wehn the frontend needs company/role wihtout a second API call."""
    job_posting: JobPostingSummary

# AnalysisRun
class AnalysisRunRead(BaseModel):
    id: int
    job_posting_id: int
    extractor_type: str
    extractor_version: str
    model_name: Optional[str]
    structured_result: dict
    latency_ms: Optional[int]
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class JobDescriptionAnalyzeRequest(BaseModel):
    text: str

class TopGroup(BaseModel):
    group: str
    match_count: int

class JobDescriptionAnalyzeResponse(BaseModel):
    character_count: int
    matched_skills: list[str]
    matched_skills_by_group: dict[str, list[str]]
    top_groups: list[TopGroup]
    suggested_focus: list[str]
    potential_untracked_skills: list[str]

class DocumentRead(BaseModel):
    id: int
    document_type: DocumentType
    title: str
    source_filename: Optional[str]
    content_hash: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)

class SearchResult(BaseModel):
    chunk_id: str
    text: str
    source_type: str
    source_id: int
    rrf_score: float

class SearchRequest(BaseModel):
    query: str
    top_k: int = 5
    source_type: Optional[str] = None