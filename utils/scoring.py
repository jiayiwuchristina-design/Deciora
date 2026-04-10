from __future__ import annotations

from utils.helpers import clean_text, extract_keywords, parse_years_requirement


SKILL_ALIASES = {
    "sql": ["sql"],
    "python": ["python", "python notebooks", "jupyter"],
    "excel": ["excel", "spreadsheets", "spreadsheet"],
    "tableau": ["tableau"],
    "power bi": ["power bi"],
    "dashboarding": ["dashboarding", "dashboard", "dashboards", "data visualisation", "data visualization"],
    "data analysis": ["data analysis", "analytics", "analysis", "business intelligence", "reporting", "kpi"],
    "statistics": ["statistics", "econometrics"],
    "communication": [
        "communication",
        "stakeholder communication",
        "stakeholder management",
        "presentation",
        "presented",
        "non-technical",
    ],
    "experimentation": ["a/b testing", "ab testing", "split testing", "experimentation", "experiment"],
    "customer analytics": ["customer analytics", "customer insights", "retention analysis", "customer behavior", "customer behaviour"],
    "crm": ["crm", "salesforce", "hubspot"],
    "research": ["research", "research assistant", "survey"],
    "project management": ["project management", "project coordination"],
    "machine learning": ["machine learning"],
    "financial modeling": ["financial modeling", "financial modelling"],
    "javascript": ["javascript"],
    "react": ["react"],
    "figma": ["figma"],
}

FIELD_PATTERNS = {
    "analytics": ["analytics", "data science", "business analytics", "statistics", "economics"],
    "business": ["business", "commerce", "management", "marketing"],
    "technical": ["computer science", "engineering", "information systems"],
}


def extract_skills(text: str) -> list[str]:
    lowered = text.lower()
    found = [
        canonical
        for canonical, aliases in SKILL_ALIASES.items()
        if any(alias in lowered for alias in aliases)
    ]
    return sorted(set(found))


def keyword_overlap(job_text: str, resume_text: str) -> tuple[float, list[str]]:
    job_keywords = list(extract_keywords(job_text, limit=24))
    resume_lower = resume_text.lower()
    matched = [keyword for keyword in job_keywords if keyword in resume_lower]
    ratio = len(matched) / max(1, len(job_keywords))
    return ratio, matched


def education_relevance(job_text: str, education_text: str) -> tuple[int, str]:
    job_lower = job_text.lower()
    education_lower = education_text.lower()
    mentions_degree = any(term in job_lower for term in ["bachelor", "degree", "bsc", "ba", "msc"])
    if not education_lower:
        return (3 if not mentions_degree else 0), "No education evidence was found in the resume text."

    base_score = 10 if not mentions_degree else 12
    matched_fields = []
    for label, patterns in FIELD_PATTERNS.items():
        if any(pattern in job_lower for pattern in patterns) and any(pattern in education_lower for pattern in patterns):
            matched_fields.append(label)

    if matched_fields:
        base_score += 6
        explanation = f"Education appears relevant to the role, especially around {', '.join(matched_fields)}."
    elif mentions_degree and any(term in education_lower for term in ["bachelor", "bsc", "ba", "msc", "degree", "university"]):
        base_score += 2
        explanation = "The resume shows a degree, but the subject alignment is only partial."
    else:
        explanation = "Education is present, though the field match is not very explicit."

    return min(base_score, 20), explanation


def estimate_resume_experience_score(experience_text: str, full_resume_text: str) -> int:
    combined = f"{experience_text}\n{full_resume_text}".lower()
    signal_count = sum(
        combined.count(term)
        for term in ["intern", "project", "analyst", "assistant", "research", "dashboard", "client", "stakeholder"]
    )
    if signal_count >= 8:
        return 3
    if signal_count >= 4:
        return 2
    if signal_count >= 2:
        return 1
    return 0


def experience_relevance(job_text: str, experience_text: str, resume_text: str) -> tuple[int, str]:
    if not resume_text:
        return 0, "No resume evidence was available for experience matching."

    required_years = parse_years_requirement(job_text)
    evidence_level = estimate_resume_experience_score(experience_text, resume_text)

    if required_years is None:
        score = 18 if evidence_level >= 2 else 12 if evidence_level == 1 else 8
        return score, "The job does not specify strict years of experience, so projects and internships carry useful weight."

    if required_years <= 2 and evidence_level >= 2:
        return 20, "Internships and project work look appropriate for an early-career opening."
    if required_years <= 2 and evidence_level == 1:
        return 15, "There is some relevant experience, but the evidence is not especially deep yet."
    if required_years <= 3 and evidence_level >= 2:
        return 16, "The resume shows decent practical evidence against a modest experience bar."
    if evidence_level >= 1:
        return 10, f"The role asks for around {required_years} years, so the candidate may be slightly under the preferred experience range."
    return 4, f"The role asks for around {required_years} years, and the resume shows limited practical experience evidence."


def build_strengths(
    matched_skills: list[str],
    matched_keywords: list[str],
    education_note: str,
    experience_note: str,
    skill_score: int,
    keyword_score: int,
    education_score_value: int,
    experience_score_value: int,
) -> list[str]:
    strengths: list[str] = []
    if matched_skills:
        strengths.append(f"Direct skill overlap is visible in {', '.join(matched_skills[:4])}.")
    if keyword_score >= 12 and matched_keywords:
        strengths.append(f"The resume mirrors important job language such as {', '.join(matched_keywords[:4])}.")
    if education_score_value >= 14:
        strengths.append(education_note)
    if experience_score_value >= 14:
        strengths.append(experience_note)
    if skill_score >= 24 and len(strengths) < 3:
        strengths.append("Core tool coverage is strong enough to justify a serious first-pass application.")
    return strengths or ["The profile shows some transferable potential, but the fit evidence is still fairly broad."]


def build_gaps(
    missing_skills: list[str],
    education_score_value: int,
    experience_score_value: int,
    job_text: str,
    resume_text: str,
) -> list[str]:
    gaps: list[str] = []
    if len(missing_skills) >= 2:
        gaps.append(f"Missing or weak evidence for {', '.join(missing_skills[:4])}.")
    if education_score_value <= 10 and "degree" in job_text.lower():
        gaps.append("The academic background is not strongly tailored to the stated degree preference.")
    if experience_score_value <= 10:
        gaps.append("The resume may not yet show enough practical experience for the employer's preferred scope.")
    if resume_text and "communication" not in resume_text.lower() and "stakeholder" in job_text.lower():
        gaps.append("The resume could make stakeholder communication more explicit.")
    return gaps or ["No major gaps stood out from the available text."]


def score_fit(job_text: str, resume_text: str, resume_sections: dict, job_title: str = "") -> dict:
    job_text = clean_text(job_text)
    resume_text = clean_text(resume_text)
    education_text = resume_sections.get("education", "")
    experience_text = resume_sections.get("experience", "")
    skills_text = resume_sections.get("skills", "")

    job_skills = extract_skills(job_text)
    resume_skills = extract_skills(f"{resume_text}\n{skills_text}")
    matched_skills = [skill for skill in job_skills if skill in resume_skills]
    missing_skills = [skill for skill in job_skills if skill not in resume_skills]

    skill_ratio = len(matched_skills) / max(1, len(job_skills))
    skill_score = round(skill_ratio * 40) if job_skills else 24

    keyword_ratio, matched_keywords = keyword_overlap(job_text, resume_text)
    keyword_score_value = round(keyword_ratio * 20)

    education_score_value, education_note = education_relevance(job_text, education_text)
    experience_score_value, experience_note = experience_relevance(job_text, experience_text, resume_text)

    fit_score = min(100, max(0, skill_score + keyword_score_value + education_score_value + experience_score_value))
    strengths = build_strengths(
        matched_skills,
        matched_keywords,
        education_note,
        experience_note,
        skill_score,
        keyword_score_value,
        education_score_value,
        experience_score_value,
    )
    gaps = build_gaps(
        missing_skills=missing_skills,
        education_score_value=education_score_value,
        experience_score_value=experience_score_value,
        job_text=job_text,
        resume_text=resume_text,
    )

    return {
        "fit_score": int(fit_score),
        "strengths": strengths[:4],
        "gaps": gaps[:4],
        "breakdown": {
            "job_title": job_title,
            "skill_score": {
                "score": skill_score,
                "max": 40,
                "ratio": round(skill_ratio, 2),
                "matched_skills": matched_skills,
                "missing_skills": missing_skills[:6],
                "job_skills": job_skills,
                "resume_skills": resume_skills,
            },
            "keyword_score": {
                "score": keyword_score_value,
                "max": 20,
                "matched_keywords": matched_keywords[:8],
                "ratio": round(keyword_ratio, 2),
            },
            "education_score": {
                "score": education_score_value,
                "max": 20,
                "summary": education_note,
                "education_text_present": bool(education_text),
            },
            "experience_score": {
                "score": experience_score_value,
                "max": 20,
                "summary": experience_note,
                "experience_text_present": bool(experience_text),
                "years_required": parse_years_requirement(job_text),
            },
            "fit_score_total": int(fit_score),
        },
    }
