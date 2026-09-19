"""
Validate every fixture in tests/eval_set/.

For each *.json file:
  1.) it must be well-formed JSON with top-level `source`, `raw_text`, `labels`
  2.) every `evidence` string must be an exact substring of that file's own `raw_text`:
      - in required_skills / preferred_skills / mentioned_skills entries
      - in every `responsibilities` entry (both `text` and `evidence`)
      - in every non-null label field that carries a `value`/`evidence` pair
        (min_experience, education, location, work_arrangement,
         work_authorization, salary, deadline, employment_type)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

EVAL_DIR = Path(__file__).resolve().parent / "eval_set"

SKILL_LISTS = ("required_skills", "preferred_skills", "mentioned_skills")
VALUE_FIELDS = (
    "min_experience",
    "education",
    "location",
    "work_arrangement",
    "work_authorization",
    "salary",
    "deadline",
    "employment_type",
)


def check_file(path: Path) -> list[str]:
    failures: list[str] = []

    try:
        obj = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return [f"{path.name} | <parse> | invalid JSON: {exc}"]

    for key in ("source", "raw_text", "labels"):
        if key not in obj:
            failures.append(f"{path.name} | <structure> | missing top-level key '{key}'")
    if failures:
        return failures

    raw_text = obj["raw_text"]
    labels = obj["labels"]

    def verify(evidence: object, where: str) -> None:
        if not isinstance(evidence, str):
            failures.append(f"{path.name} | {where} | evidence is not a string: {evidence!r}")
        elif evidence not in raw_text:
            failures.append(f"{path.name} | {where} | not a substring of raw_text: {evidence!r}")

    for list_name in SKILL_LISTS:
        for entry in labels.get(list_name, []):
            name = entry.get("name", "?")
            if "evidence" not in entry:
                failures.append(f"{path.name} | {list_name}/{name} | entry has no 'evidence'")
                continue
            verify(entry["evidence"], f"{list_name}/{name}")

    for i, entry in enumerate(labels.get("responsibilities", [])):
        verify(entry.get("text"), f"responsibilities[{i}]/text")
        verify(entry.get("evidence"), f"responsibilities[{i}]/evidence")

    for field_name in VALUE_FIELDS:
        field = labels.get(field_name)
        if field is None:
            continue
        if "value" not in field or "evidence" not in field:
            failures.append(f"{path.name} | {field_name} | field missing 'value'/'evidence' pair")
            continue
        verify(field["evidence"], field_name)

    return failures


def main() -> int:
    files = sorted(EVAL_DIR.glob("*.json"))
    if not files:
        print(f"No JSON files found in {EVAL_DIR}")
        return 1

    all_failures: list[str] = []
    for path in files:
        file_failures = check_file(path)
        status = "OK" if not file_failures else f"FAIL ({len(file_failures)})"
        print(f"{path.name:52s} {status}")
        all_failures.extend(file_failures)

    print()
    if all_failures:
        print(f"{len(all_failures)} failure(s):")
        for line in all_failures:
            print(f"  {line}")
        return 1

    print(f"All {len(files)} files valid: every evidence string is a verbatim substring of its raw_text.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
