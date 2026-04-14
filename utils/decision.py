from __future__ import annotations


def compute_confidence(
    *,
    job_text: str,
    resume_text: str,
    scrape_result: dict,
    resume_result: dict,
    company_name: str,
    job_title: str,
) -> dict:
    score = 35

    job_words = len(job_text.split())
    if job_words >= 220:
        score += 20
    elif job_words >= 140:
        score += 15
    elif job_words >= 80:
        score += 9

    if resume_text:
        score += 15
    if resume_result.get("success"):
        score += 12
    if scrape_result.get("attempted") and scrape_result.get("success"):
        score += 8
    if scrape_result.get("attempted") and not scrape_result.get("success"):
        score -= 3
    if company_name:
        score += 5
    if job_title:
        score += 4
    if resume_result.get("fallback_used"):
        score -= 4
    if not resume_text:
        score -= 12

    score = max(25, min(96, score))

    explanation_parts = []
    explanation_parts.append("The confidence is higher when the app has enough job text to score reliably.")
    if resume_result.get("success"):
        explanation_parts.append("Resume parsing succeeded, which improves the evidence quality.")
    elif resume_text:
        explanation_parts.append("Resume text exists, but the parsing quality is weaker than a clean PDF extraction.")
    else:
        explanation_parts.append("No resume text was available, so this recommendation leans more heavily on the job posting alone.")

    if scrape_result.get("attempted") and not scrape_result.get("success"):
        explanation_parts.append("The URL scrape fell back to pasted text, which is still fine but slightly less certain.")

    return {"confidence": int(score), "explanation": " ".join(explanation_parts)}


def make_decision(
    *,
    fit_score: int,
    risk_level: str,
    strengths: list[str],
    gaps: list[str],
    company_name: str,
    job_title: str,
) -> dict:
    if risk_level == "High" or fit_score < 45:
        recommendation = "Skip"
    elif fit_score >= 70 and risk_level in {"Low", "Medium"}:
        recommendation = "Apply"
    elif fit_score >= 55 and risk_level == "Low":
        recommendation = "Consider"
    elif fit_score >= 65 and risk_level == "Medium":
        recommendation = "Consider"
    else:
        recommendation = "Skip"

    role_label = job_title or "this role"
    company_label = company_name or "the company"

    if recommendation == "Apply":
        rationale = (
            f"{role_label} looks like a credible target at {company_label}: the fit is strong enough to justify an application, "
            "and the risk does not outweigh the upside."
        )
    elif recommendation == "Consider":
        rationale = (
            f"{role_label} has some upside, but the match is not automatic. It is worth considering if you can quickly close the main gaps "
            "or verify the weaker signals."
        )
    else:
        rationale = (
            f"{role_label} is probably not the best use of time right now. The fit is weak, the risk is too high, or both."
        )

    if gaps and recommendation != "Skip":
        rationale += f" Biggest watch-out: {gaps[0].rstrip('.')}"
    elif strengths and recommendation == "Apply":
        rationale += f" Biggest positive: {strengths[0].rstrip('.')}"

    return {"recommendation": recommendation, "rationale": rationale}


def build_next_steps(
    *,
    recommendation: str,
    strengths: list[str],
    gaps: list[str],
    risk_flags: list[dict],
    company_name: str,
    job_title: str,
) -> list[str]:
    role_label = job_title or "the role"
    company_label = company_name or "the employer"

    if recommendation == "Apply":
        return [
            f"Tailor the top third of the resume to {role_label}, especially around the strongest overlap themes.",
            "Prepare two short stories that prove analytical impact, stakeholder communication, and learning speed.",
            f"Submit the application soon, then use LinkedIn and the company website to learn more about {company_label}.",
        ]

    if recommendation == "Consider":
        steps = [
            f"Decide whether you can strengthen the key missing evidence before applying to {role_label}.",
            "Research recent company news, team structure, and employee reviews to test the role quality.",
            "If the risk feels manageable, tailor the resume and apply only after tightening the weakest gap.",
        ]
        if gaps:
            steps[0] = f"Close the biggest gap first: {gaps[0].rstrip('.')}"
        return steps

    steps = [
        f"Save the application time and focus on roles closer to your current profile than {role_label}.",
        "Keep a short note on why this one was rejected so your search criteria get sharper over time.",
        "Only revisit this job if you later verify the risk flags or discover hidden upside.",
    ]
    if risk_flags:
        steps[2] = f"Only revisit this job if you can resolve the main red flag: {risk_flags[0]['reason']}"
    return steps
