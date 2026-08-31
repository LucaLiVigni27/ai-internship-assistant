from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
from backend.database import Base, engine, get_db
from backend.models import JobPosting, Application
from backend.job_analyzer import analyze_job_description
from backend.schemas import (
    JobPostingCreate,
    JobPostingRead,
    JobPostingSummary,
    ApplicationCreate,
    ApplicationRead,
    ApplicationReadWithPosting,
    ApplicationUpdate,
    JobDescriptionAnalyzeRequest,
    JobDescriptionAnalyzeResponse,
)

# Base.metadata.create_all(bind=engine) 
# Remove once Alembice is created

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
@app.post("/job-descriptions/analyze", response_model=JobDescriptionAnalyzeResponse)
def analyze_job_description_endpoint(payload: JobDescriptionAnalyzeRequest):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="Job description text is required")
    return analyze_job_description(payload.text)