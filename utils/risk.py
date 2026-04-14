from __future__ import annotations

from urllib.parse import urlparse

from utils.helpers import contains_any


SUSPICIOUS_PHRASES = [
    "unlimited earning",
    "unlimited income",
    "quick money",
    "start immediately",
    "whatsapp",
    "telegram",
    "no experience needed",
    "work from your phone",
    "commission only",
]


def assess_company_risk(job_text: str, company_name: str, job_title: str, job_url: str = "") -> dict:
    lowered = job_text.lower()
    word_count = len(job_text.split())
    score = 0
    flags: list[dict] = []
    company_signals: list[str] = []
    job_reality: list[str] = []

    domain = urlparse(job_url).netloc.lower() if job_url else ""
    named_company = bool(company_name.strip())

    if word_count < 140:
        score += 14
        flags.append({"flag": "vague_description", "severity": "medium", "reason": "The job text is short and may be missing practical detail."})
    else:
        company_signals.append("The posting contains enough detail to assess the core responsibilities.")

    if not named_company:
        score += 18
        flags.append({"flag": "missing_company_identity", "severity": "high", "reason": "No company name was provided."})
    else:
        company_signals.append(f"The employer is named as {company_name}.")

    if not contains_any(lowered, ["responsibilities", "what you will do", "you will", "day-to-day"]):
        score += 10
        flags.append({"flag": "unclear_responsibilities", "severity": "medium", "reason": "Responsibilities are not clearly laid out."})
    else:
        job_reality.append("Responsibilities are concrete enough to tell what success in the role should look like.")

    if not contains_any(lowered, ["salary", "benefits", "compensation", "$", "£", "€"]):
        score += 6
        flags.append({"flag": "missing_compensation_context", "severity": "low", "reason": "No salary or compensation detail is visible."})
        company_signals.append("Compensation is not listed, so candidates should verify pay before spending too much time.")
    else:
        company_signals.append("Compensation or benefits language is present, which is a credibility positive.")

    if contains_any(lowered, SUSPICIOUS_PHRASES):
        score += 24
        flags.append({"flag": "suspicious_wording", "severity": "high", "reason": "The wording includes phrases often associated with low-credibility job ads."})
        job_reality.append("The language reads more promotional than professional, which is a strong caution signal.")

    if contains_any(lowered, ["commission only", "commission-only", "1099", "independent contractor"]) and "salary" not in lowered:
        score += 18
        flags.append({"flag": "possible_commission_only", "severity": "high", "reason": "The pay model may be unclear or heavily commission based."})
        company_signals.append("The compensation model may be riskier than a standard salaried graduate role.")

    if ("entry level" in lowered or "graduate" in lowered or "junior" in lowered) and contains_any(
        lowered, ["5+ years", "6+ years", "7+ years"]
    ):
        score += 18
        flags.append({"flag": "unrealistic_requirements", "severity": "high", "reason": "The posting looks entry-level but asks for unusually senior experience."})
        job_reality.append("The experience bar looks inflated for an early-career title.")

    if domain:
        if any(domain.endswith(suffix) for suffix in ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com"]):
            score += 16
            flags.append({"flag": "personal_email_domain", "severity": "medium", "reason": "The job points to a consumer email domain rather than a company website."})
        elif "example.com" in domain:
            score += 8
            flags.append({"flag": "generic_domain", "severity": "low", "reason": "The URL uses a generic placeholder domain."})
        else:
            company_signals.append(f"The job URL uses the domain {domain}, which helps credibility.")
    else:
        score += 5
        flags.append({"flag": "missing_job_url", "severity": "low", "reason": "No job URL was available to cross-check the company presence."})

    if contains_any(lowered, ["mentor", "mentorship", "training", "structured learning", "manager support"]):
        company_signals.append("The post mentions learning support, which is a positive sign for an early-career role.")

    if not job_reality:
        job_reality.append("The role looks real enough to evaluate, but the posting leaves some questions unanswered.")
    if word_count >= 180 and contains_any(lowered, ["sql", "python", "excel", "analytics", "dashboard"]):
        job_reality.append("The responsibilities and tools line up with a believable junior knowledge-worker role.")
    if not company_signals:
        company_signals.append("There are not many positive trust signals in the available posting text.")

    if score >= 45:
        risk_level = "High"
    elif score >= 22:
        risk_level = "Medium"
    else:
        risk_level = "Low"

    return {
        "risk_level": risk_level,
        "risk_score": score,
        "flags": flags,
        "job_reality": job_reality[:4],
        "company_signals": company_signals[:5],
    }
