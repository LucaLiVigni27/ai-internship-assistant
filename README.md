# AI Internship Assistant

> 🚧 **Prototype — not yet deployed.** Runs locally via Docker; no hosted demo yet.

A hybrid SQL/vector RAG system for tracking internship applications and matching them against resumes and project experience — built to demonstrate SWE, ML/AI engineering, and data skills together in one project, with measured evaluation at every layer rather than "it works" claims.

## What it does

- Tracks job postings and applications in a relational database (SQLite via SQLAlchemy)
- Extracts structured data from job postings (required/preferred skills, responsibilities, scalar fields like salary/location) via both a rule-based regex matcher and an LLM-based structured extractor, with the two compared head-to-head
- Indexes job postings, resumes, and project write-ups into a hybrid search layer (lexical BM25 + vector embeddings) for semantic + keyword retrieval
- Answers free-text questions about the indexed corpus with citation-grounded, hallucination-checked answers
- Matches a candidate's resume/projects against a specific posting with an explainable, evidence-grounded recommendation (not just an opaque score)

## Architecture

- **Backend**: FastAPI + SQLAlchemy 2.0 (typed `Mapped[]` style), Alembic migrations, SQLite
- **Retrieval**: Chroma (vector, `all-MiniLM-L6-v2` embeddings) + SQLite FTS5 (BM25), fused via Reciprocal Rank Fusion
- **Extraction/Generation**: LangChain + Claude, with structured output schemas and verbatim-quote citation validation
- **Frontend**: Streamlit
- **Infra**: Dockerized (backend + frontend containers), GitHub Actions CI running a pytest suite

## Measured results

Every major component was evaluated against a hand-labeled test set, not just spot-checked.

**Retrieval** (14 hand-labeled queries, hybrid search via RRF vs. either method alone):

| Method | Recall@5 | MRR |
|---|---|---|
| Lexical (BM25) | 77.38% | 0.768 |
| Vector (semantic) | 58.33% | 0.720 |
| **Hybrid (RRF)** | **81.55%** | **0.810** |

Hybrid beat both individual methods on every metric, including correctly rescuing a purely-semantic query ("helping customers at a fast food restaurant" → an In-N-Out resume chunk with zero literal word overlap) that lexical search alone completely missed.

**Skill extraction** (18 hand-labeled job postings, regex matcher vs. LLM extractor):

| Extractor | Precision | Recall | Hallucination Rate | Avg Latency |
|---|---|---|---|---|
| Regex (catalog-based) | 97.22% | 100% | 0% | 114ms |
| LLM (structured output) | 95.58% | 70.69% | 2.40% | ~17.8s |

The regex matcher wins outright on this catalog-scoped comparison, but the LLM path surfaces real skills *outside* the fixed catalog, which the regex approach structurally cannot.

**Citation-grounded answer generation**: initial citation hallucination rate measured at 25.2%, but that number conflated real fabrication with harmless formatting drift (line-wrap joins, curly-vs-straight quotes) from source-text extraction noise. After normalizing for that and fixing one genuine issue (the model splicing two non-adjacent sentences together with "..." and presenting it as one verbatim quote), the true hallucination rate dropped to 0% across the eval set, with `sufficient_context` correctly identified 100% of the time.

**Resume-to-posting matching**: skill-matching accuracy turned out to be **header-dependent** — 79% precision / 100% recall on postings with clear "Required Qualifications:"-style section headings, but only 11%/11% on postings phrased less formulaically (e.g. "What we're looking for:"). This is a known, measured limitation of the current regex-based section detector, not a hidden bug — see Known Limitations below.

**Tests**: 67 automated tests (pytest), all passing in CI, covering models, extraction, chunking, hybrid search, and API endpoints.

## Known limitations

- **Skill-matching accuracy depends on job posting formatting.** The rule-based extractor relies on recognizable section headings; postings without them land all their skills in one undifferentiated bucket, degrading match-score reliability for those postings specifically.
- **The Application Tracker's create-application form is out of sync with the backend schema** (pre-existing gap — it posts fields the API doesn't accept). Doesn't crash, just fails validation; not yet fixed.
- **Not deployed.** Currently runs locally only, via `docker-compose up`.

## Running locally

Requires Docker and an Anthropic API key.

```bash
# 1. Clone the repo
git clone https://github.com/LucaLiVigni27/ai-internship-assistant.git
cd ai-internship-assistant

# 2. Create db/ and chroma_db/ directories for the persistent volumes
mkdir -p db chroma_db

# 3. Add your API key
echo "ANTHROPIC_API_KEY=sk-ant-..." > .env

# 4. Build and run
docker-compose up --build
```

Backend: `http://localhost:8000` · Frontend: `http://localhost:8501`

## Tech stack

Python, FastAPI, SQLAlchemy, Alembic, SQLite, ChromaDB, LangChain, Claude (Anthropic API), Streamlit, Docker, pytest, GitHub Actions
