from __future__ import annotations

import json
import re
from typing import Any

import streamlit as st

from sample_data import (
    SAMPLE_COMPANY_NAME,
    SAMPLE_COMPANY_PROFILE,
    SAMPLE_JOB_DESCRIPTION,
    SAMPLE_JOB_TITLE,
    SAMPLE_JOB_URL,
    SAMPLE_RESUME_TEXT,
)
from utils.decision import build_next_steps, compute_confidence, make_decision
from utils.helpers import clean_text
from utils.llm import call_llm_analysis, is_llm_configured
from utils.parsing import parse_resume_pdf, parse_resume_text, scrape_job_url
from utils.risk import assess_company_risk
from utils.scoring import score_fit
from utils.ui import (
    escape,
    normalize_section_content,
    render_coverage_section,
    render_decision_banner,
    render_hero,
    render_list_section,
    render_metric_card,
    render_pills,
    render_text_section,
)


JOB_STATE_DEFAULTS = {
    "job_url": "",
    "job_description": "",
    "company_name": "",
    "job_title": "",
    "use_demo_resume": True,
    "career_analysis_result": None,
    "career_analysis_error": "",
}


def init_job_state() -> None:
    for key, value in JOB_STATE_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def load_job_demo_inputs() -> None:
    st.session_state["job_url"] = SAMPLE_JOB_URL
    st.session_state["job_description"] = SAMPLE_JOB_DESCRIPTION
    st.session_state["company_name"] = SAMPLE_COMPANY_NAME
    st.session_state["job_title"] = SAMPLE_JOB_TITLE
    st.session_state["use_demo_resume"] = True
    st.session_state["career_analysis_result"] = None
    st.session_state["career_analysis_error"] = ""


def normalize_job_llm_result(result: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    merged = fallback.copy()
    merged.update(result)
    merged["fit_score"] = int(max(0, min(100, merged.get("fit_score", fallback["fit_score"]))))
    merged["confidence"] = int(max(0, min(100, merged.get("confidence", fallback["confidence"]))))
    merged["risk_level"] = str(merged.get("risk_level", fallback["risk_level"])).title()
    merged["recommendation"] = str(merged.get("recommendation", fallback["recommendation"])).title()

    for list_key in ("strengths", "gaps", "job_reality", "company_signals", "next_steps"):
        value = merged.get(list_key, fallback.get(list_key, []))
        items, paragraph = normalize_section_content(value)
        if items:
            merged[list_key] = items
        elif paragraph:
            merged[list_key] = [paragraph]
        else:
            merged[list_key] = fallback.get(list_key, [])

    merged["recommendation_rationale"] = str(
        merged.get("recommendation_rationale", fallback.get("recommendation_rationale", ""))
    ).strip()
    merged["confidence_explanation"] = str(
        merged.get("confidence_explanation", fallback.get("confidence_explanation", ""))
    ).strip()
    return merged


def format_series(items: list[str], limit: int = 4) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for raw_item in items:
        item = str(raw_item).strip().rstrip(".")
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        cleaned.append(item)
        seen.add(lowered)
        if len(cleaned) >= limit:
            break

    if not cleaned:
        return ""
    if len(cleaned) == 1:
        return cleaned[0]
    if len(cleaned) == 2:
        return f"{cleaned[0]} and {cleaned[1]}"
    return f"{', '.join(cleaned[:-1])}, and {cleaned[-1]}"


def unique_non_empty(items: list[str], limit: int = 4) -> list[str]:
    unique_items: list[str] = []
    seen: set[str] = set()
    for raw_item in items:
        item = str(raw_item).strip()
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        unique_items.append(item)
        seen.add(lowered)
        if len(unique_items) >= limit:
            break
    return unique_items


def has_gap_signal(gaps: list[str], needles: tuple[str, ...]) -> bool:
    gap_text = " ".join(gaps).lower()
    return any(needle in gap_text for needle in needles)


def mentions_any(text: str, phrases: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(phrase in lowered for phrase in phrases)


def has_quantified_evidence(text: str) -> bool:
    lowered = text.lower()
    impact_patterns = (
        r"\b\d+(?:\.\d+)?\s*(?:%|percent|x|k|m|million|thousand)\b",
        r"\b(?:improved|increased|reduced|saved|cut|boosted|lifted|grew)\b[^.\n]{0,40}\b\d+",
        r"\b\d+\s*(?:stakeholders?|users?|customers?|clients?|teams?|reports?|dashboards?|hours?|days?|weeks?|months?|projects?|queries?|experiments?|metrics?|records?|rows?)\b",
        r"(?:£|\$|€)\s*\d+",
    )
    return any(re.search(pattern, lowered) for pattern in impact_patterns)


def build_job_layer3_content(result: dict[str, Any]) -> dict[str, Any]:
    details = result.get("details", {})
    score_breakdown = details.get("score_breakdown", {})
    skill_score = score_breakdown.get("skill_score", {})
    keyword_score = score_breakdown.get("keyword_score", {})
    education_score = score_breakdown.get("education_score", {})
    experience_score = score_breakdown.get("experience_score", {})
    risk_flags = details.get("risk_flags", [])
    gaps = result.get("gaps", [])
    raw_data = details.get("raw_data", {})
    scrape_result = raw_data.get("scrape_result", {})
    scrape_sources = scrape_result.get("sources", {})
    resume_parse = raw_data.get("resume_parse", {})

    job_text = details.get("job_text", "")
    matched_skills = skill_score.get("matched_skills", [])
    missing_skills = skill_score.get("missing_skills", [])
    job_skills = skill_score.get("job_skills", [])
    matched_keywords = keyword_score.get("matched_keywords", [])
    recommendation = result.get("recommendation", "Consider")
    confidence = int(result.get("confidence", 0))
    resume_text = details.get("resume_text", "")
    resume_sections = details.get("resume_sections", {})
    experience_text = resume_sections.get("experience", "")
    education_text = resume_sections.get("education", "")
    job_source = result.get("sources", {}).get("job_source", "")
    resume_source = result.get("sources", {}).get("resume_source", "")
    url_attempted = bool(result.get("sources", {}).get("url_attempted"))
    url_scrape_success = bool(result.get("sources", {}).get("url_scrape_success"))
    url_error = result.get("sources", {}).get("url_error", "")

    needs_reporting = mentions_any(job_text, ("reporting", "weekly performance", "kpi", "ad hoc analysis", "performance"))
    has_reporting = mentions_any(resume_text, ("reporting", "report", "kpi"))
    needs_dashboard = mentions_any(job_text, ("dashboard", "tableau", "power bi", "dashboarding"))
    has_dashboard = mentions_any(resume_text, ("dashboard", "tableau", "power bi"))
    needs_stakeholder = mentions_any(
        job_text,
        ("stakeholder", "non-technical", "product", "marketing", "operations", "customer success", "commercial"),
    )
    has_stakeholder = mentions_any(
        resume_text,
        ("stakeholder", "presented", "presentation", "cross-functional", "non-technical", "client", "manager", "founder"),
    )
    needs_analysis = mentions_any(job_text, ("analysis", "analytics", "insights", "recommendations"))
    has_analysis = mentions_any(resume_text, ("analysis", "analytics", "insights", "recommendations", "analysed", "analyzed"))
    needs_customer = mentions_any(job_text, ("customer analytics", "customer insights", "retention", "crm"))
    has_customer = mentions_any(resume_text, ("customer analytics", "customer", "retention", "crm", "salesforce", "hubspot"))
    needs_experimentation = mentions_any(job_text, ("a/b testing", "ab testing", "experimentation", "experiment"))
    has_experimentation = mentions_any(resume_text, ("a/b testing", "ab testing", "experimentation", "experiment"))
    has_metrics = has_quantified_evidence(experience_text or resume_text)
    enough_evidence = bool(job_text and resume_text)
    lead_themes = matched_skills or job_skills or matched_keywords

    positive_signals: list[str] = []
    if matched_skills:
        positive_signals.append(f"direct proof of {format_series(matched_skills, limit=3)}")
    if experience_score.get("score", 0) >= 14:
        positive_signals.append("hands-on internship or project work at roughly the right level")
    if needs_stakeholder and has_stakeholder:
        positive_signals.append("stakeholder-facing communication evidence")
    if needs_reporting and has_reporting:
        positive_signals.append("reporting or KPI work already visible in the CV")

    limiting_signals: list[str] = []
    if missing_skills:
        limiting_signals.append(f"missing direct proof of {format_series(missing_skills, limit=3)}")
    if experience_score.get("score", 0) <= 12:
        limiting_signals.append("lighter hands-on scope than the role appears to want")
    if not has_metrics and resume_text:
        limiting_signals.append("no quantified achievement tied to the relevant work")
    if risk_flags:
        limiting_signals.append(risk_flags[0].get("reason", "").rstrip("."))

    primary_positive = format_series(positive_signals, limit=3) or "some transferable evidence"
    primary_limit = format_series(limiting_signals, limit=2) or "no single blocker, but the application still needs a sharp tailoring pass"
    why_intro = f"{recommendation} is being driven by {primary_positive}. The main hold-back is {primary_limit}."

    why_items: list[str] = []
    if matched_skills:
        why_items.append(
            f"Decision support: the strongest overlap is in {format_series(matched_skills, limit=4)}, which maps directly to the core role requirements."
        )
    elif matched_keywords:
        why_items.append(
            f"Decision support: the CV already uses role-relevant language such as {format_series(matched_keywords, limit=4)}, which helps the fit case."
        )

    if missing_skills:
        why_items.append(
            f"Main hold-back: there is still no direct CV evidence for {format_series(missing_skills, limit=4)}, so the match is not fully proven."
        )
    elif experience_score.get("score", 0) <= 12:
        why_items.append("Main hold-back: the CV does not yet show enough role-shaped analytical work, reporting scope, or delivery depth.")

    if risk_flags:
        why_items.append(f"Risk effect: {risk_flags[0].get('reason', '').rstrip('.')}.")
    else:
        why_items.append("Risk effect: the posting has enough concrete detail to treat this as a real opportunity rather than a vague listing.")

    if recommendation == "Apply":
        why_items.append("Time-use judgement: this looks worth a tailored application now rather than more analysis first.")
    elif recommendation == "Consider":
        why_items.append("Time-use judgement: only keep this live if you can close the main proof gaps quickly before applying.")
    else:
        why_items.append("Time-use judgement: this is not worth much more effort unless you can add missing proof or verify the weaker signals.")

    improve_items: list[str] = []
    if lead_themes:
        improve_items.append(
            f"CV opening: put {format_series(lead_themes, limit=3)} in the summary and again in the first relevant experience bullet so the match is visible in seconds."
        )
    if matched_keywords:
        improve_items.append(
            f"Keyword alignment: work in job language like {format_series(matched_keywords, limit=4)} where it is true, instead of leaving that experience implied."
        )
    if missing_skills:
        improve_items.append(
            f"Missing tool proof: if you have used {format_series(missing_skills, limit=3)} in coursework, projects, or internships, add one bullet for where you used it, what you produced, and who used the output."
        )
    if needs_reporting:
        improve_items.append(
            "Reporting proof: make one bullet explicit about KPI tracking, reporting cadence, or ad hoc analysis, because that responsibility is named in the role."
        )
    if needs_dashboard:
        improve_items.append(
            "Tool-to-outcome proof: pair one dashboard or BI tool bullet with an audience, decision, or business question so it reads as useful work, not just software usage."
        )
    if needs_stakeholder:
        improve_items.append(
            "Stakeholder framing: show who received your analysis and what recommendation, handoff, or action followed from it."
        )
    if not has_metrics and resume_text:
        improve_items.append(
            "Impact evidence: add numbers to the strongest bullets, such as report frequency, dataset size, KPI movement, time saved, or number of stakeholders supported."
        )
    elif has_metrics:
        improve_items.append(
            "Ordering: move the strongest quantified analytics bullet higher so the employer sees evidence of outcome, not just activity."
        )
    if education_score.get("score", 0) <= 10 and education_text:
        improve_items.append(
            "Education fit: add the most relevant modules, dissertation topic, or capstone if the degree title alone does not make the subject match obvious."
        )
    if needs_experimentation and not has_experimentation:
        improve_items.append(
            "Nice-to-have coverage: if you have any A/B testing, experiment measurement, or hypothesis work, add it explicitly before applying."
        )
    if recommendation != "Apply" and missing_skills:
        improve_items.append(
            f"Application filter: if you cannot honestly add proof of {format_series(missing_skills, limit=2)}, this role should stay lower priority."
        )

    fallback_improvements = [
        "Experience bullets: rewrite the first relevant bullet in a tool + task + result format so it reads like evidence, not a duty list.",
        "Tailoring pass: cut generic wording and keep only bullets that help prove fit for this specific role.",
        "Role proof check: before applying, make sure the CV clearly shows one tool, one responsibility, and one outcome that match the posting.",
    ]
    improve_items = unique_non_empty(improve_items, limit=6)
    if enough_evidence:
        for fallback_item in fallback_improvements:
            if len(improve_items) >= 3:
                break
            improve_items.append(fallback_item)
    improve_items = unique_non_empty(improve_items, limit=5)

    missing_intro = "These are the proof points most likely to weaken the application in a first screen."
    missing_items: list[str] = []
    if not resume_text:
        missing_items.append("Core CV evidence: no resume text was available, so the app could not verify tools, experience, or achievements from your side.")
    if missing_skills:
        missing_items.append(
            f"Missing tool evidence: no direct CV proof of {format_series(missing_skills, limit=4)}, even though those tools look central to the role."
        )
    if needs_reporting and not has_reporting:
        missing_items.append("Missing reporting evidence: no clear example of KPI tracking, recurring reporting, or ad hoc analysis work.")
    if needs_dashboard and not has_dashboard:
        missing_items.append("Missing dashboard evidence: no clear example of building dashboards or BI outputs for a stakeholder or team.")
    if needs_analysis and not has_analysis:
        missing_items.append("Missing analysis evidence: no bullet clearly shows analysis turning into a recommendation, decision, or business action.")
    if needs_stakeholder and not has_stakeholder:
        missing_items.append("Missing stakeholder evidence: limited proof of presenting findings or working with non-technical partners.")
    if not has_metrics and resume_text:
        missing_items.append("Missing impact evidence: the relevant bullets are not quantified, so competitiveness is harder to judge.")
    if education_score.get("score", 0) <= 10 and "degree" in job_text.lower():
        missing_items.append("Weak subject alignment: the CV does not clearly connect the degree or coursework to the preferred field.")
    if needs_customer and not has_customer:
        missing_items.append("Missing domain exposure: no clear evidence of customer, product, retention, or CRM-related analysis.")
    if needs_experimentation and not has_experimentation:
        missing_items.append("Missing experimentation exposure: no clear evidence of A/B testing or experiment measurement.")
    if experience_score.get("score", 0) <= 12:
        missing_items.append("Limited experience depth: the current CV does not yet show enough hands-on project or internship scope for this role.")
    if has_gap_signal(gaps, ("communication", "stakeholder")) and not needs_stakeholder:
        missing_items.append("Communication proof: the CV still under-shows presentation or stakeholder-facing work.")
    missing_items = unique_non_empty(missing_items, limit=4)
    if not missing_items:
        missing_intro = "No major competitiveness gaps stood out from the available evidence. The main task now is sharper framing, not brand-new proof."
        missing_items = ["No critical proof point is obviously missing; the main gain now is making the best evidence easier to spot quickly."]

    coverage_rows: list[dict[str, str]] = []
    if url_scrape_success:
        coverage_rows.append(
            {
                "label": "Job page",
                "status": "Extracted",
                "tone": "success",
                "detail": "The live job page was extracted successfully and used as the main source for role requirements.",
            }
        )
    elif job_source == "Pasted job description":
        coverage_rows.append(
            {
                "label": "Job page",
                "status": "Manual source",
                "tone": "info",
                "detail": "Fit was judged from pasted job text, so role coverage is usable but company-site context is still limited.",
            }
        )
    else:
        coverage_rows.append(
            {
                "label": "Job page",
                "status": "Partial",
                "tone": "partial",
                "detail": url_error or "Only a partial or fallback version of the job text was available, so the role read is less reliable.",
            }
        )

    same_domain_pages = scrape_result.get("same_domain_pages", [])
    if url_attempted and url_scrape_success and scrape_sources.get("same_domain_pages"):
        coverage_rows.append(
            {
                "label": "Same-domain company pages",
                "status": "Partially extracted",
                "tone": "partial",
                "detail": f"Pulled {len(same_domain_pages)} same-domain page(s), which adds some company context beyond the job ad itself.",
            }
        )
    elif url_attempted and url_scrape_success:
        coverage_rows.append(
            {
                "label": "Same-domain company pages",
                "status": "Not found",
                "tone": "missing",
                "detail": "No supporting company pages were pulled, so team, culture, and credibility context remains thin.",
            }
        )
    else:
        coverage_rows.append(
            {
                "label": "Same-domain company pages",
                "status": "Not checked",
                "tone": "info",
                "detail": "No reliable live scrape was available, so broader company-page coverage could not be checked.",
            }
        )

    if url_attempted and url_scrape_success and scrape_sources.get("benefits"):
        coverage_rows.append(
            {
                "label": "Benefits information",
                "status": "Found",
                "tone": "success",
                "detail": "Benefits or compensation language was found, which helps judge whether the role is worth deeper follow-up.",
            }
        )
    elif url_attempted and url_scrape_success:
        coverage_rows.append(
            {
                "label": "Benefits information",
                "status": "Not found",
                "tone": "missing",
                "detail": "Benefits or compensation were not visible, so pay and package should be verified before investing much more time.",
            }
        )
    else:
        coverage_rows.append(
            {
                "label": "Benefits information",
                "status": "Not checked",
                "tone": "info",
                "detail": "Benefits coverage depends on a successful live page extraction, which was not available here.",
            }
        )

    if resume_source == "Built-in demo resume":
        coverage_rows.append(
            {
                "label": "CV PDF",
                "status": "Demo source",
                "tone": "info",
                "detail": "The app used the built-in demo resume rather than a personal CV upload, so the result is not personalised.",
            }
        )
    elif resume_parse.get("success") and not resume_parse.get("fallback_used"):
        page_count = int(resume_parse.get("page_count") or 0)
        coverage_rows.append(
            {
                "label": "CV PDF",
                "status": "Parsed successfully",
                "tone": "success",
                "detail": f"Resume text was parsed from {page_count} page(s) of the uploaded PDF and used in the fit judgement.",
            }
        )
    elif resume_parse.get("fallback_used"):
        coverage_rows.append(
            {
                "label": "CV PDF",
                "status": "Fallback used",
                "tone": "partial",
                "detail": "The uploaded PDF did not parse cleanly, so the fit result is fallback-based rather than fully tied to your own CV.",
            }
        )
    else:
        coverage_rows.append(
            {
                "label": "CV PDF",
                "status": "Missing",
                "tone": "missing",
                "detail": "No resume text was available, so the recommendation leans much more heavily on the job side than on your profile.",
            }
        )

    coverage_rows.append(
        {
            "label": "External reputation",
            "status": "Not fetched",
            "tone": "info",
            "detail": "Third-party reviews, public sentiment, and outside reputation checks were not fetched, so trust checks still need manual follow-up.",
        }
    )

    missing_coverage_items: list[str] = []
    if not resume_text:
        missing_coverage_items.append("resume evidence")
    if resume_source == "Built-in demo resume":
        missing_coverage_items.append("your own CV evidence")
    if not url_scrape_success:
        missing_coverage_items.append("live job-page context")
    if not scrape_sources.get("same_domain_pages"):
        missing_coverage_items.append("broader company-page context")
    if not scrape_sources.get("benefits"):
        missing_coverage_items.append("benefits or pay detail")
    missing_coverage_items.append("external public signals")

    if url_scrape_success and resume_parse.get("success") and not resume_parse.get("fallback_used") and confidence >= 75:
        coverage_summary_label = "Strong coverage"
        coverage_summary_tone = "strong"
        coverage_summary_detail = (
            "Enough evidence to make a grounded first-pass fit call: the live role text and your resume were both available. "
            "The main blind spot is external public reputation data."
        )
    elif job_text and resume_text:
        coverage_summary_label = "Moderate coverage"
        coverage_summary_tone = "moderate"
        coverage_summary_detail = (
            f"Enough evidence to assess fit, but important context is still missing. The biggest gaps are {format_series(missing_coverage_items, limit=2)}."
        )
    else:
        coverage_summary_label = "Limited coverage"
        coverage_summary_tone = "limited"
        coverage_summary_detail = (
            f"Fit judgement is tentative because the evidence base is incomplete. The biggest gaps are {format_series(missing_coverage_items, limit=3)}."
        )

    return {
        "why": {"intro": why_intro, "items": unique_non_empty(why_items, limit=4)},
        "improve": {
            "intro": "These are the highest-value edits to make before you spend time on this application.",
            "items": improve_items,
        },
        "missing": {"intro": missing_intro, "items": missing_items},
        "coverage": {
            "summary_label": coverage_summary_label,
            "summary_detail": coverage_summary_detail,
            "summary_tone": coverage_summary_tone,
            "rows": coverage_rows,
        },
    }


def run_job_analysis(
    *,
    job_url: str,
    job_description: str,
    company_name: str,
    job_title: str,
    uploaded_resume: Any,
    use_demo_resume: bool,
    use_llm: bool,
) -> dict[str, Any]:
    cleaned_jd_input = clean_text(job_description)
    scrape_result: dict[str, Any] = {"attempted": False, "success": False, "text": "", "error": ""}

    if job_url.strip():
        scrape_result = scrape_job_url(job_url.strip())

    if scrape_result.get("success"):
        final_job_text = scrape_result["text"]
        job_source = "Scraped from URL"
    elif cleaned_jd_input:
        final_job_text = cleaned_jd_input
        job_source = "Pasted job description"
    else:
        final_job_text = clean_text(scrape_result.get("text", ""))
        job_source = "Partial URL extraction"

    if not final_job_text:
        raise ValueError("Please provide a job URL or paste a job description so the engine has something to analyze.")

    resume_source = "No resume provided"
    if uploaded_resume is not None:
        resume_result = parse_resume_pdf(uploaded_resume.getvalue())
        if resume_result.get("success"):
            resume_source = "Uploaded PDF resume"
        elif use_demo_resume:
            resume_result = parse_resume_text(SAMPLE_RESUME_TEXT)
            resume_result["success"] = True
            resume_result["fallback_used"] = True
            resume_result["error"] = "PDF parsing failed, so the built-in demo resume was used instead."
            resume_source = "Demo resume fallback"
        else:
            resume_source = "Uploaded PDF could not be parsed"
    elif use_demo_resume:
        resume_result = parse_resume_text(SAMPLE_RESUME_TEXT)
        resume_result["success"] = True
        resume_result["fallback_used"] = True
        resume_source = "Built-in demo resume"
    else:
        resume_result = {
            "success": False,
            "text": "",
            "page_count": 0,
            "sections": {"education": "", "experience": "", "skills": "", "certifications": "", "other": ""},
            "error": "",
            "fallback_used": False,
        }

    final_company_name = company_name.strip()
    final_job_title = job_title.strip()

    fit_result = score_fit(
        job_text=final_job_text,
        resume_text=resume_result.get("text", ""),
        resume_sections=resume_result.get("sections", {}),
        job_title=final_job_title,
    )
    risk_result = assess_company_risk(
        job_text=final_job_text,
        company_name=final_company_name,
        job_title=final_job_title,
        job_url=job_url.strip(),
    )
    confidence_result = compute_confidence(
        job_text=final_job_text,
        resume_text=resume_result.get("text", ""),
        scrape_result=scrape_result,
        resume_result=resume_result,
        company_name=final_company_name,
        job_title=final_job_title,
    )
    decision_result = make_decision(
        fit_score=fit_result["fit_score"],
        risk_level=risk_result["risk_level"],
        strengths=fit_result["strengths"],
        gaps=fit_result["gaps"],
        company_name=final_company_name,
        job_title=final_job_title,
    )
    next_steps = build_next_steps(
        recommendation=decision_result["recommendation"],
        strengths=fit_result["strengths"],
        gaps=fit_result["gaps"],
        risk_flags=risk_result["flags"],
        company_name=final_company_name,
        job_title=final_job_title,
    )

    fallback_result: dict[str, Any] = {
        "fit_score": fit_result["fit_score"],
        "risk_level": risk_result["risk_level"],
        "recommendation": decision_result["recommendation"],
        "confidence": confidence_result["confidence"],
        "strengths": fit_result["strengths"],
        "gaps": fit_result["gaps"],
        "job_reality": risk_result["job_reality"],
        "company_signals": risk_result["company_signals"],
        "next_steps": next_steps,
        "recommendation_rationale": decision_result["rationale"],
        "confidence_explanation": confidence_result["explanation"],
    }

    llm_error = ""
    analysis_mode = "Deterministic mode"
    if use_llm and is_llm_configured():
        llm_result, llm_error = call_llm_analysis(
            payload={
                "job_title": final_job_title,
                "company_name": final_company_name,
                "job_url": job_url.strip(),
                "job_text": final_job_text,
                "resume_text": resume_result.get("text", ""),
                "resume_sections": resume_result.get("sections", {}),
                "fit_breakdown": fit_result["breakdown"],
                "risk_flags": risk_result["flags"],
                "fallback_result": fallback_result,
            }
        )
        if llm_result:
            fallback_result = normalize_job_llm_result(llm_result, fallback_result)
            analysis_mode = "Optional LLM mode"

    return {
        **fallback_result,
        "analysis_mode": analysis_mode,
        "llm_error": llm_error,
        "sources": {
            "job_source": job_source,
            "resume_source": resume_source,
            "url_attempted": bool(job_url.strip()),
            "url_scrape_success": bool(scrape_result.get("success")),
            "url_error": scrape_result.get("error", ""),
        },
        "details": {
            "job_text": final_job_text,
            "resume_text": resume_result.get("text", ""),
            "resume_sections": resume_result.get("sections", {}),
            "score_breakdown": fit_result["breakdown"],
            "risk_flags": risk_result["flags"],
            "raw_data": {
                "company_name": final_company_name,
                "job_title": final_job_title,
                "job_url": job_url.strip(),
                "job_source": job_source,
                "resume_source": resume_source,
                "scrape_result": scrape_result,
                "resume_parse": {
                    "success": resume_result.get("success"),
                    "page_count": resume_result.get("page_count"),
                    "error": resume_result.get("error", ""),
                    "fallback_used": resume_result.get("fallback_used", False),
                },
                "company_profile": SAMPLE_COMPANY_PROFILE if final_company_name == SAMPLE_COMPANY_NAME else {},
            },
        },
    }


def render_job_sidebar() -> bool:
    st.sidebar.markdown("## Career Track")
    st.sidebar.markdown(
        "\n".join(
            [
                "1. Pull job text from a URL or paste it manually.",
                "2. Parse a PDF resume or use the built-in demo profile.",
                "3. Score fit, flag risk, and recommend whether to apply.",
            ]
        )
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("Load Demo Career Inputs", use_container_width=True):
        load_job_demo_inputs()

    llm_ready = is_llm_configured()
    use_llm = st.sidebar.checkbox(
        "Use optional LLM enhancement",
        value=False,
        disabled=not llm_ready,
        help="When enabled and configured, the app asks an OpenAI-compatible model to refine the deterministic job-decision output.",
    )
    st.sidebar.caption("LLM configured" if llm_ready else "LLM not configured. Deterministic mode remains fully functional.")
    return use_llm


def render_job_results(result: dict[str, Any]) -> None:
    layer3 = build_job_layer3_content(result)
    st.markdown('<div class="divider-gap"></div>', unsafe_allow_html=True)
    render_pills(
        [
            f"Mode: {result['analysis_mode']}",
            f"Job source: {result['sources']['job_source']}",
            f"Resume source: {result['sources']['resume_source']}",
        ]
    )
    render_decision_banner("Decision-first summary", result["recommendation_rationale"])
    if result["sources"]["url_attempted"] and not result["sources"]["url_scrape_success"] and result["sources"]["url_error"]:
        st.info(f'Job URL fallback used: {result["sources"]["url_error"]}')
    if result.get("llm_error"):
        st.info(f"LLM mode was attempted but fell back to deterministic logic: {result['llm_error']}")

    st.markdown("### Layer 1 · Decision")
    fit_col, risk_col, rec_col = st.columns(3, gap="large")
    with fit_col:
        render_metric_card(
            "1. Fit Score",
            f'{result["fit_score"]}/100',
            "Higher is better. This blends skills, keywords, education, and experience alignment.",
        )
        st.progress(result["fit_score"] / 100)
    with risk_col:
        risk_color = {
            "Low": ("#ecfeff", "#155e75", "#a5f3fc"),
            "Medium": ("#fffbeb", "#92400e", "#fde68a"),
            "High": ("#fef2f2", "#991b1b", "#fecaca"),
        }.get(result["risk_level"], ("#f8fafc", "#334155", "#cbd5e1"))
        badge = (
            f'<span class="risk-badge" style="background:{risk_color[0]};color:{risk_color[1]};'
            f'border:1px solid {risk_color[2]};">{escape(result["risk_level"])}</span>'
        )
        render_metric_card(
            "2. Risk Level",
            result["risk_level"],
            "Flags vague, suspicious, or low-credibility signals that could waste application time.",
            badge_html=badge,
        )
    with rec_col:
        rec_color = {
            "Apply": ("#ecfdf5", "#166534", "#86efac"),
            "Consider": ("#eff6ff", "#1d4ed8", "#bfdbfe"),
            "Skip": ("#fff7ed", "#c2410c", "#fdba74"),
        }.get(result["recommendation"], ("#f8fafc", "#334155", "#cbd5e1"))
        badge = (
            f'<span class="rec-badge" style="background:{rec_color[0]};color:{rec_color[1]};'
            f'border:1px solid {rec_color[2]};">{escape(result["recommendation"])}</span>'
        )
        render_metric_card(
            "3. Recommendation",
            result["recommendation"],
            result["recommendation_rationale"],
            badge_html=badge,
        )

    st.markdown("### Layer 2 · Explanation")
    render_text_section(4, "Confidence", f'{result["confidence"]}/100 confidence. {result["confidence_explanation"]}')
    render_list_section(5, "Strengths", result["strengths"], "No standout strengths were detected.")
    render_list_section(6, "Gaps", result["gaps"], "No major gaps were detected.")
    render_list_section(7, "Job Reality", result["job_reality"], "No job reality notes were generated.")
    render_list_section(8, "Company Signals", result["company_signals"], "No company signals were generated.")
    render_list_section(9, "Next Steps", result["next_steps"], "No next steps were generated.")

    st.markdown("### Layer 3 · Before You Apply")
    render_list_section(10, "Why This Recommendation", layer3["why"]["items"], "No recommendation drivers were generated.", intro=layer3["why"]["intro"])
    render_list_section(11, "How To Improve Before Applying", layer3["improve"]["items"], "No improvement actions were generated.", intro=layer3["improve"]["intro"])
    render_list_section(12, "Missing Evidence", layer3["missing"]["items"], "No missing evidence items were generated.", intro=layer3["missing"]["intro"])
    render_coverage_section(
        13,
        "Evidence & Source Coverage",
        layer3["coverage"]["summary_label"],
        layer3["coverage"]["summary_detail"],
        layer3["coverage"]["summary_tone"],
        layer3["coverage"]["rows"],
    )

    st.caption("Advanced transparency is still available below if you want the raw extraction and scoring detail.")
    with st.expander("Advanced View · Source Text", expanded=False):
        st.markdown("**Extracted job description**")
        st.write(result["details"]["job_text"] or "No job text available.")
        st.markdown("**Parsed resume text**")
        st.write(result["details"]["resume_text"] or "No resume text available.")
    with st.expander("Advanced View · Scoring & Risk", expanded=False):
        st.markdown("**Scoring breakdown**")
        st.json(result["details"]["score_breakdown"])
        st.markdown("**Risk flags**")
        st.json(result["details"]["risk_flags"])
    with st.expander("Advanced View · Raw Analysis Data", expanded=False):
        st.code(json.dumps(result["details"]["raw_data"], indent=2), language="json")


def render_job_page() -> None:
    init_job_state()
    use_llm = render_job_sidebar()
    render_hero(
        "Career Track",
        "Should You Apply To This Role?",
        "Evaluate whether a company opportunity is worth pursuing, why the recommendation was made, and what to tighten before you spend application time.",
    )

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### Candidate + Job Input")
            with st.form("career-decision-form", clear_on_submit=False):
                st.text_input("Job URL", key="job_url", placeholder="https://company.com/careers/graduate-analyst")
                uploaded_resume = st.file_uploader("Upload PDF resume", type=["pdf"], key="career_resume")

                with st.expander("Optional fallback fields", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Company name", key="company_name", placeholder="Northstar Analytics")
                    with col2:
                        st.text_input("Job title", key="job_title", placeholder="Graduate Data Analyst")
                    st.text_area(
                        "Job description text",
                        key="job_description",
                        height=220,
                        placeholder="Paste the full job description here. If the URL scrape fails, this text becomes the fallback source.",
                    )
                    st.checkbox(
                        "Use built-in demo resume when no PDF is uploaded",
                        key="use_demo_resume",
                        help="Keeps the demo fully runnable even if you do not upload a resume yet.",
                    )

                analyze_clicked = st.form_submit_button("Analyze Job Opportunity", use_container_width=True, type="primary")

    with right:
        with st.container(border=True):
            st.markdown("### What the career engine returns")
            st.markdown(
                "\n".join(
                    [
                        "- A 0 to 100 fit score with a transparent breakdown",
                        "- A company and posting risk check",
                        "- A clear recommendation: Apply, Consider, or Skip",
                        "- Strengths, gaps, reality checks, and next steps",
                    ]
                )
            )
            mode_label = "Optional LLM mode available" if use_llm else "Deterministic mode active"
            st.markdown(f'<div class="mode-pill">{escape(mode_label)}</div>', unsafe_allow_html=True)
            st.caption(
                "This track keeps the existing decision-engine workflow: fast recommendation first, then layered explanation and action support."
            )

    if analyze_clicked:
        with st.spinner("Running fit score, risk checks, and decision logic..."):
            try:
                st.session_state["career_analysis_result"] = run_job_analysis(
                    job_url=st.session_state["job_url"],
                    job_description=st.session_state["job_description"],
                    company_name=st.session_state["company_name"],
                    job_title=st.session_state["job_title"],
                    uploaded_resume=uploaded_resume,
                    use_demo_resume=st.session_state["use_demo_resume"],
                    use_llm=use_llm,
                )
                st.session_state["career_analysis_error"] = ""
            except Exception as exc:
                st.session_state["career_analysis_result"] = None
                st.session_state["career_analysis_error"] = str(exc)

    if st.session_state.get("career_analysis_error"):
        st.error(st.session_state["career_analysis_error"])
    if st.session_state.get("career_analysis_result"):
        render_job_results(st.session_state["career_analysis_result"])
