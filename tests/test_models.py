from sqlalchemy.exc import IntegrityError
import pytest
from backend.models import JobPosting, Document, DocumentType


def test_compute_content_hash_is_deterministic():
    assert JobPosting.compute_content_hash("Python and SQL.") == JobPosting.compute_content_hash("Python and SQL.")


def test_compute_content_hash_ignores_surrounding_whitespace():
    assert JobPosting.compute_content_hash("Python.") == JobPosting.compute_content_hash("  Python.  \n")


def test_compute_content_hash_differs_for_different_text():
    assert JobPosting.compute_content_hash("Python.") != JobPosting.compute_content_hash("SQL.")


def test_document_hash_uses_the_same_scheme_as_job_posting():
    assert Document.compute_content_hash("Resume text.") == JobPosting.compute_content_hash("Resume text.")


def test_job_posting_content_hash_is_unique_at_the_db_level(db_session):
    hash_value = JobPosting.compute_content_hash("Duplicate text.")
    db_session.add(JobPosting(company="A", role="Intern", raw_text="Duplicate text.", content_hash=hash_value))
    db_session.commit()

    db_session.add(JobPosting(company="B", role="Intern", raw_text="Duplicate text.", content_hash=hash_value))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


def test_document_content_hash_is_unique_at_the_db_level(db_session):
    hash_value = Document.compute_content_hash("Resume body.")
    db_session.add(Document(document_type=DocumentType.RESUME, title="A", raw_text="Resume body.", content_hash=hash_value))
    db_session.commit()

    db_session.add(Document(document_type=DocumentType.RESUME, title="B", raw_text="Resume body.", content_hash=hash_value))
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()
