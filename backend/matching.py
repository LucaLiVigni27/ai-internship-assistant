"""
Matches a JobPosting against the user's Documents (resumes/projects): skill
overlap (matched/missing required & preferred) plus a grounded, cited
explanation of the match.
"""

from collections.abc import Mapping
from typing import Any, Protocol
from sqlalchemy.orm import Session
from backend.models import JobPosting, Document
from backend.skill_matcher import analyze_text
from backend.vector_store import index_job_posting, index_document, get_collection
from backend.answer_generation import generate_answer


class _HasRawText(Protocol):
    raw_text: str


def _skill_names(db: Session, text: str, levels: set[str] | None = None) -> set[str]:
    findings = analyze_text(text, db)
    if levels is not None:
        findings = [f for f in findings if f.requirement_level in levels]
    return {f.canonical_name for f in findings}


def compute_skill_overlap(db: Session, job_posting: _HasRawText, documents: list[Document]) -> dict:
    """
    Required/preferred skills from the posting vs. the union of skills found
    across all given documents.
    """
    required = _skill_names(db, job_posting.raw_text, levels={"required"})
    preferred = _skill_names(db, job_posting.raw_text, levels={"preferred"})

    candidate_skills: set[str] = set()
    for document in documents:
        candidate_skills |= _skill_names(db, document.raw_text)

    matched_required = sorted(required & candidate_skills)
    missing_required = sorted(required - candidate_skills)
    matched_preferred = sorted(preferred & candidate_skills)
    missing_preferred = sorted(preferred - candidate_skills)

    match_score = len(matched_required) / len(required) if required else None

    return {
        "matched_required_skills": matched_required,
        "missing_required_skills": missing_required,
        "matched_preferred_skills": matched_preferred,
        "missing_preferred_skills": missing_preferred,
        "match_score": match_score,
        "total_required": len(required),
        "total_preferred": len(preferred),
    }


def _rows_to_chunks(rows: Mapping[str, Any]) -> list[dict]:
    return [
        {"chunk_id": chunk_id, "text": text, "source_type": metadata.get("source_type"), "source_id": metadata.get("source_id")}
        for chunk_id, text, metadata in zip(rows["ids"], rows["documents"], rows["metadatas"])
    ]


def _match_context_chunks(job_posting: JobPosting, documents: list[Document]) -> list[dict]:
    index_job_posting(job_posting)
    for document in documents:
        index_document(document)

    collection = get_collection()
    chunks = _rows_to_chunks(
        collection.get(where={"$and": [{"source_type": "job_posting"}, {"source_id": job_posting.id}]})
    )
    for document in documents:
        chunks.extend(
            _rows_to_chunks(
                collection.get(where={"$and": [{"source_type": "document"}, {"source_id": document.id}]})
            )
        )
    return chunks


def match_job_posting(db: Session, job_posting: JobPosting, documents: list[Document]) -> dict:
    overlap = compute_skill_overlap(db, job_posting, documents)

    query = f"How does this candidate's background match the {job_posting.role} requirements at {job_posting.company}?"
    retrieved_chunks = _match_context_chunks(job_posting, documents)
    explanation = generate_answer(query, retrieved_chunks=retrieved_chunks)

    return {
        **overlap,
        "document_ids": [document.id for document in documents],
        "answer": explanation["answer"],
        "citations": explanation["citations"],
        "sufficient_context": explanation["sufficient_context"],
    }
