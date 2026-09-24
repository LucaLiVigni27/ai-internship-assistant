"""
Compares the regex skill-matcher against the LLM extractor on the labeled
postings in tests/eval_set/. Prints precision/recall, evidence hallucination
rate, scalar-field agreement, and latency for each.

Run directly (not a pytest module):
    PYTHONPATH=. python3 tests/eval_extractors.py

Notes:
  - Precision/recall are scored against catalog-scoped ground truth, so LLM
    skills found outside the catalog are reported separately, not penalized.
  - Scalar fields (salary, location, etc.) are checked for presence only,
    not exact value match, free-text values need a human spot-check.
"""

import json
import time
from collections import Counter
from pathlib import Path
from backend.database import SessionLocal
from backend.skill_matcher import analyze_text, build_alias_index, build_structured_result, detect_sections

from dotenv import load_dotenv
load_dotenv()

EVAL_DIR = Path("tests/eval_set")


def load_eval_files() -> list[dict]:
    postings = []
    for path in sorted(EVAL_DIR.glob("*.json")):
        with open(path) as f:
            data = json.load(f)
            data["_filename"] = path.name
            postings.append(data)
    return postings


def run_regex_extractor(raw_text: str, db) -> tuple[dict, int]:
    start = time.perf_counter()
    findings = analyze_text(raw_text, db)
    sections = detect_sections(raw_text)
    result = build_structured_result(raw_text, findings, sections)
    latency_ms = int((time.perf_counter() - start) * 1000)
    return result, latency_ms


def run_llm_extractor(raw_text: str) -> tuple[dict, int]:
    from backend.llm_extractor import extract_with_llm

    start = time.perf_counter()
    result = extract_with_llm(raw_text).model_dump()
    latency_ms = int((time.perf_counter() - start) * 1000)
    return result, latency_ms


def normalize_names(skill_list: list[dict]) -> set[str]:
    return {s["name"].strip().lower() for s in skill_list}


def score_skill_field(predicted: list[dict], expected: list[dict], catalog_aliases: set[str]) -> dict:
    pred_names = normalize_names(predicted)
    exp_names = normalize_names(expected)

    true_positives = pred_names & exp_names
    false_positives = pred_names - exp_names
    false_negatives = exp_names - pred_names
    catalog_scoped_pred_names = pred_names & catalog_aliases

    precision = (
        len(true_positives) / len(catalog_scoped_pred_names)
        if catalog_scoped_pred_names
        else (1.0 if not exp_names else 0.0)
    )
    recall = len(true_positives) / len(exp_names) if exp_names else 1.0

    return {
        "precision": precision,
        "recall": recall,
        "true_positives": len(true_positives),
        "false_positives": len(false_positives),
        "false_negatives": len(false_negatives),
        "extra_names": sorted(false_positives),
        "missed_names": sorted(false_negatives),
    }


def validate_evidence(result: dict, raw_text: str) -> dict:
    """Check every evidence string across the result is a real substring of raw_text."""
    total = 0
    valid = 0
    invalid_examples = []

    def check_list(items, evidence_key="evidence"):
        nonlocal total, valid
        for item in items:
            ev = item.get(evidence_key)
            if ev is None:
                continue
            total += 1
            if ev in raw_text:
                valid += 1
            else:
                invalid_examples.append(ev[:80])

    check_list(result.get("required_skills", []))
    check_list(result.get("preferred_skills", []))
    check_list(result.get("mentioned_skills", []))
    check_list(result.get("responsibilities", []), evidence_key="evidence")

    for field_name in ["min_experience", "education", "location", "work_arrangement",
                       "work_authorization", "salary", "deadline", "employment_type"]:
        field = result.get(field_name)
        if field is not None:
            total += 1
            if field.get("evidence") in raw_text:
                valid += 1
            else:
                invalid_examples.append(str(field.get("evidence"))[:80])

    return {
        "total_evidence_checked": total,
        "valid_evidence": valid,
        "hallucination_rate": (total - valid) / total if total else 0.0,
        "invalid_examples": invalid_examples[:5],
    }

def bucket_extra_names(extra_names: list[str], llm_result: dict, db, raw_text: str) -> dict:
    """
    Split score_skill_field()'s `extra_names` into three buckets so LLM finds that
    the ground truth can't account for aren't all lumped together as "wrong":
      1.) ground_truth_miss: name matches a catalog alias -> it should have been labeled. A gap in the eval labels, not an LLM error.
      2.) beyond_catalog_real: not in the catalog, but the LLM's evidence is a verbatim substring of raw_text AND the skill name appears inside that evidence -> a real, uncatalogued skill (a catalog gap).
      3.) unsupported: neither -> likely noise / hallucination.
    """
    catalog_aliases = {entry.alias.strip().lower() for entry in build_alias_index(db)}

    evidence_by_name: dict[str, list[str]] = {}
    for list_name in ("required_skills", "preferred_skills", "mentioned_skills"):
        for item in llm_result.get(list_name, []):
            key = item["name"].strip().lower()
            evidence_by_name.setdefault(key, []).append(item.get("evidence") or "")

    buckets: dict[str, list[str]] = {
        "ground_truth_miss": [],
        "beyond_catalog_real": [],
        "unsupported": [],
    }
    for name in extra_names:
        key = name.strip().lower()
        if key in catalog_aliases:
            buckets["ground_truth_miss"].append(name)
            continue
        evidences = evidence_by_name.get(key, [])
        supported = any(ev in raw_text and key in ev.lower() for ev in evidences)
        buckets["beyond_catalog_real" if supported else "unsupported"].append(name)

    return buckets


SCALAR_FIELDS = ["min_experience", "education", "location", "work_arrangement", "work_authorization", "salary", "deadline", "employment_type"]


def score_scalar_fields(predicted: dict, expected: dict) -> dict:
    """
    Presence/absence agreement only — NOT content correctness, since these are free-text values that can't be fairly compared with exact string matching.
    Content accuracy requires a human spot-check!
    """
    agreements = 0
    for field in SCALAR_FIELDS:
        pred_present = predicted.get(field) is not None
        exp_present = expected.get(field) is not None
        if pred_present == exp_present:
            agreements += 1
    return {"field_presence_agreement": agreements / len(SCALAR_FIELDS)}


def run_evaluation():
    db = SessionLocal()
    postings = load_eval_files()

    regex_scores = {"precision": [], "recall": [], "hallucination_rate": [],
                    "field_presence_agreement": [], "latency_ms": []}
    llm_scores = {"precision": [], "recall": [], "hallucination_rate": [],
                  "field_presence_agreement": [], "latency_ms": []}

    catalog_gap_counter: Counter = Counter()

    catalog_aliases = {entry.alias.strip().lower() for entry in build_alias_index(db)}

    for posting in postings:
        raw_text = posting["raw_text"]
        labels = posting["labels"]

        regex_result, regex_latency = run_regex_extractor(raw_text, db)
        llm_result, llm_latency = run_llm_extractor(raw_text)

        for extractor_name, result, latency, scores in [
            ("regex", regex_result, regex_latency, regex_scores),
            ("llm", llm_result, llm_latency, llm_scores),
        ]:
            all_predicted = (
                result.get("required_skills", []) +
                result.get("preferred_skills", []) +
                result.get("mentioned_skills", [])
            )
            all_expected = (
                labels.get("required_skills", []) +
                labels.get("preferred_skills", []) +
                labels.get("mentioned_skills", [])
            )
            skill_score = score_skill_field(all_predicted, all_expected, catalog_aliases)
            evidence_score = validate_evidence(result, raw_text)
            scalar_score = score_scalar_fields(result, labels)

            scores["precision"].append(skill_score["precision"])
            scores["recall"].append(skill_score["recall"])
            scores["hallucination_rate"].append(evidence_score["hallucination_rate"])
            scores["field_presence_agreement"].append(scalar_score["field_presence_agreement"])
            scores["latency_ms"].append(latency)

            if extractor_name == "llm" and skill_score["extra_names"]:
                print(f"  [{posting['_filename']}] LLM found beyond catalog: {skill_score['extra_names']}")
                buckets = bucket_extra_names(skill_score["extra_names"], result, db, raw_text)
                catalog_gap_counter.update(buckets["beyond_catalog_real"])

    db.close()

    def avg(lst):
        return sum(lst) / len(lst) if lst else 0.0

    print("\n=== Aggregate Results ===")
    for name, scores in [("REGEX", regex_scores), ("LLM", llm_scores)]:
        print(f"\n{name}:")
        print(f"  Precision (catalog-scoped): {avg(scores['precision']):.2%}")
        print(f"  Recall (catalog-scoped):    {avg(scores['recall']):.2%}")
        print(f"  Evidence hallucination rate: {avg(scores['hallucination_rate']):.2%}")
        print(f"  Scalar field presence agreement: {avg(scores['field_presence_agreement']):.2%}")
        print(f"  Avg latency: {avg(scores['latency_ms']):.0f}ms")

    print("\n=== Catalog Gap Frequency ===")
    print("(LLM skills with valid evidence that are outside the catalog — candidates for seed_skills.py)")
    if catalog_gap_counter:
        for name, count in catalog_gap_counter.most_common():
            print(f"  {count:3d}  {name}")
    else:
        print("  (none)")


if __name__ == "__main__":
    run_evaluation()
