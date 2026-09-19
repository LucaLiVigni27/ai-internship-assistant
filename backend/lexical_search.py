import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = ROOT_DIR / "db" / "internships.db"

def get_raw_connection() -> sqlite3.Connection:
    """
    Since FTS5 virtual table aren't supported  through SQLAlchemy's ORM layer, use this as a raw sqlite3 connection against the same database file.
    """
    return sqlite3.connect(str(DB_PATH))

def ensure_fts_table():
    conn = get_raw_connection()
    conn.execute("""
        CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(
            chunk_id UNINDEXED,
            text,
            source_type UNINDEXED,
            source_id UNINDEXED
        )
    """)
    conn.commit()
    conn.close()

def index_chunks_fts(chunks: list["Chunk"], source_type: str, source_id: int) -> dict: #type: ignore[arg-type]
    conn = get_raw_connection()

    existing_rows = conn.execute(
        "SELECT chunk_id FROM chunks_fts WHERE source_type = ? AND source_id = ?",
        (source_type, source_id),
    ).fetchall()
    existing_ids = {row[0] for row in existing_rows}
    desired_ids = {c.chunk_id for c in chunks}

    ids_to_remove = existing_ids - desired_ids
    ids_to_add = desired_ids - existing_ids

    for chunk_id in ids_to_remove:
        conn.execute("DELETE FROM chunks_fts WHERE chunk_id = ?", (chunk_id,))

    chunks_by_id = {c.chunk_id: c for c in chunks}
    for chunk_id in ids_to_add:
        c = chunks_by_id[chunk_id]
        conn.execute(
            "INSERT INTO chunks_fts (chunk_id, text, source_type, source_id) VALUES (?, ?, ?, ?)",
            (c.chunk_id, c.text, source_type, source_id),
        )

    conn.commit()
    conn.close()
    return {"added": len(ids_to_add), "removed": len(ids_to_remove), "unchanged": len(existing_ids & desired_ids)}

STOPWORDS = {
    "a", "an", "the", "at", "in", "on", "of", "to", "for", "and", "or", "by", "but"
    "is", "are", "was", "were", "be", "with", "like", "as", "it", "this", "that", "from",
}

def search_lexical(query: str, top_k: int = 5, source_type: str | None = None) -> list[dict]:
    conn = get_raw_connection()
    words = query.split()
    terms = [word for word in words if word.lower() not in STOPWORDS]
    if not terms:
        terms=words
    # Quote each term so FTS5 treats it as a literal string, not a query operator
    quoted_terms = [f'"{term.replace(chr(34), chr(34)*2)}"' for term in terms]
    fts_query = " OR ".join(quoted_terms)

    sql = """
        SELECT chunk_id, text, source_type, source_id, bm25(chunks_fts) as score
        FROM chunks_fts
        WHERE chunks_fts MATCH?
    """
    params: list = [fts_query]

    if source_type is not None:
        sql += " AND source_type = ?"
        params.append(source_type)

    sql += " ORDER BY score LIMIT ?"
    params.append(top_k)

    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [
        {"chunk_id": r[0], "text": r[1], "source_type": r[2], "source_id": r[3], "score": r[4]}
        for r in rows
    ]