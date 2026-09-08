import re
from dataclasses import dataclass
from sqlalchemy.orm import Session
from backend.models import Skill

@dataclass
class AliasEntry:
    alias: str
    skill_id: int
    canonical_name: str
    requires_case_sensitive: bool
    is_ambiguous: bool

def build_alias_index(db: Session) -> list[AliasEntry]:
    """
    Flatten every skill's aliases into individual entries
    """
    entries: list[AliasEntry] = []
    for skill in db.query(Skill).all():
        for alias in skill.aliases:
            entries.append(
                AliasEntry(
                    alias=alias,
                    skill_id=skill.id,
                    canonical_name=skill.canonical_name,
                    requires_case_sensitive=skill.requires_case_sensitive,
                    is_ambiguous=skill.is_ambiguous,
                )
            )
    entries.sort(key=lambda e: len(e.alias), reverse=True) # Sort by alias length, descending
    return entries

@dataclass
class Match:
    skill_id: int
    canonical_name: str
    alias_matched: str
    start: int
    end: int
    is_ambiguous: bool
    requirement_level: str = "mentioned"

# Words that, immediately before/after an ambiguous match, disqualify it as a real mention of the skill
DENY_CONTEXT: dict[str, dict[str, set[str]]] = {
    "C": {
        "before": {"vitamin", "plan", "section", "grade", "option", "hepatitis"},
        "after": {"student", "section"},
    },
    "Go": {
        "before": {"let's", "lets", "to", "will", "can", "should", "please", "we'll", "i'll"},
        "after": {"ahead", "through", "over", "there", "now", "live", "public"},
    },
    "R": {
        "before": {"vitamin", "rated"},
        "after": {"rated", "us"},
    },
    "React": {
        "before": {"please", "quickly", "immediately", "promptly", "will", "should"},
        "after": {"quickly", "immediately", "accordingly", "promptly", "to"},
    },
    "RAG": {
        "before": {"old"},
        "after": {"doll", "week", "tag"},
    },
    "Pandas": {
        "before": {"cute", "giant", "red", "baby"},
        "after": {"bear", "bears", "zoo"},
    },
    "Spark": {
        "before": {"a", "the"},
        "after": {"joy", "conversation", "debate", "interest", "creativity", "innovation"},
    },
    "Excel": {
        "before": {"will", "should", "to", "can", "could", "would"},
        "after": {"at", "in"},
    },
}

_WORD_RE = re.compile(r"[A-Za-z0-9']+")

def _word_before(text: str, pos: int) -> str:
    words = _WORD_RE.findall(text[:pos])
    return words[-1].lower() if words else ""

def _word_after(text: str, pos: int) -> str:
    words = _WORD_RE.findall(text[pos:])
    return words[0].lower() if words else ""

def passes_context_check(text: str, match: Match) -> bool:
    """
    Disqualifies ambiguous matches sitting next to a word that marks them as something other than the skill
    """
    deny = DENY_CONTEXT.get(match.canonical_name)
    if not deny:
        return True

    before_word = _word_before(text, match.start)
    if before_word and before_word in deny.get("before", set()):
        return False

    after_word = _word_after(text, match.end)
    if after_word and after_word in deny.get("after", set()):
        return False

    return True

NEGATION_PHRASES = [
    "no experience with",
    "not required",
    "nice to have but not",
    "without",
    "doesn't require",
    "does not require",
    "not necessary",
]

def is_negated(text: str, match: Match, window_chars: int = 60) -> bool:
    """
    Checks the text immediately preceding a match for a negation phrase
    """
    window_start = max(0, match.start - window_chars)
    window = text[window_start:match.start].lower()
    return any(phrase in window for phrase in NEGATION_PHRASES)

SECTION_LABEL_MAP = {
    "required": "required",
    "requirements": "required",
    "qualifications": "required",
    "preferred": "preferred",
    "preferred qualifications": "preferred",
    "responsibilities": "mentioned",
}

_HEADING_WORDS = r"Preferred Qualifications|Requirements|Required|Preferred|Responsibilities|Qualifications"
_HEADING_RE = re.compile(
    r"(?im)"
    r"(?:^[ \t]*#{0,2}[ \t]*(?P<h1>" + _HEADING_WORDS + r")[ \t]*:?[ \t]*$)"
    r"|(?:\b(?P<h2>" + _HEADING_WORDS + r")\b[ \t]*:)"
)

def detect_sections(text: str) -> list[tuple[str, int, int]]:
    heading_matches: list[tuple[str, int, int]] = []
    for m in _HEADING_RE.finditer(text):
        heading_text = m.group("h1") or m.group("h2")
        heading_matches.append((heading_text.lower(), m.start(), m.end()))

    if not heading_matches:
        return [("mentioned", 0, len(text))] if text else []

    sections: list[tuple[str, int, int]] = []

    first_start = heading_matches[0][1]
    if first_start > 0:
        sections.append(("mentioned", 0, first_start))

    for i, (heading_text, _, heading_end) in enumerate(heading_matches):
        section_label = SECTION_LABEL_MAP.get(heading_text, "mentioned")
        next_start = heading_matches[i + 1][1] if i + 1 < len(heading_matches) else len(text)
        sections.append((section_label, heading_end, next_start))

    return sections

def _section_for_offset(sections: list[tuple[str, int, int]], offset: int) -> str:
    for label, start, end in sections:
        if start <= offset < end:
            return label
    return "mentioned"

def _overlaps_any(span: tuple[int, int], consumed: list[tuple[int, int]]) -> bool:
    start, end = span
    for consumed_start, consumed_end in consumed:
        overlaps = start < consumed_end and end > consumed_start
        if overlaps:
            return True
    return False

def find_matches(text:str, alias_index: list[AliasEntry]) -> list[Match]:
    consumed: list[tuple[int, int]] = []
    matches: list[Match] = []
    for entry in alias_index:
        flags = 0 if entry.requires_case_sensitive else re.IGNORECASE
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(entry.alias) + r"(?![A-Za-z0-9])", flags)

        for m in pattern.finditer(text):
            span = (m.start(), m.end())
            if _overlaps_any(span, consumed):
                continue
            matches.append(
                Match(
                    skill_id=entry.skill_id,
                    canonical_name=entry.canonical_name,
                    alias_matched=entry.alias,
                    start=span[0],
                    end=span[1],
                    is_ambiguous=entry.is_ambiguous
                )
            )
            consumed.append(span)
    return matches

@dataclass
class SkillFinding:
    skill_id: int
    canonical_name: str
    evidence_spans: list[tuple[int, int]]
    mention_count: int
    requirement_level: str = "mentioned"

REQUIREMENT_PRIORITY = {"required": 0, "preferred": 1, "mentioned": 2}

def dedup_matches(matches: list[Match]) -> list[SkillFinding]:
    """
    Deduplicate matches by skill_id by collapsing mutliple matches into the same skill, while saving every occurence as evidence.
    When a skill is matched at different requirement levels, the highest-priority one wins (required > preferred > mentioned).
    """
    by_skill: dict[int, SkillFinding] = {}

    for m in matches:
        if m.skill_id not in by_skill:
            by_skill[m.skill_id] = SkillFinding(
                skill_id=m.skill_id,
                canonical_name=m.canonical_name,
                evidence_spans=[],
                mention_count=0,
                requirement_level=m.requirement_level,
            )
        finding = by_skill[m.skill_id]
        finding.evidence_spans.append((m.start, m.end))
        finding.mention_count += 1
        if REQUIREMENT_PRIORITY[m.requirement_level] < REQUIREMENT_PRIORITY[finding.requirement_level]:
            finding.requirement_level = m.requirement_level

    return list(by_skill.values())

def analyze_text(text: str, db: Session) -> list[SkillFinding]:
    """
    Full extraction pipeline: index aliases, find matches, drop ambiguous matches
    that fail their context check, assign a requirement level from the section
    each match falls in (downgraded to "mentioned" if the mention is negated),
    then dedupe into one finding per skill.
    """
    alias_index = build_alias_index(db)
    matches = find_matches(text, alias_index)
    matches = [m for m in matches if passes_context_check(text, m)]

    sections = detect_sections(text)

    for m in matches:
        m.requirement_level = _section_for_offset(sections, m.start)
        if is_negated(text, m):
            m.requirement_level = "mentioned"

    return dedup_matches(matches)

SOFT_SKILL_KEYWORDS = [
    "communication", "problem solving", "problem-solving", "teamwork",
    "collaboration", "leadership", "time management", "attention to detail",
    "adaptability", "critical thinking", "self-motivated", "self motivated",
    "interpersonal", "organizational skills", "work ethic",
]


def find_potential_untracked_skills(text: str) -> list[str]:
    lowered = text.lower()
    found = [kw for kw in SOFT_SKILL_KEYWORDS if kw in lowered]
    seen = set()
    deduped = []
    for kw in found:
        normalized = kw.replace("-", " ")
        if normalized not in seen:
            seen.add(normalized)
            deduped.append(kw)
    return deduped


def extract_responsibilities(text: str, sections: list[tuple[str, int, int]]) -> list[dict]:
    responsibilities = []
    for label, start, end in sections:
        if label != "mentioned":
            continue  
        section_text = text[start:end]
        sentences = re.split(r"(?<=[.!?])\s+", section_text.strip())
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) > 10:  
                responsibilities.append({"text": sentence, "evidence": sentence})
    return responsibilities

_LEADING_LABEL_RE = re.compile(r"^\s*(?:" + _HEADING_WORDS + r")\s*:\s*", re.IGNORECASE)

def _expand_to_sentence(text: str, start: int, end: int) -> str:
    """Expand a match span outward to the sentence containing it, stripping a leading section-label prefix (e.g. "Preferred:") if the match sits on the same line as a heading."""
    sentence_start = max(text.rfind(".", 0, start), text.rfind("!", 0, start), text.rfind("?", 0, start), text.rfind("\n", 0, start))
    sentence_start = sentence_start + 1 if sentence_start != -1 else 0

    candidates = [text.find(".", end), text.find("!", end), text.find("?", end), text.find("\n", end)]
    candidates = [c for c in candidates if c != -1]
    sentence_end = min(candidates) + 1 if candidates else len(text)

    sentence = text[sentence_start:sentence_end].strip()
    return _LEADING_LABEL_RE.sub("", sentence)

def get_primary_evidence(text: str, finding: "SkillFinding") -> str | None:
    if not finding.evidence_spans:
        return None
    return _expand_to_sentence(text, *finding.evidence_spans[0])


def build_structured_result(
    text: str,
    findings: list["SkillFinding"],
    sections: list[tuple[str, int, int]],
) -> dict:
    required_skills = []
    preferred_skills = []
    mentioned_skills = []

    for f in findings:
        entry = {
            "name": f.canonical_name,
            "evidence": _expand_to_sentence(text, *f.evidence_spans[0]) if f.evidence_spans else None,
        }
        if f.requirement_level == "required":
            required_skills.append(entry)
        elif f.requirement_level == "preferred":
            preferred_skills.append(entry)
        else:
            # "mentioned" skills (including negated mentions, e.g. "no experience with X required") get their own list
            mentioned_skills.append(entry)

    return {
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "mentioned_skills": mentioned_skills,
        "responsibilities": extract_responsibilities(text, sections),
        "min_experience": None,
        "education": None,
        "location": None,
        "work_arrangement": None,
        "work_authorization": None,
        "salary": None,
        "deadline": None,
        "employment_type": None,
        "potential_untracked_skills": find_potential_untracked_skills(text),
    }