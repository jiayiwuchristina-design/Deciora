from __future__ import annotations

from utils.helpers import clean_text


def _first(items: list[str], fallback: str) -> str:
    for item in items:
        cleaned = clean_text(item)
        if cleaned:
            return cleaned
    return fallback


def _candidate_keyword_pool(candidate: dict, candidate_profile: dict) -> list[str]:
    values = (
        candidate.get("research_tags", [])[:6]
        + candidate.get("recent_topics", [])[:4]
        + candidate.get("discipline_tags", [])[:3]
        + candidate_profile.get("interest_keywords", [])[:5]
        + candidate_profile.get("methods", [])[:3]
        + candidate_profile.get("tools", [])[:4]
    )
    pool: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value).lower()
        if not cleaned or cleaned in seen:
            continue
        pool.append(cleaned)
        seen.add(cleaned)
    return pool


def _resume_lines(text: str) -> list[str]:
    lines: list[str] = []
    seen: set[str] = set()
    for raw_line in str(text or "").splitlines():
        cleaned = clean_text(raw_line)
        if len(cleaned) < 8:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        lines.append(cleaned)
        seen.add(lowered)
    return lines


def _score_resume_line(line: str, keyword_pool: list[str], preferred_tools: list[str]) -> tuple[int, int]:
    lowered = clean_text(line).lower()
    keyword_hits = sum(1 for keyword in keyword_pool if keyword and keyword in lowered)
    tool_hits = sum(1 for tool in preferred_tools if tool and tool.lower() in lowered)
    quantified = int(any(char.isdigit() for char in lowered))
    score = keyword_hits * 4 + tool_hits * 3 + quantified * 2
    return score, len(lowered)


def _best_section_evidence(section_text: str, keyword_pool: list[str], preferred_tools: list[str], limit: int = 2) -> list[str]:
    ranked: list[tuple[int, int, str]] = []
    for line in _resume_lines(section_text):
        score, length = _score_resume_line(line, keyword_pool, preferred_tools)
        if score <= 0:
            continue
        ranked.append((score, -length, line))
    ranked.sort(key=lambda item: (-item[0], item[1], item[2].lower()))
    return [line for _score, _length, line in ranked[:limit]]


def _coursework_evidence(education_text: str, keyword_pool: list[str]) -> list[str]:
    results: list[str] = []
    for line in _resume_lines(education_text):
        lowered = line.lower()
        if "course" in lowered or "module" in lowered:
            if any(keyword in lowered for keyword in keyword_pool):
                results.append(line)
        if len(results) >= 2:
            break
    return results


def _student_evidence(candidate: dict, candidate_profile: dict) -> dict[str, list[str] | str]:
    sections = candidate_profile.get("resume_sections", {})
    keyword_pool = _candidate_keyword_pool(candidate, candidate_profile)
    preferred_tools = candidate_profile.get("tools", [])[:5]
    project_lines = _best_section_evidence(sections.get("projects", ""), keyword_pool, preferred_tools, limit=2)
    experience_lines = _best_section_evidence(sections.get("experience", ""), keyword_pool, preferred_tools, limit=2)
    coursework_lines = _coursework_evidence(sections.get("education", ""), keyword_pool)
    if not coursework_lines:
        coursework_lines = _best_section_evidence(sections.get("education", ""), keyword_pool, preferred_tools, limit=1)

    evidence_points: list[str] = []
    for group in (project_lines, experience_lines, coursework_lines):
        for line in group:
            if line not in evidence_points:
                evidence_points.append(line)
            if len(evidence_points) >= 3:
                break
        if len(evidence_points) >= 3:
            break

    compact_evidence: list[str] = []
    for line in evidence_points:
        trimmed = line if len(line) <= 140 else f"{line[:137].rstrip()}..."
        compact_evidence.append(trimmed)

    tool_summary = ", ".join(candidate_profile.get("tools", [])[:4])
    method_summary = ", ".join(candidate_profile.get("methods", [])[:3])
    return {
        "evidence_points": compact_evidence,
        "project_lines": project_lines,
        "experience_lines": experience_lines,
        "coursework_lines": coursework_lines,
        "tool_summary": tool_summary,
        "method_summary": method_summary,
    }


def _subject_lines(candidate: dict, candidate_profile: dict, topic_anchor: str, publication_anchor: str) -> list[str]:
    stage = candidate_profile.get("academic_stage", "Student")
    university = candidate.get("university", "your group")
    return [
        f"{stage} outreach about {topic_anchor}",
        f"Potential fit for your work on {publication_anchor}",
        f"Student interest in {topic_anchor} at {university}",
    ]


def _greeting(candidate: dict) -> str:
    contact_name = clean_text(candidate.get("lead_contact_name") or candidate.get("name", ""))
    surname = contact_name.split()[-1] if contact_name else ""
    role_title = clean_text(candidate.get("role_title", "")).lower()
    entity_type = candidate.get("entity_type", "Professor")
    if entity_type == "Professor" or "professor" in role_title:
        return f"Dear Professor {surname or contact_name},"
    if contact_name:
        return f"Dear {contact_name},"
    return "Dear Research Team,"


def generate_outreach_package(candidate: dict, candidate_profile: dict) -> dict:
    contact_name = clean_text(candidate.get("lead_contact_name") or candidate.get("name", "Professor"))
    university = candidate.get("university", "the group")
    interests_text = clean_text(candidate_profile.get("interests_text", "")) or "this research area"
    topic_anchor = _first(candidate.get("recent_topics", []), _first(candidate.get("research_tags", []), "your current research"))
    secondary_topic = _first(candidate.get("research_tags", [])[1:], _first(candidate.get("discipline_tags", []), topic_anchor))
    publication_anchor = _first(candidate.get("publications", []), _first(candidate.get("project_signals", []), topic_anchor))
    target_label = candidate.get("entity_type", "research target").lower()
    role_title = clean_text(candidate.get("role_title", "")) or candidate.get("entity_type", "Researcher")
    evidence = _student_evidence(candidate, candidate_profile)
    evidence_points = evidence["evidence_points"] if isinstance(evidence["evidence_points"], list) else []
    evidence_summary = "; ".join(evidence_points[:2]) if evidence_points else ""
    tool_summary = clean_text(str(evidence.get("tool_summary", ""))) or "my current technical toolkit"
    method_summary = clean_text(str(evidence.get("method_summary", "")))
    source_anchor = candidate.get("official_profile_url") or candidate.get("primary_source_url") or "the source page"

    subject_lines = _subject_lines(candidate, candidate_profile, topic_anchor, publication_anchor)
    personalization_lines = [
        f"I am reaching out specifically because your {role_title.lower()} work on {topic_anchor} is closely aligned with the research direction I want to pursue.",
        f"The research signals surfaced on {source_anchor} point especially strongly to {publication_anchor}.",
        f"My current preparation in {tool_summary} maps well onto the methods and topics visible in your work on {secondary_topic}.",
    ]

    cv_tailoring = [
        f"Move the strongest evidence for {topic_anchor} closer to the top of the CV so the fit is obvious immediately.",
        "Add one short bullet that explains what research question, method, or technical contribution your most relevant project actually involved.",
        f"Make your most relevant tools explicit near the top of the CV, especially {tool_summary}.",
    ]
    if evidence.get("coursework_lines"):
        cv_tailoring.append("If relevant coursework is important here, mention the strongest one-line coursework evidence directly in the email rather than leaving it buried in the education section.")
    if candidate.get("weaknesses"):
        cv_tailoring.append(candidate["weaknesses"][0])

    greeting = _greeting(candidate)
    stage = candidate_profile.get("academic_stage", "student").lower()
    email_lines = [
        greeting,
        "",
        f"I am {candidate_profile.get('name', 'a student')}, a {stage} interested in {interests_text}, and I am reaching out because your work on {topic_anchor} looks closely aligned with the direction I want to pursue.",
    ]
    if evidence_summary:
        email_lines.append(f"The most relevant preparation I can offer from my current background is {evidence_summary}.")
    else:
        evidence_fallback = clean_text(", ".join(candidate_profile.get("research_exposure", [])[:2]).lower()) or "project and analytical work"
        email_lines.append(f"My background so far includes {evidence_fallback}, together with hands-on work using {tool_summary}.")
    if method_summary:
        email_lines.append(f"I also have experience with methods and tools around {method_summary}, which seems relevant to the way your {target_label} approaches {secondary_topic}.")
    else:
        email_lines.append(f"I would be especially interested in contributing to or learning from work in this area at {university}.")
    email_lines.extend(
        [
            f"If you think there could be a fit, I would be glad to send a short summary of my background or discuss whether there may be a suitable way to contribute to this line of research at {university}.",
            "Thank you for your time and consideration.",
            "",
            "Best regards,",
            candidate_profile.get("name", "The student"),
        ]
    )

    follow_up = (
        "If you send this to an official address, wait about 7 to 10 business days before sending one concise follow-up. "
        "If no official email was found for this selected researcher, do not reuse another person’s address from the page."
    )

    return {
        "subject_lines": subject_lines[:3],
        "personalization_lines": personalization_lines[:3],
        "email_draft": "\n".join(email_lines),
        "cv_tailoring": cv_tailoring[:4],
        "follow_up": follow_up,
        "greeting": greeting,
        "recipient_email": candidate.get("official_email", ""),
        "selected_candidate_id": candidate.get("candidate_id", ""),
        "selected_candidate_name": contact_name,
        "selected_candidate_title": role_title,
    }
