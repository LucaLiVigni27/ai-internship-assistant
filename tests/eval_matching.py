"""
Evaluates Day 11 skill matching. Two things, both against real data rather
than a single demo run:

  1.) Posting-side extraction accuracy: precision/recall of the required/
     preferred skills matching.py identifies, measured against the 18
     hand-labeled postings in tests/eval_set/*.json. This is the input the
     match score depends on, so it's the part worth a real number.
  2.) Real match scores: every one of those 18 postings matched against
     whatever Document(s) currently exist in the dev DB (compute_skill_overlap
     only, no LLM calls -- deterministic and free to run for all 18).

There's no independent ground truth for "does the candidate actually have
skill X", so match_score itself isn't precision/recall-scored here -- only
the posting-side extraction feeding it is. The grounded-explanation half of
matching.py (citations) is already covered by tests/eval_answers.py's
citation-hallucination eval; this script does one live demo call at the end
to confirm the full /match path (extraction + explanation) works end to end.

Run directly (not a pytest module):
    PYTHONPATH=. python3 tests/eval_matching.py
"""

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from backend.database import SessionLocal
from backend.models import Document, JobPosting
from backend.matching import _skill_names, compute_skill_overlap, match_job_posting
from backend.skill_matcher import detect_sections

EVAL_DIR = Path("tests/eval_set")


@dataclass
class _FakePosting:
    raw_text: str


def load_eval_postings() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(EVAL_DIR.glob("*.json"))]


def score_extraction(db, raw_text: str, level: str, expected_names: set[str]) -> dict:
    predicted = _skill_names(db, raw_text, levels={level})
    true_positives = predicted & expected_names
    precision = len(true_positives) / len(predicted) if predicted else (1.0 if not expected_names else 0.0)
    recall = len(true_positives) / len(expected_names) if expected_names else 1.0
    return {"precision": precision, "recall": recall}


def run_evaluation():
    db = SessionLocal()
    postings = load_eval_postings()

    required_scores = {"precision": [], "recall": []}
    preferred_scores = {"precision": [], "recall": []}
    with_headings = {"precision": [], "recall": []}
    without_headings = {"precision": [], "recall": []}

    print(f"=== Posting-side skill extraction vs. hand-labeled ground truth (n={len(postings)}) ===")
    for posting in postings:
        raw_text = posting["raw_text"]
        labels = posting["labels"]
        expected_required = {s["name"] for s in labels["required_skills"]}
        expected_preferred = {s["name"] for s in labels["preferred_skills"]}

        req = score_extraction(db, raw_text, "required", expected_required)
        pref = score_extraction(db, raw_text, "preferred", expected_preferred)
        required_scores["precision"].append(req["precision"])
        required_scores["recall"].append(req["recall"])
        preferred_scores["precision"].append(pref["precision"])
        preferred_scores["recall"].append(pref["recall"])

        sections = detect_sections(raw_text)
        has_headings = any(label != "mentioned" for label, _, _ in sections)
        bucket = with_headings if has_headings else without_headings
        bucket["precision"].append(req["precision"])
        bucket["recall"].append(req["recall"])

        label = posting["source"].rsplit("/", 1)[-1][:55]
        print(
            f"  {label:55s} required P={req['precision']:.2f} R={req['recall']:.2f}"
            f"  preferred P={pref['precision']:.2f} R={pref['recall']:.2f}"
            f"  headings={'yes' if has_headings else 'no'}"
        )

    print("\n=== Aggregate extraction accuracy ===")
    print(f"required_skills : precision={mean(required_scores['precision']):.2%}  recall={mean(required_scores['recall']):.2%}")
    print(f"preferred_skills: precision={mean(preferred_scores['precision']):.2%}  recall={mean(preferred_scores['recall']):.2%}")
    print(f"\nrequired_skills, split by whether detect_sections found Required/Preferred-style headings:")
    print(f"  with headings    (n={len(with_headings['precision'])}): precision={mean(with_headings['precision']):.2%}  recall={mean(with_headings['recall']):.2%}")
    if without_headings["precision"]:
        print(f"  without headings (n={len(without_headings['precision'])}): precision={mean(without_headings['precision']):.2%}  recall={mean(without_headings['recall']):.2%}")

    documents = db.query(Document).all()
    print(f"\n=== Real match scores vs. {len(documents)} document(s) in the dev DB ===")
    if not documents:
        print("  (no documents uploaded -- skipping)")
    else:
        print("  documents:", ", ".join(f"{d.title} ({d.document_type.value})" for d in documents))
        match_scores = []
        for posting in postings:
            fake_posting = _FakePosting(raw_text=posting["raw_text"])
            overlap = compute_skill_overlap(db, fake_posting, documents)
            if overlap["match_score"] is not None:
                match_scores.append(overlap["match_score"])
            label = posting["source"].rsplit("/", 1)[-1][:55]
            score_str = f"{overlap['match_score']:.2%}" if overlap["match_score"] is not None else "n/a"
            print(
                f"  {label:55s} score={score_str:>6s}"
                f"  matched_required={len(overlap['matched_required_skills'])}/{overlap['total_required']}"
            )

        if match_scores:
            print(f"\nmean match_score across {len(match_scores)} postings with required skills: {mean(match_scores):.2%}")

        example = postings[0]
        example_overlap = compute_skill_overlap(db, _FakePosting(raw_text=example["raw_text"]), documents)
        print(f"\nExample ({example['source'].rsplit('/', 1)[-1]}):")
        print(f"  matched_required_skills: {example_overlap['matched_required_skills']}")
        print(f"  missing_required_skills: {example_overlap['missing_required_skills'][:10]}"
              f"{' ...' if len(example_overlap['missing_required_skills']) > 10 else ''}")

    real_posting = db.query(JobPosting).filter(JobPosting.id > 1).first()
    if real_posting and documents:
        print(f"\n=== Live /match demo: {real_posting.company} - {real_posting.role} ===")
        result = match_job_posting(db, real_posting, documents)
        print(f"match_score: {result['match_score']}")
        print(f"matched_required_skills: {result['matched_required_skills']}")
        print(f"sufficient_context: {result['sufficient_context']}")
        print(f"answer: {result['answer']}")
        print(f"citations: {len(result['citations'])}")
        for c in result["citations"]:
            print(f"  [{c['chunk_id']}] {c['quote']!r}")

    db.close()


if __name__ == "__main__":
    run_evaluation()
