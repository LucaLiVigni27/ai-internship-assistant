import hashlib
from dataclasses import dataclass

@dataclass
class Chunk:
    chunk_id: str
    text: str
    chunk_index: int
    metadata: dict

def chunk_text(raw_text: str, max_chunk_chars: int = 1000) -> list[str]:
    """
    Splits text along paragraph boundaries first. Any paragraph still longer than max_chunk_chars get split at sentence boundaries instead.
    Avoids cutting at mid-sentence!
    """
    paragraphs = [p.strip() for p in raw_text.split("\n\n") if p.strip()]
    chunks: list[str] = []

    for paragraph in paragraphs:
        if len(paragraph) <= max_chunk_chars:
            chunks.append(paragraph)
        else:
            chunks.extend(_split_long_paragraph(paragraph, max_chunk_chars))

    return chunks

def _split_long_paragraph(paragraph: str, max_chunk_chars: int) -> list[str]:
    """
    Fallblack for paragraphs too large on their own.
    1. Split on sentence boundaries (periods, etc.).
    2. If a resulting piece is still too long, split on bullet markers (common in resumes: ●, -, *, •).
    3. If a piece is still too long, hard-split by character count as a last resort, gurantees no chunk ever exceeds the budget. 
    """
    sentences = _split_into_sentences(paragraph)
    chunks: list[str] = []
    current = ""

    for sentence in sentences:
        if len(sentence) > max_chunk_chars:
            if current:
                chunks.append(current.strip())
                current=""
            chunks.extend(_split_by_bullets_or_length(sentence, max_chunk_chars))
        elif current and len(current) + len(sentence) + 1 > max_chunk_chars:
            chunks.append(current.strip())
            current = sentence
        else:
            current = f"{current} {sentence}".strip()

    if current:
        chunks.append(current.strip())

    return chunks


def _split_into_sentences(text: str) -> list[str]:
    import re
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()] 

def _split_by_bullets_or_length(text: str, max_chunk_chars: int) -> list[str]:
    import re
    bullet_pieces = [p.strip() for p in re.split(r"(?=[●•\-\*]\s)", text) if p.strip()]

    if len(bullet_pieces) <= 1:
        # No bullet point markers found --> hard character-count split, last resort
        return[text[i:i + max_chunk_chars].strip() for i in range(0, len(text), max_chunk_chars)]

    chunks: list[str] = []
    current = ""
    for piece in bullet_pieces:
        if current and len(current) + len(piece) + 1 > max_chunk_chars:
            chunks.append(current.strip())
            current = piece
        else:
            current = f"{current} {piece}".strip()
    if current:
        chunks.append(current.strip())
    return chunks

def compute_chunk_id(source_type: str, source_id: int, chunk_index: int, chunk_text_value: str) -> str:
    """
    Deterministic ID: same source + position + content always produce the same ID. If the underlying text changes, the ID changes too.
    Allows for a new ID for changed content and a stable ID for unchanged content, allowing for better re-indexing to only touch what actually changed.
    """
    content_hash = hashlib.sha256(chunk_text_value.encode("utf-8")).hexdigest()[:12]
    return f"{source_type}:{source_id}:{chunk_index}:{content_hash}"

def build_chunks(
    raw_text: str,
    source_type: str,
    source_id: int,
    extra_metadata: dict | None = None,
    max_chunk_chars: int = 1000,
) -> list[Chunk]:
    text_chunks = chunk_text(raw_text, max_chunk_chars)
    result = []

    for i, chunk_str in enumerate(text_chunks):
        chunk_id = compute_chunk_id(source_type, source_id, i, chunk_str)
        metadata = {
            "source_type": source_type,
            "source_id": source_id,
            "chunk_index": i,
            **(extra_metadata or {}),
        }
        result.append(Chunk(chunk_id=chunk_id, text=chunk_str, chunk_index=i, metadata=metadata))

    return result

def build_chunks_for_document(document) -> list[Chunk]:
    return build_chunks(
        raw_text=document.raw_text,
        source_type="document",
        source_id= document.id,
        extra_metadata={
            "document_type": document.document_type.value,
            "title": document.title,
        },
    )

def build_chunks_for_job_posting(job_posting) -> list[Chunk]:
    return build_chunks(
        raw_text=job_posting.raw_text,
        source_type="job_posting",
        source_id=job_posting.id,
        extra_metadata={
            "company":job_posting.company,
            "role": job_posting.role,
        },
    )