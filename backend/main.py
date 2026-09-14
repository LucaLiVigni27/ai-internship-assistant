import time
import tempfile
import os
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session, joinedload
from backend.database import get_db
from backend.models import JobPosting, Application, JobPostingSkill, RequirementLevel, AnalysisRun, Document, DocumentType
from backend.skill_matcher import analyze_text, detect_sections, build_structured_result, get_primary_evidence
from backend.schemas import (
    JobPostingCreate,
    JobPostingRead,
    JobPostingSummary,
    ApplicationCreate,
    ApplicationRead,
    ApplicationReadWithPosting,
    ApplicationUpdate,
    AnalysisRunRead,
    JobDescriptionAnalyzeRequest,
    DocumentRead,
) 
from backend.document_extraction import extract_text_from_file

ANALYZER_VERSION = "regex-v1.1"

app = FastAPI(
    title="AI Internship Assistant API",
    description="Backend API for tracking internships and powering RAG search.",
    version="0.2.0"
)

# JobPosting
@app.get("/")
def root():
    return {"message": "AI Internship Assistant API is running"}

@app.get("/health")
def health_check():
    return{"status": "ok"}

@app.post("/job-postings", response_model=JobPostingRead)
def create_job_posting(payload: JobPostingCreate, db: Session = Depends(get_db)):
    content_hash = JobPosting.compute_content_hash(payload.raw_text)

    existing = (
        db.query(JobPosting)
        .filter(JobPosting.content_hash == content_hash)
        .first()
    )
    if existing is not None:
        # Idempotent: re-saving the same posting text returns the existing row
        return existing

    job_posting = JobPosting(
        company=payload.company,
        role=payload.role,
        location=payload.location,
        source_url = payload.source_url,
        raw_text = payload.raw_text,
        content_hash = content_hash,
    )
    db.add(job_posting)
    db.commit()
    db.refresh(job_posting)
    return job_posting

@app.get("/job-postings", response_model=list[JobPostingSummary])
def list_job_postings(db: Session = Depends(get_db)):
    return (
        db.query(JobPosting)
        .order_by(JobPosting.created_at.desc())
        .all()
    )

@app.get("/job-postings/{job_posting_id}", response_model=JobPostingRead)
def get_job_posting(job_posting_id: int, db: Session = Depends(get_db)):
    job_posting = db.query(JobPosting). filter(JobPosting.id == job_posting_id).first()
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    return job_posting

@app.delete("/job-postings/{job_posting_id}")
def delete_job_posting(job_posting_id: int, db: Session = Depends(get_db)):
    job_posting = db.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")
    db.delete(job_posting)
    db.commit()
    return {"message": "Job posting deleted"}

# Application
@app.post("/applications", response_model=ApplicationRead)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)):
    job_posting = (
        db.query(JobPosting).filter(JobPosting.id == payload.job_posting_id).first()
    )
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")

    application = Application(**payload.model_dump())
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@app.get("/applications", response_model=list[ApplicationReadWithPosting])
def list_applications(db: Session = Depends(get_db)):
    return (
        db.query(Application)
        .options(joinedload(Application.job_posting))
        .order_by(Application.created_at.desc())
        .all()
    )


@app.get("/applications/{application_id}", response_model=ApplicationReadWithPosting)
def get_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@app.patch("/applications/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: int, payload: ApplicationUpdate, db: Session = Depends(get_db)
):
    application = db.query(Application).filter(Application.id == application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(application, field, value)

    db.commit()
    db.refresh(application)
    return application


@app.delete("/applications/{application_id}")
def delete_application(application_id: int, db: Session = Depends(get_db)):
    application = db.query(Application).filter(Application.id == application_id).first()
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")

    db.delete(application)
    db.commit()
    return {"message": "Application deleted"}

# Analyzer
@app.post("/job-postings/{job_posting_id}/analyze", response_model=AnalysisRunRead)
def analyze_job_posting(job_posting_id: int, db: Session = Depends(get_db)):
    job_posting = db.query(JobPosting).filter(JobPosting.id == job_posting_id).first()
    if job_posting is None:
        raise HTTPException(status_code=404, detail="Job posting not found")

    start_time = time.perf_counter()
    findings = analyze_text(job_posting.raw_text, db)
    sections = detect_sections(job_posting.raw_text)
    structured_result = build_structured_result(job_posting.raw_text, findings, sections)
    latency_ms = int((time.perf_counter() - start_time) * 1000)

    db.query(JobPostingSkill).filter(
        JobPostingSkill.job_posting_id == job_posting_id,
        JobPostingSkill.extractor_source == "regex",
    ).delete()

    for f in findings:
        db.add(
            JobPostingSkill(
                job_posting_id=job_posting_id,
                skill_id=f.skill_id,
                requirement_level=RequirementLevel(f.requirement_level),
                evidence_span=get_primary_evidence(job_posting.raw_text, f),
                extractor_source="regex",
            )
        )

    analysis_run = AnalysisRun(
        job_posting_id=job_posting_id,
        extractor_type="regex",
        extractor_version=ANALYZER_VERSION,
        model_name=None,
        structured_result=structured_result,
        latency_ms=latency_ms,
    )
    db.add(analysis_run)
    db.commit()
    db.refresh(analysis_run)
    return analysis_run

@app.post("/job-descriptions/analyze")
def analyze_job_description_endpoint(
    payload: JobDescriptionAnalyzeRequest, db: Session = Depends(get_db)
):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Job description text is required")

    findings = analyze_text(payload.text, db)
    sections = detect_sections(payload.text)
    return build_structured_result(payload.text, findings, sections)

# Document Upload
@app.post("/documents/upload", response_model=DocumentRead)
async def upload_document(
    file: UploadFile = File(...),
    document_type: DocumentType = Form(...),
    title: str = Form(...),
    db: Session = Depends(get_db),
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Uploaded file must have a filename")

    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file.filename).suffix) as tmp:
        contents = await file.read()
        tmp.write(contents)
        tmp_path = tmp.name

    try:
        raw_text = extract_text_from_file(tmp_path, file.filename)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        os.unlink(tmp.name)

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="No extractable text found in file")

    content_hash = Document.compute_content_hash(raw_text)
    existing = db.query(Document).filter(Document.content_hash == content_hash).first()
    if existing is not None:
        return existing
    
    document = Document(
        document_type=document_type,
        title=title,
        raw_text=raw_text,
        source_filename=file.filename,
        content_hash=content_hash,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document

@app.get("/documents", response_model=list[DocumentRead])
def list_documents (document_type: DocumentType | None = None, db: Session = Depends(get_db)):
    query = db.query(Document)
    if document_type is not None:
        query = query.filter(Document.document_type == document_type)
    return query.order_by(Document.created_at.desc()).all()

@app.get("/documents/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_db)):
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return document

@app.delete("/documents/{document_id}")
def delete_document(document_id: int, db: Session = Depends(get_db)):
    # NOTE: Currently, this only deletes the SQL row. Once documents are chunked and embedded into Chroma, need to update this to also remove associated chunks/embeddings
    document = db.query(Document).filter(Document.id == document_id).first()
    if document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    db.delete(document)
    db.commit()
    return {"message": "Document deleted"}

