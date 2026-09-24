from backend.skill_matcher import (
    build_alias_index,
    find_matches,
    dedup_matches,
    passes_context_check,
    is_negated,
    detect_sections,
    analyze_text,
    find_potential_untracked_skills,
    Match,
)


def test_find_matches_is_case_insensitive_for_non_ambiguous_skills(db_session):
    alias_index = build_alias_index(db_session)
    matches = find_matches("we use docker and PYTHON daily", alias_index)
    names = {m.canonical_name for m in matches}
    assert "Docker" in names
    assert "Python" in names


def test_dedup_matches_collapses_repeated_mentions_of_the_same_skill(db_session):
    alias_index = build_alias_index(db_session)
    matches = find_matches("Python, Python, and more Python.", alias_index)
    findings = dedup_matches(matches)
    python_findings = [f for f in findings if f.canonical_name == "Python"]
    assert len(python_findings) == 1
    assert python_findings[0].mention_count == 3


def _match_for(text: str, term: str, canonical_name: str) -> Match:
    start = text.index(term)
    return Match(skill_id=1, canonical_name=canonical_name, alias_matched=term, start=start, end=start + len(term), is_ambiguous=True)


def test_passes_context_check_denies_ambiguous_go_in_denylisted_context():
    text = "Let's go over the plan."
    assert not passes_context_check(text, _match_for(text, "go", "Go"))


def test_passes_context_check_allows_go_the_language_in_normal_context():
    text = "Experience with Go is a plus."
    assert passes_context_check(text, _match_for(text, "Go", "Go"))


def test_is_negated_true_within_window():
    text = "No experience with Kubernetes required for this role."
    match = Match(skill_id=1, canonical_name="Kubernetes", alias_matched="Kubernetes", start=20, end=30, is_ambiguous=False)
    assert is_negated(text, match)


def test_is_negated_false_when_phrase_is_outside_the_window():
    text = "not required for the intro course. " + ("filler " * 20) + "Kubernetes experience is a plus."
    start = text.index("Kubernetes")
    match = Match(skill_id=1, canonical_name="Kubernetes", alias_matched="Kubernetes", start=start, end=start + 10, is_ambiguous=False)
    assert not is_negated(text, match)


def test_detect_sections_classifies_required_and_preferred_headings():
    text = "Intro paragraph.\n\nRequired:\nPython, SQL.\n\nPreferred:\nDocker."
    sections = detect_sections(text)
    labels = [label for label, _, _ in sections]
    assert "mentioned" in labels
    assert "required" in labels
    assert "preferred" in labels


def test_detect_sections_falls_back_to_one_mentioned_section_with_no_headings():
    text = "EDUCATION\nUCLA, BS Computer Science.\n\nSKILLS\nPython, SQL, Docker."
    sections = detect_sections(text)
    assert len(sections) == 1
    assert sections[0][0] == "mentioned"
    assert sections[0][1] == 0
    assert sections[0][2] == len(text)


def test_analyze_text_required_skill_is_tagged_required(db_session):
    findings = analyze_text("Required: Python and Docker.", db_session)
    by_name = {f.canonical_name: f.requirement_level for f in findings}
    assert by_name["Python"] == "required"
    assert by_name["Docker"] == "required"


def test_analyze_text_negated_required_skill_downgrades_to_mentioned(db_session):
    findings = analyze_text("Required: Python. No experience with Kubernetes required.", db_session)
    by_name = {f.canonical_name: f.requirement_level for f in findings}
    assert by_name["Python"] == "required"
    assert by_name["Kubernetes"] == "mentioned"


def test_analyze_text_on_unstructured_resume_text_lands_everything_in_mentioned(db_session):
    resume_text = "EDUCATION\nBS Computer Science.\n\nSKILLS\nPython, SQL, Docker, React."
    findings = analyze_text(resume_text, db_session)
    assert {f.canonical_name for f in findings} >= {"Python", "SQL", "Docker", "React"}
    assert all(f.requirement_level == "mentioned" for f in findings)


def test_find_potential_untracked_skills_dedupes_hyphen_variants():
    text = "We value problem solving and problem-solving skills."
    found = find_potential_untracked_skills(text)
    normalized = {kw.replace("-", " ") for kw in found}
    assert normalized == {"problem solving"}
