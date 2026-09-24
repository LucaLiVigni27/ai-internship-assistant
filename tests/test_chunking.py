from types import SimpleNamespace
from backend.chunking import chunk_text, compute_chunk_id, build_chunks_for_document, build_chunks_for_job_posting
from backend.models import DocumentType


def test_short_paragraphs_get_merged_into_the_next_paragraph():
    text = "REQUIRED\nPython, SQL, and Docker experience for this role."
    chunks = chunk_text(text, max_chunk_chars=1000, min_chunk_chars=40)
    assert len(chunks) == 1
    assert "REQUIRED" in chunks[0]
    assert "Python, SQL, and Docker experience for this role." in chunks[0]


def test_paragraph_already_above_min_length_is_not_merged_with_its_neighbor():
    first = "A" * 60
    second = "B" * 60
    chunks = chunk_text(f"{first}\n\n{second}", max_chunk_chars=1000, min_chunk_chars=40)
    assert chunks == [first, second]


def test_no_chunk_ever_exceeds_max_chunk_chars():
    text = "word " * 400
    chunks = chunk_text(text, max_chunk_chars=200, min_chunk_chars=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)


def test_oversized_paragraph_splits_on_sentence_boundaries_when_punctuated():
    sentence = "This is one sentence about the role. "
    text = sentence * 40
    chunks = chunk_text(text, max_chunk_chars=200, min_chunk_chars=40)
    assert len(chunks) > 1
    assert all(len(c) <= 200 for c in chunks)
    assert all(c.strip().endswith(".") for c in chunks)


def test_oversized_unpunctuated_paragraph_falls_back_to_bullet_splitting():
    bullets = "".join(f"● Did thing number {i} at the job. " for i in range(20))
    chunks = chunk_text(bullets, max_chunk_chars=150, min_chunk_chars=40)
    assert len(chunks) > 1
    assert all(len(c) <= 150 for c in chunks)


def test_compute_chunk_id_is_deterministic_for_identical_content():
    assert compute_chunk_id("job_posting", 1, 0, "Python required.") == compute_chunk_id("job_posting", 1, 0, "Python required.")


def test_compute_chunk_id_changes_when_content_changes():
    id_a = compute_chunk_id("job_posting", 1, 0, "Python required.")
    id_b = compute_chunk_id("job_posting", 1, 0, "SQL required.")
    assert id_a != id_b


def test_compute_chunk_id_changes_when_source_id_or_index_changes():
    base = compute_chunk_id("job_posting", 1, 0, "same text")
    assert base != compute_chunk_id("job_posting", 2, 0, "same text")
    assert base != compute_chunk_id("job_posting", 1, 1, "same text")


def test_build_chunks_for_job_posting_tags_source_type_and_metadata():
    posting = SimpleNamespace(id=7, raw_text="Python and SQL required.", company="Acme", role="Intern")
    chunks = build_chunks_for_job_posting(posting)
    assert len(chunks) == 1
    assert chunks[0].metadata["source_type"] == "job_posting"
    assert chunks[0].metadata["source_id"] == 7
    assert chunks[0].metadata["company"] == "Acme"


def test_build_chunks_for_document_tags_source_type_and_metadata():
    document = SimpleNamespace(id=3, raw_text="Python, SQL, Docker.", document_type=DocumentType.RESUME, title="My Resume")
    chunks = build_chunks_for_document(document)
    assert len(chunks) == 1
    assert chunks[0].metadata["source_type"] == "document"
    assert chunks[0].metadata["source_id"] == 3
    assert chunks[0].metadata["document_type"] == "resume"
