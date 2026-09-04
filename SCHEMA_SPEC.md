# structured_result schema

Shared output shape for `AnalysisRun.structured_result` (`backend/models.py`), produced today by
`backend.skill_matcher.build_structured_result` (rule-based extractor) and, later, by an LLM-based
extractor. Both extractors must emit this same shape.

```json
{
  "required_skills": [{"name": "Python", "evidence": "Required: Python and SQL experience."}],
  "preferred_skills": [{"name": "Docker", "evidence": "Docker experience is a plus."}],
  "mentioned_skills": [{"name": "Kubernetes", "evidence": "No experience with Kubernetes required."}],
  "responsibilities": [{"text": "...", "evidence": "..."}],
  "min_experience": null,
  "education": null,
  "location": null,
  "work_arrangement": null,
  "work_authorization": null,
  "salary": null,
  "deadline": null,
  "employment_type": null,
  "potential_untracked_skills": ["problem solving"]
}
```

## Skill lists

Every extracted skill lands in exactly one of three lists, keyed by `requirement_level`:

- `required_skills` — skill appears in a Required/Requirements/Qualifications section.
- `preferred_skills` — skill appears in a Preferred/Preferred Qualifications section.
- `mentioned_skills` — skill appears outside a required/preferred section, **or** the mention is negated (e.g.
  "no experience with Kubernetes required") and is downgraded to `mentioned` regardless of which
  section it was found in.

Each entry has the same shape: `{"name": <canonical skill name>, "evidence": <sentence containing the mention, with any leading section-label prefix like "Preferred:" stripped>}`.

A skill never appears in more than one list, when a skill is mentioned multiple times at
different requirement levels, only its highest-priority level (required > preferred > mentioned)
is kept.
