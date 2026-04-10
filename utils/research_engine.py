from __future__ import annotations

from typing import Any
from urllib.parse import quote

import streamlit as st

from sample_data import (
    SAMPLE_RESEARCH_FUNDING_REQUIRED,
    SAMPLE_RESEARCH_INTERESTS,
    SAMPLE_RESEARCH_METHODS,
    SAMPLE_RESEARCH_OPPORTUNITY_TYPE,
    SAMPLE_RESEARCH_REGION,
    SAMPLE_RESEARCH_SKILLS,
    SAMPLE_RESEARCH_STAGE,
    SAMPLE_RESEARCH_TARGET_URL,
    SAMPLE_RESUME_TEXT,
)
from utils.debug import debug_mode_source, is_debug_mode
from utils.helpers import clean_text
from utils.outreach import generate_outreach_package
from utils.parsing import parse_resume_pdf, parse_resume_text
from utils.professor_search import analyze_research_target
from utils.ui import (
    escape,
    render_coverage_section,
    render_decision_banner,
    render_hero,
    render_list_section,
    render_metric_card,
    render_outreach_package,
    render_pills,
    render_shortlist_card,
    render_text_section,
)


RESEARCH_STATE_DEFAULTS = {
    "research_target_url": "",
    "research_interests": "",
    "research_target_region": "",
    "research_stage": "Undergraduate",
    "research_opportunity_type": "Summer research",
    "research_funding_required": False,
    "research_existing_skills": "",
    "research_method_theory": False,
    "research_method_empirical": True,
    "research_method_experimental": False,
    "research_method_computational": True,
    "research_method_interdisciplinary": False,
    "research_use_demo_resume": False,
    "research_analysis_result": None,
    "research_analysis_error": "",
    "research_selected_candidate_id": "",
}


def init_research_state() -> None:
    for key, value in RESEARCH_STATE_DEFAULTS.items():
        st.session_state.setdefault(key, value)


def load_research_demo_inputs() -> None:
    st.session_state["research_target_url"] = SAMPLE_RESEARCH_TARGET_URL
    st.session_state["research_interests"] = SAMPLE_RESEARCH_INTERESTS
    st.session_state["research_target_region"] = SAMPLE_RESEARCH_REGION
    st.session_state["research_stage"] = SAMPLE_RESEARCH_STAGE
    st.session_state["research_opportunity_type"] = SAMPLE_RESEARCH_OPPORTUNITY_TYPE
    st.session_state["research_funding_required"] = SAMPLE_RESEARCH_FUNDING_REQUIRED
    st.session_state["research_existing_skills"] = SAMPLE_RESEARCH_SKILLS
    st.session_state["research_method_theory"] = "Theory" in SAMPLE_RESEARCH_METHODS
    st.session_state["research_method_empirical"] = "Empirical" in SAMPLE_RESEARCH_METHODS
    st.session_state["research_method_experimental"] = "Experimental" in SAMPLE_RESEARCH_METHODS
    st.session_state["research_method_computational"] = "Computational" in SAMPLE_RESEARCH_METHODS
    st.session_state["research_method_interdisciplinary"] = "Interdisciplinary" in SAMPLE_RESEARCH_METHODS
    st.session_state["research_use_demo_resume"] = True
    st.session_state["research_analysis_result"] = None
    st.session_state["research_analysis_error"] = ""
    st.session_state["research_selected_candidate_id"] = ""


def _selected_methods_from_state() -> list[str]:
    methods = []
    if st.session_state.get("research_method_theory"):
        methods.append("Theory")
    if st.session_state.get("research_method_empirical"):
        methods.append("Empirical")
    if st.session_state.get("research_method_experimental"):
        methods.append("Experimental")
    if st.session_state.get("research_method_computational"):
        methods.append("Computational")
    if st.session_state.get("research_method_interdisciplinary"):
        methods.append("Interdisciplinary")
    return methods


def render_research_sidebar() -> None:
    st.sidebar.markdown("## Research Track")
    st.sidebar.markdown(
        "\n".join(
            [
                "1. Parse a CV and extract research-relevant signals.",
                "2. Parse the professor, lab, or research-group URL you provide.",
                "3. Decide whether that target is worth contacting and generate a grounded outreach package.",
            ]
        )
    )
    st.sidebar.markdown("---")
    if st.sidebar.button("Load Demo Research Inputs", use_container_width=True):
        load_research_demo_inputs()
    st.sidebar.caption("This track evaluates the specific research URL you provide and keeps outreach grounded in parsed source evidence.")
    if is_debug_mode(st.session_state):
        st.sidebar.caption(f"Developer debug mode is enabled via {debug_mode_source(st.session_state)}.")


def run_research_analysis(
    *,
    target_url: str,
    uploaded_resume: Any,
    use_demo_resume: bool,
    interests_text: str,
    target_region: str,
    academic_stage: str,
    opportunity_type: str,
    funding_required: bool,
    preferred_methods: list[str],
    existing_skills: str,
) -> dict[str, Any]:
    normalized_target_url = clean_text(target_url)
    if not normalized_target_url:
        raise ValueError("Please provide a professor, lab, faculty, or research-group URL to evaluate.")

    interests = interests_text.strip()

    resume_source = "No resume provided"
    resume_result: dict[str, Any] | None = None
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
            raise ValueError(resume_result.get("error") or "The uploaded CV PDF could not be parsed. Please try another PDF or use the demo resume.")
    elif use_demo_resume:
        resume_result = parse_resume_text(SAMPLE_RESUME_TEXT)
        resume_result["success"] = True
        resume_result["fallback_used"] = True
        resume_source = "Built-in demo resume"
    else:
        raise ValueError("Upload a CV PDF so the research track can judge fit honestly, or use the built-in demo resume for testing.")

    analysis_result = analyze_research_target(
        target_url=normalized_target_url,
        resume_result=resume_result,
        interests_text=interests,
        target_region=target_region,
        academic_stage=academic_stage,
        opportunity_type=opportunity_type,
        funding_required=funding_required,
        preferred_methods=preferred_methods,
        existing_skills=existing_skills,
    )

    return {
        "analysis_mode": "Target URL evaluation",
        "resume_source": resume_source,
        "resume_result": resume_result,
        "target_url": analysis_result["target_url"],
        "candidate_profile": analysis_result["candidate_profile"],
        "queries": analysis_result.get("queries", []),
        "search_result_count": analysis_result.get("search_result_count", 0),
        "trusted_result_count": analysis_result.get("trusted_result_count", 0),
        "official_result_count": analysis_result.get("official_result_count", 0),
        "source_page_parsed": analysis_result.get("source_page_parsed", False),
        "source_page_word_count": analysis_result.get("source_page_word_count", 0),
        "source_credibility_label": analysis_result.get("source_credibility_label", "Limited"),
        "source_credibility_detail": analysis_result.get("source_credibility_detail", ""),
        "related_pages_checked": analysis_result.get("related_pages_checked", 0),
        "related_pages_used": analysis_result.get("related_pages_used", []),
        "faculty_page_count": analysis_result.get("faculty_page_count", 0),
        "lab_page_count": analysis_result.get("lab_page_count", 0),
        "center_page_count": analysis_result.get("center_page_count", 0),
        "department_page_count": analysis_result.get("department_page_count", 0),
        "directory_page_count": analysis_result.get("directory_page_count", 0),
        "opportunity_page_count": analysis_result.get("opportunity_page_count", 0),
        "project_page_count": analysis_result.get("project_page_count", 0),
        "publication_page_count": analysis_result.get("publication_page_count", 0),
        "source_type_counts": analysis_result.get("source_type_counts", {}),
        "candidate_type_counts": analysis_result.get("candidate_type_counts", {}),
        "parsed_candidate_count": analysis_result.get("parsed_candidate_count", 0),
        "extracted_candidate_count": analysis_result.get("extracted_candidate_count", 0),
        "official_email_count": analysis_result.get("official_email_count", 0),
        "recent_topic_profile_count": analysis_result.get("recent_topic_profile_count", 0),
        "shortlist": analysis_result.get("shortlist", []),
        "target": analysis_result.get("target"),
        "selected_candidate_id": analysis_result.get("selected_candidate_id", ""),
        "multi_profile_detected": analysis_result.get("multi_profile_detected", False),
        "errors": analysis_result.get("errors", []),
        "parser_report": analysis_result.get("parser_report", {}),
        "details": {
            "resume_text": resume_result.get("text", ""),
            "resume_sections": resume_result.get("sections", {}),
            "raw_data": analysis_result,
        },
    }


def _preview_text(text: str, fallback: str, limit: int = 120) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return fallback
    first_line = next((line.strip() for line in cleaned.splitlines() if line.strip()), cleaned)
    if len(first_line) <= limit:
        return first_line
    return f"{first_line[: limit - 1].rstrip()}..."


def _build_research_diagnostics(result: dict[str, Any]) -> dict[str, Any]:
    resume_result = result["resume_result"]
    profile = result["candidate_profile"]
    sections = resume_result.get("sections", {})
    word_count = len((resume_result.get("text") or "").split())
    keyword_list = profile.get("interest_keywords") or profile.get("topic_keywords", [])
    skills = profile.get("tools", [])
    research_signals = profile.get("research_exposure", [])
    education_preview = _preview_text(sections.get("education", ""), "No dedicated education section was extracted.")
    used_demo = result["resume_source"] in {"Demo resume fallback", "Built-in demo resume"}
    thin_extraction = resume_result.get("success") and word_count < 90

    if result["resume_source"] == "Demo resume fallback":
        parse_value = "Fallback"
        parse_status = "Uploaded CV parsing failed, so the demo resume fallback was used."
    elif used_demo:
        parse_value = "Demo"
        parse_status = "The current run used the built-in demo resume."
    elif not resume_result.get("success"):
        parse_value = "Failed"
        parse_status = "CV parsing failed."
    elif thin_extraction:
        parse_value = "Thin"
        parse_status = "CV parsed, but the extracted text is thin."
    else:
        parse_value = "Parsed"
        parse_status = "CV parsed successfully."

    parse_subtext = (
        f"{resume_result.get('page_count', 0)} pages parsed · {len(keyword_list)} research keywords"
        if resume_result.get("page_count")
        else f"{len(keyword_list)} research keywords extracted"
    )
    parse_items = [
        f"Resume source used: {result['resume_source']}.",
        f"Pages parsed: {resume_result.get('page_count', 0)}.",
        f"Resume text extracted: {word_count} words.",
        f"Research-relevant keywords extracted: {len(keyword_list)}.",
        f"Skills extracted: {', '.join(skills[:6]) if skills else 'No clear skill tags were extracted.'}",
        f"Education extracted: {education_preview}",
        f"Research-related signals extracted: {', '.join(research_signals) if research_signals else 'No clear research-related signals were detected.'}",
    ]
    if resume_result.get("error"):
        parse_items.append(f"Parsing note: {resume_result['error']}")
    if thin_extraction:
        parse_items.append("The extracted text is thin, so research-target matching may be weak until the CV yields more usable text.")

    parsed_candidate_count = result.get("parsed_candidate_count", len(result.get("shortlist", [])))
    official_email_count = result.get("official_email_count", 0)
    recent_topic_profile_count = result.get("recent_topic_profile_count", 0)
    extracted_candidate_count = result.get("extracted_candidate_count", parsed_candidate_count)
    multi_profile_detected = result.get("multi_profile_detected", False)
    source_page_parsed = result.get("source_page_parsed", False)
    source_page_word_count = result.get("source_page_word_count", 0)
    source_credibility_label = result.get("source_credibility_label", "Limited")
    source_credibility_detail = result.get("source_credibility_detail", "")
    related_pages_checked = result.get("related_pages_checked", 0)
    related_pages_used = result.get("related_pages_used", [])
    selected_target = result.get("target") or (result.get("shortlist") or [{}])[0]
    extracted_topics = selected_target.get("research_tags", [])[:6]
    extracted_outputs = selected_target.get("publications", [])[:3] + selected_target.get("project_signals", [])[:2]

    source_mix_items = [
        f"Credibility {source_credibility_label}",
        f"Candidates {parsed_candidate_count}",
        f"Topics {len(extracted_topics)}",
        f"Outputs {len(extracted_outputs)}",
    ]
    if related_pages_checked:
        source_mix_items.append(f"Related pages checked {related_pages_checked}")
    if official_email_count:
        source_mix_items.append("Official email found")

    if source_page_parsed and parsed_candidate_count:
        if multi_profile_detected:
            search_value = "Ranked"
            search_status = f"The provided page exposed multiple plausible people, and {parsed_candidate_count} candidates were scored and ranked."
        else:
            search_value = "Ready"
            search_status = "The provided research URL was parsed successfully and turned into a scored outreach target."
    elif source_page_parsed:
        search_value = "Limited"
        search_status = "The URL was parsed, but the evidence was too thin to support a strong decision."
    else:
        search_value = "Weak"
        search_status = "The provided URL did not yield enough trustworthy page content to evaluate confidently."

    search_items = [
        f"Source page parsed successfully: {'Yes' if source_page_parsed else 'No'}.",
        f"Multiple researcher profiles detected: {'Yes' if multi_profile_detected else 'No'}.",
        f"Source page word count: {source_page_word_count}.",
        f"Candidates extracted from the source page: {extracted_candidate_count}.",
        f"Candidates kept in the ranked shortlist: {parsed_candidate_count}.",
        f"Source credibility: {source_credibility_label}.",
        f"Official email found: {'Yes' if official_email_count else 'No'}.",
        f"Related pages checked for enrichment: {related_pages_checked}.",
        f"Research topics extracted from the source: {len(extracted_topics)}.",
        (
            f"Recent outputs found: {len(extracted_outputs)}."
            if extracted_outputs
            else "Recent outputs found: limited."
        ),
        (
            f"Related pages used for enrichment: {len(related_pages_used)}."
            if related_pages_used
            else "No related same-domain pages materially improved the target profile."
        ),
    ]

    limitations: list[str] = []
    next_actions: list[str] = []
    if thin_extraction or not resume_result.get("success"):
        limitations.append("CV extraction is weak, so the engine has limited student evidence to match against research targets.")
        next_actions.append("Try a text-based PDF or a CV with clearer section headings so the parser can extract more usable text.")
    if interests_text := clean_text(profile.get("interests_text", "")):
        if len(keyword_list) < 3 and len(interests_text.split()) < 4:
            limitations.append("The optional outreach-goal text is still broad, so the fit explanation may be less specific than it could be.")
            next_actions.append("Add 2 to 4 concrete topics, methods, or goals so the outreach package can be more targeted.")
    if not source_page_parsed:
        limitations.append("The provided URL could not be parsed into a trustworthy source profile.")
        next_actions.append("Check that the URL points to a readable professor, lab, faculty, or research-group page.")
    elif parsed_candidate_count == 0:
        if multi_profile_detected or extracted_candidate_count:
            limitations.append("The source page exposed people or contacts, but the extracted researcher evidence stayed too thin to rank them confidently.")
            next_actions.append("Try an individual faculty or profile link from the page so the engine can gather more direct role, research, and contact detail.")
        else:
            limitations.append("The source page was parsed, but it did not contain enough profile evidence to support a strong outreach decision.")
            next_actions.append("Try a more specific faculty or lab page instead of a broad department landing page.")
    if source_page_parsed and source_credibility_label == "Limited":
        limitations.append("Source credibility is limited, so official context and contact confidence are weaker than ideal.")
    if source_page_parsed and not extracted_topics:
        limitations.append("The source page did not expose clear research topics, which weakens topical matching.")
    if parsed_candidate_count > 0 and official_email_count == 0:
        limitations.append("Contact information is limited because no official email address was found on the source or related trustworthy pages.")
    if parsed_candidate_count > 0 and recent_topic_profile_count == 0:
        limitations.append("Recent topic evidence is limited because papers, projects, or output signals were thin on the available pages.")
    for error in result.get("errors", []):
        if error not in limitations:
            limitations.append(error)

    return {
        "parse_value": parse_value,
        "parse_status": parse_status,
        "parse_subtext": parse_subtext,
        "parse_items": parse_items,
        "keyword_list": keyword_list[:8],
        "skills": skills[:8],
        "search_value": search_value,
        "search_status": search_status,
        "search_subtext": (
            f"{source_credibility_label} source credibility · {extracted_candidate_count} candidates extracted"
            if multi_profile_detected
            else f"{source_credibility_label} source credibility · {related_pages_checked} related pages checked"
        ),
        "search_items": search_items,
        "queries": result.get("queries", []),
        "source_mix_items": source_mix_items,
        "source_page_parsed": source_page_parsed,
        "source_page_word_count": source_page_word_count,
        "source_credibility_label": source_credibility_label,
        "source_credibility_detail": source_credibility_detail,
        "related_pages_checked": related_pages_checked,
        "related_pages_used": related_pages_used,
        "trusted_result_count": int(source_page_parsed),
        "parsed_candidate_count": parsed_candidate_count,
        "extracted_candidate_count": extracted_candidate_count,
        "multi_profile_detected": multi_profile_detected,
        "official_email_count": official_email_count,
        "recent_topic_profile_count": recent_topic_profile_count,
        "limitations": limitations,
        "next_actions": next_actions,
    }


def render_research_status(result: dict[str, Any]) -> dict[str, Any]:
    diagnostics = _build_research_diagnostics(result)

    st.markdown("### Analysis Status")
    top_row = st.columns(3, gap="large")
    with top_row[0]:
        render_metric_card("CV Parse", diagnostics["parse_value"], diagnostics["parse_subtext"])
    with top_row[1]:
        render_metric_card("Source Page", "Parsed" if diagnostics["source_page_parsed"] else "Limited", diagnostics["search_subtext"])
    with top_row[2]:
        render_metric_card("Candidates", str(diagnostics["parsed_candidate_count"]), diagnostics["search_status"])

    bottom_row = st.columns(3, gap="large")
    with bottom_row[0]:
        render_metric_card(
            "Source Credibility",
            diagnostics["source_credibility_label"],
            diagnostics["source_credibility_detail"],
        )
    with bottom_row[1]:
        render_metric_card("Related Pages", str(diagnostics["related_pages_checked"]), "Same-domain pages checked for official enrichment and contact details.")
    with bottom_row[2]:
        render_metric_card("Official Emails", str(diagnostics["official_email_count"]), "Official contact addresses confirmed.")

    left, right = st.columns(2, gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### CV Parsing Summary")
            st.markdown(f"**{diagnostics['parse_status']}**")
            st.markdown("\n".join(f"- {item}" for item in diagnostics["parse_items"]))
            st.markdown("**Research keywords extracted**")
            if diagnostics["keyword_list"]:
                render_pills(diagnostics["keyword_list"])
            else:
                st.markdown("No strong research keywords were extracted.")
            st.markdown("**Skills extracted**")
            if diagnostics["skills"]:
                render_pills(diagnostics["skills"])
            else:
                st.markdown("No clear skills were extracted from the current CV evidence.")

    with right:
        with st.container(border=True):
            st.markdown("### Source Page Summary")
            st.markdown(f"**{diagnostics['search_status']}**")
            st.markdown("\n".join(f"- {item}" for item in diagnostics["search_items"]))
            st.markdown("**Source signals found**")
            render_pills(diagnostics["source_mix_items"])
            if diagnostics["related_pages_used"]:
                st.markdown("**Related pages used for enrichment**")
                st.markdown("\n".join(f"- {url}" for url in diagnostics["related_pages_used"]))

    if diagnostics["limitations"] or diagnostics["next_actions"]:
        with st.container(border=True):
            st.markdown("### What Limited The Results")
            if diagnostics["limitations"]:
                st.markdown("\n".join(f"- {item}" for item in diagnostics["limitations"]))
            if diagnostics["next_actions"]:
                st.markdown("**What to adjust next**")
                st.markdown("\n".join(f"- {item}" for item in diagnostics["next_actions"]))

    return diagnostics


def render_research_debug_report(result: dict[str, Any]) -> None:
    if not is_debug_mode(st.session_state):
        return

    parser_report = result.get("parser_report") or {}
    if not parser_report:
        return

    with st.expander("Developer Debug · Parser Report", expanded=False):
        st.caption(f"Debug mode enabled via {debug_mode_source(st.session_state)}")
        st.markdown("**Parser summary**")
        st.markdown(
            "\n".join(
                [
                    f"- Input URL: {parser_report.get('input_url', 'Unknown')}",
                    f"- Page language: {parser_report.get('page_language', 'Unknown')}",
                    f"- Page type: {parser_report.get('page_type', 'other')}",
                    f"- Multi-profile detected: {'Yes' if parser_report.get('multi_profile_detected') else 'No'}",
                    f"- Raw person blocks found: {parser_report.get('raw_person_block_count', 0)}",
                    f"- Visible text candidates found: {parser_report.get('visible_text_candidate_count', 0)}",
                    f"- Candidate objects built: {parser_report.get('candidate_objects_built_count', 0)}",
                    f"- Page-level fallback used: {'Yes' if parser_report.get('page_level_fallback_used') else 'No'}",
                    f"- Fallback path: {parser_report.get('fallback_path_used') or 'None'}",
                    f"- Selected candidate id: {parser_report.get('selected_candidate_id') or 'None'}",
                    f"- Selected candidate: {parser_report.get('selected_candidate_name') or 'None'}",
                    f"- Selected email: {parser_report.get('selected_candidate_email') or 'None'}",
                    f"- Selected title: {parser_report.get('selected_candidate_title') or 'None'}",
                    f"- Candidate binding valid: {'Yes' if parser_report.get('candidate_binding_valid', True) else 'No'}",
                ]
            )
        )
        if parser_report.get("candidate_names"):
            st.markdown("**Candidate names extracted**")
            st.markdown("\n".join(f"- {item}" for item in parser_report.get("candidate_names", [])))
        if parser_report.get("candidate_emails"):
            st.markdown("**Candidate emails extracted**")
            st.markdown("\n".join(f"- {item}" for item in parser_report.get("candidate_emails", [])))
        if parser_report.get("candidate_snapshots"):
            st.markdown("**Candidate snapshots**")
            for snapshot in parser_report.get("candidate_snapshots", []):
                st.markdown(
                    f"- `{snapshot.get('candidate_type', 'unknown')}` "
                    f"{snapshot.get('name', 'Unnamed')} | "
                    f"title={snapshot.get('title', 'None') or 'None'} | "
                    f"email={snapshot.get('email', 'None') or 'None'} | "
                    f"email_confidence={snapshot.get('email_confidence', 'missing') or 'missing'} | "
                    f"confidence={snapshot.get('extraction_confidence', 0)}"
                )
        if parser_report.get("failure_categories") or parser_report.get("warning_categories"):
            st.markdown("**Failure and warning categories**")
            categories = parser_report.get("failure_categories", []) + parser_report.get("warning_categories", [])
            st.markdown("\n".join(f"- {item}" for item in categories))
        if parser_report.get("events"):
            with st.expander("Developer Debug · Detailed Events", expanded=False):
                for event in parser_report.get("events", []):
                    st.markdown(f"- `{event.get('severity', 'info')}` `{event.get('category', 'uncategorized')}`: {event.get('detail', '')}")


def build_research_layer3(selected: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    profile = result["candidate_profile"]
    target_label = "professor" if selected.get("entity_type") == "Professor" else "research opportunity"
    topic_anchor = next((item for item in selected.get("recent_topics", []) if item), "") or next(
        (item for item in selected.get("research_tags", []) if item), "the target's current research"
    )
    why_intro = (
        f"{selected.get('recommendation', 'Insufficient evidence')} is being driven by {selected.get('why_match_topline', 'the available source evidence').rstrip('.')}. "
        f"The biggest watch-out is {selected.get('main_watchout', 'the evidence base is still limited').rstrip('.')}."
    )
    why_items = selected.get("why_match", [])[:3] + [
        "Time-use judgement: contact this target now only if the fit and feasibility together justify a tailored outreach note."
    ]

    improve_items = [
        f"Opening line: lead with your interest in {topic_anchor} so the reason for contacting this {target_label} feels specific from the first sentence.",
        f"CV emphasis: move the strongest evidence for {topic_anchor} closer to the top of the CV before sending.",
        "Proof of readiness: mention one concrete project, paper, dataset, or analysis task that shows you can contribute at a student level rather than just that you are interested.",
    ]
    if not selected.get("official_email"):
        improve_items.append("Channel check: do not guess an email address. Use the official faculty page, department contact route, or lab contact form only.")
    if profile.get("research_exposure") and "Research experience" not in profile["research_exposure"]:
        improve_items.append("Research framing: if your background is mostly coursework or projects, make that explicit instead of implying a formal lab role you have not had.")
    if selected.get("weaknesses"):
        improve_items.append(selected["weaknesses"][0])

    missing_items = [
        f"Missing research proof: the CV should clearly show at least one project, paper, thesis, or independent analysis that maps onto this {target_label}'s area.",
        f"Missing motivation proof: your outreach will be weaker if the email cannot point to one specific paper, project, or topic from this {target_label}'s official work.",
    ]
    if "Communication" not in profile.get("research_exposure", []):
        missing_items.append("Missing communication proof: there is limited evidence of writing, presenting, or explaining technical work to others.")
    if selected.get("weaknesses"):
        missing_items.append(selected["weaknesses"][0])

    coverage_rows = selected.get("source_coverage", [])
    success_rows = sum(1 for row in coverage_rows if row["tone"] == "success")
    if success_rows >= 5:
        coverage_label = "Strong coverage"
        coverage_tone = "strong"
        coverage_detail = "The recommendation is grounded in several official signals, including profile, publication, and CV evidence."
    elif success_rows >= 3:
        coverage_label = "Moderate coverage"
        coverage_tone = "moderate"
        coverage_detail = "There is enough official evidence to rank this target, but some contact or activity context is still limited."
    else:
        coverage_label = "Limited coverage"
        coverage_tone = "limited"
        coverage_detail = "This ranking is tentative because key official signals such as email, department page, or recent outputs are incomplete."

    return {
        "why": {"intro": why_intro, "items": why_items[:4]},
        "improve": {
            "intro": "These are the highest-value edits to make before you send a cold email.",
            "items": improve_items[:5],
        },
        "missing": {
            "intro": "These are the missing proof points most likely to weaken the outreach email.",
            "items": missing_items[:4],
        },
        "coverage": {
            "summary_label": coverage_label,
            "summary_tone": coverage_tone,
            "summary_detail": coverage_detail,
            "rows": coverage_rows,
        },
        "outreach_package": generate_outreach_package(selected, profile),
    }


def _research_badge_html(label: str) -> str:
    colors = {
        "Reach out now": ("#ecfdf5", "#166534", "#86efac"),
        "Reach out after tailoring": ("#eff6ff", "#1d4ed8", "#bfdbfe"),
        "Save for later": ("#fffbeb", "#92400e", "#fde68a"),
        "Low priority": ("#fff7ed", "#c2410c", "#fdba74"),
        "Low-priority contact": ("#fff7ed", "#c2410c", "#fdba74"),
        "Insufficient evidence": ("#fef2f2", "#991b1b", "#fecaca"),
    }
    bg, fg, border = colors.get(label, ("#f8fafc", "#334155", "#cbd5e1"))
    return f'<span class="rec-badge" style="background:{bg};color:{fg};border:1px solid {border};">{escape(label)}</span>'


def _build_mailto_link(email: str, subject: str, body: str) -> str:
    return f"mailto:{email}?subject={quote(subject)}&body={quote(body)}"


def render_email_actions(selected: dict[str, Any], package: dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown("### Email Draft Actions")
        subject_line = (package.get("subject_lines") or ["Research outreach"])[0]
        draft_body = package.get("email_draft", "")
        if selected.get("official_email"):
            st.link_button(
                "Open Email Draft",
                _build_mailto_link(selected["official_email"], subject_line, draft_body),
                use_container_width=True,
                type="primary",
            )
            st.caption(f'The mail app draft uses the first generated subject line: "{subject_line}"')
        else:
            st.info("Email not found from official source. Review the source page and copy the draft manually if you still want to reach out.")
            if selected.get("primary_source_url") or selected.get("official_profile_url"):
                st.link_button(
                    "View Source Page",
                    selected.get("primary_source_url") or selected.get("official_profile_url"),
                    use_container_width=True,
                )

        st.text_area(
            "Copyable email draft",
            value=draft_body,
            height=260,
            key=f"research_email_draft_{abs(hash((selected.get('name', ''), subject_line))) % 1_000_000}",
        )


def render_selected_match(selected: dict[str, Any], result: dict[str, Any]) -> None:
    layer3 = build_research_layer3(selected, result)
    target_label = selected.get("entity_type", "Research Match")
    why_title = "Why This Professor" if selected.get("entity_type") == "Professor" else "Why This Opportunity"
    render_pills(
        [
            f"Mode: {result['analysis_mode']}",
            f"Resume source: {result['resume_source']}",
            f"Source credibility: {result.get('source_credibility_label', 'Limited')}",
            f"Related pages checked: {result.get('related_pages_checked', 0)}",
        ]
    )
    render_decision_banner("Decision-first summary", selected.get("why_matched_summary", "The match summary is limited because the available evidence is thin."))

    with st.container(border=True):
        st.markdown("### Selected Match")
        st.markdown(f"**Name:** {selected.get('name', 'Unnamed research target')}")
        st.markdown(f"**Match type:** {target_label}")
        if selected.get("role_title") and selected.get("role_title") != "Role not clearly labeled on the source page":
            st.markdown(f"**Role / Title:** {selected['role_title']}")
        st.markdown(f"**University:** {selected.get('university', 'Institution not clearly identified')}")
        st.markdown(f"**Department / Lab:** {selected.get('department_or_lab', 'Research context not clearly identified')}")
        st.markdown(f"**Opportunity type:** {selected.get('opportunity_type', 'Research opportunity')}")
        st.markdown(f"**Confidence:** {selected.get('confidence_score', 0)}/100 · {selected.get('confidence_label', 'Low')}")
        if selected.get("lead_contact_name") and selected.get("lead_contact_name") != selected.get("name"):
            st.markdown(f"**Lead contact surfaced:** {selected['lead_contact_name']}")
        st.markdown(f"**Official email:** {selected.get('official_email') or 'Email not found from official sources'}")
        st.markdown(f"**Primary source page:** {selected.get('primary_source_url') or selected.get('official_profile_url') or 'Not found'}")
        if selected.get("department_page_url"):
            st.markdown(f"**Department / lab page:** {selected['department_page_url']}")
        if selected.get("opportunity_page_url"):
            st.markdown(f"**Related opportunity page:** {selected['opportunity_page_url']}")
        st.markdown(f"**Quick source summary:** {selected.get('quick_source_summary', 'Not summarized.')}")
        if selected.get("academic_background"):
            st.markdown(f"**Academic background found:** {selected['academic_background'][0]}")
        if selected.get("research_tags") or selected.get("discipline_tags"):
            render_pills(selected.get("research_tags", [])[:4] + selected.get("discipline_tags", [])[:3])

    st.markdown("### Layer 1 · Decision")
    metric_row_one = st.columns(2, gap="large")
    metric_row_two = st.columns(2, gap="large")
    with metric_row_one[0]:
        render_metric_card("1. Research Fit Score", f"{selected.get('research_fit_score', 0)}/100", "How well this target’s topics match your interests, methods, and CV signals.")
    with metric_row_one[1]:
        render_metric_card("2. Outreach Feasibility", f"{selected.get('outreach_feasibility_score', 0)}/100", "How realistic it is to contact this target now using official evidence and stage signals.")
    with metric_row_two[0]:
        render_metric_card("3. Confidence", f"{selected.get('confidence_score', 0)}/100", selected.get("confidence_note", "Confidence reflects how complete and trustworthy the evidence base is."))
    with metric_row_two[1]:
        render_metric_card("4. Recommendation", selected.get("recommendation", "Insufficient evidence"), selected.get("why_match_topline", "The available evidence is limited."), badge_html=_research_badge_html(selected.get("recommendation", "Insufficient evidence")))

    st.markdown("### Layer 2 · Explanation")
    render_text_section(5, "Why This Match", selected.get("why_matched_summary", "No match summary was generated."))
    render_list_section(6, "Alignment Signals", selected.get("why_match", []), "No alignment signals were generated.")
    render_list_section(7, "Match Risks", selected.get("weaknesses", []), "No major match risks were generated.")
    render_list_section(8, "Contact Feasibility", selected.get("contact_feasibility", []), "No contact feasibility notes were generated.")
    render_list_section(9, "Recent Topics & Outputs", selected.get("recent_topics", []) + selected.get("publications", []) + selected.get("project_signals", []), "No recent topics were generated.")

    st.markdown("### Layer 3 · Before You Reach Out")
    render_list_section(10, why_title, layer3["why"]["items"], "No rationale was generated.", intro=layer3["why"]["intro"])
    render_list_section(11, "How To Improve Before Emailing", layer3["improve"]["items"], "No improvement suggestions were generated.", intro=layer3["improve"]["intro"])
    render_list_section(12, "Missing Evidence", layer3["missing"]["items"], "No missing evidence notes were generated.", intro=layer3["missing"]["intro"])
    render_coverage_section(
        13,
        "Evidence & Source Coverage",
        layer3["coverage"]["summary_label"],
        layer3["coverage"]["summary_detail"],
        layer3["coverage"]["summary_tone"],
        layer3["coverage"]["rows"],
    )
    render_outreach_package(layer3["outreach_package"])
    render_email_actions(selected, layer3["outreach_package"])

    st.caption("Advanced transparency is still available below if you want the underlying source excerpts and parsed CV highlights.")
    with st.expander("Advanced View · Official Source Detail", expanded=False):
        st.markdown("**Provided research URL**")
        st.write(result.get("target_url", "No target URL recorded."))
        st.markdown("**Related pages checked**")
        st.write(result.get("related_pages_used") or "No related same-domain pages were used.")
        st.markdown("**Primary source excerpt**")
        st.write(selected.get("raw_text_excerpt", "No raw text excerpt available."))
        if selected.get("research_tags") or selected.get("recent_topics"):
            st.markdown("**Extracted research themes**")
            render_pills(selected.get("research_tags", [])[:6] + selected.get("recent_topics", [])[:4])
        outputs = selected.get("publications", [])[:3] + selected.get("project_signals", [])[:3]
        if outputs:
            st.markdown("**Recent outputs and project signals**")
            st.markdown("\n".join(f"- {item}" for item in outputs))
        else:
            st.markdown("Recent outputs were limited on the available sources.")
    with st.expander("Advanced View · Parsed CV Highlights", expanded=False):
        sections = result["details"].get("resume_sections", {})
        if sections.get("education"):
            st.markdown("**Education**")
            st.write(sections["education"])
        if sections.get("experience"):
            st.markdown("**Experience**")
            st.write(sections["experience"])
        if sections.get("projects"):
            st.markdown("**Projects**")
            st.write(sections["projects"])
        if sections.get("skills"):
            st.markdown("**Skills**")
            st.write(sections["skills"])
        if not any(sections.get(key) for key in ("education", "experience", "projects", "skills")):
            st.write(result["details"]["resume_text"] or "No resume text available.")


def render_research_page() -> None:
    init_research_state()
    render_research_sidebar()
    render_hero(
        "Research Track",
        "Is This Research Target Worth Contacting?",
        "Bring a professor, lab, faculty, or research-group URL plus your CV, then get a decision-first outreach evaluation grounded in parsed source evidence.",
    )

    left, right = st.columns([1.35, 1], gap="large")
    with left:
        with st.container(border=True):
            st.markdown("### Research Target + Student Input")
            with st.form("research-decision-form", clear_on_submit=False):
                st.text_input(
                    "Professor / Lab / Faculty / Research Group URL",
                    key="research_target_url",
                    placeholder="https://...",
                )
                uploaded_resume = st.file_uploader("Upload CV PDF", type=["pdf"], key="research_resume")
                st.text_area(
                    "Research interests / outreach goal (optional but recommended)",
                    key="research_interests",
                    height=130,
                    placeholder="Example: development economics and field experiments, machine learning for biology, summer research interest, pre-PhD outreach",
                )

                with st.expander("Optional filters", expanded=False):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.text_input("Target country / region", key="research_target_region", placeholder="United Kingdom")
                        st.selectbox("Academic stage", ["Undergraduate", "Master", "Pre-PhD", "Other"], key="research_stage")
                        st.selectbox(
                            "Opportunity type",
                            ["Summer research", "RA / outreach", "Long-term research", "PhD interest"],
                            key="research_opportunity_type",
                        )
                    with col2:
                        st.checkbox("Funding required", key="research_funding_required")
                        st.text_area("Existing research tools / skills", key="research_existing_skills", height=100, placeholder="Python, econometrics, lab methods, qualitative coding")
                        st.checkbox("Use built-in demo resume when no PDF is uploaded", key="research_use_demo_resume")
                    st.markdown("**Preferred methods**")
                    method_row_one = st.columns(3)
                    with method_row_one[0]:
                        st.checkbox("Theory", key="research_method_theory")
                    with method_row_one[1]:
                        st.checkbox("Empirical", key="research_method_empirical")
                    with method_row_one[2]:
                        st.checkbox("Experimental", key="research_method_experimental")
                    method_row_two = st.columns(2)
                    with method_row_two[0]:
                        st.checkbox("Computational", key="research_method_computational")
                    with method_row_two[1]:
                        st.checkbox("Interdisciplinary", key="research_method_interdisciplinary")

                analyze_clicked = st.form_submit_button("Analyze Research Fit", use_container_width=True, type="primary")

    with right:
        with st.container(border=True):
            st.markdown(
                """
                <div class="explain-panel">
                    <h3>What the research engine returns</h3>
                    <ul>
                        <li>A decision on whether the specific professor, lab, or research page is worth contacting</li>
                        <li>Research Fit, Outreach Feasibility, Recommendation, and Confidence from parsed source evidence</li>
                        <li>Visible CV parsing and source-page parsing transparency</li>
                        <li>Actionable guidance before you email</li>
                        <li>A grounded outreach package plus an email-app draft action when an official address is found</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.markdown('<div class="mode-pill">Decision engine for a provided research URL</div>', unsafe_allow_html=True)
            st.caption("No guessed emails, no invented publications, and no fabricated professor or lab claims.")

    if analyze_clicked:
        with st.spinner("Parsing the CV and evaluating the provided research target..."):
            try:
                st.session_state["research_analysis_result"] = run_research_analysis(
                    target_url=st.session_state["research_target_url"],
                    uploaded_resume=uploaded_resume,
                    use_demo_resume=st.session_state["research_use_demo_resume"],
                    interests_text=st.session_state["research_interests"],
                    target_region=st.session_state["research_target_region"],
                    academic_stage=st.session_state["research_stage"],
                    opportunity_type=st.session_state["research_opportunity_type"],
                    funding_required=st.session_state["research_funding_required"],
                    preferred_methods=_selected_methods_from_state(),
                    existing_skills=st.session_state["research_existing_skills"],
                )
                st.session_state["research_analysis_error"] = ""
                st.session_state["research_selected_candidate_id"] = ""
            except Exception as exc:
                st.session_state["research_analysis_result"] = None
                st.session_state["research_analysis_error"] = str(exc)

    if st.session_state.get("research_analysis_error"):
        st.error(st.session_state["research_analysis_error"])

    result = st.session_state.get("research_analysis_result")
    if not result:
        return

    if result.get("multi_profile_detected"):
        st.success("Research analysis completed. Multiple targets were found on the provided page, ranked, and prepared for comparison below.")
    else:
        st.success("Research analysis completed. Review the CV parse, source-page parse, and outreach recommendation below.")
    render_research_status(result)

    if result["errors"]:
        for error in result["errors"]:
            st.info(error)

    st.markdown("### Research Target")
    if not result["shortlist"] or not result.get("target"):
        st.warning("The engine parsed the inputs, but it could not build a strong enough research-target profile from the provided URL.")
        return

    shortlist = result.get("shortlist", [])
    selected = result.get("target") or shortlist[0]

    if result.get("multi_profile_detected"):
        st.caption("Multiple people were found on the provided page. The shortlist below is ranked from strongest match to weakest match, and you can inspect any candidate in detail.")
        for rank, candidate in enumerate(shortlist, start=1):
            render_shortlist_card(candidate, rank=rank)
        candidate_ids = [candidate.get("candidate_id") or str(rank) for rank, candidate in enumerate(shortlist, start=1)]
        shortlist_by_id = {candidate_ids[idx]: candidate for idx, candidate in enumerate(shortlist)}
        default_id = result.get("selected_candidate_id") or (result.get("target") or shortlist[0]).get("candidate_id") or candidate_ids[0]
        if st.session_state.get("research_selected_candidate_id") not in shortlist_by_id:
            st.session_state["research_selected_candidate_id"] = default_id
        selected_id = st.selectbox(
            "Inspect a ranked candidate",
            options=candidate_ids,
            format_func=lambda candidate_id: (
                f"#{candidate_ids.index(candidate_id) + 1} · "
                f"{shortlist_by_id[candidate_id].get('name', 'Unnamed target')} · "
                f"{shortlist_by_id[candidate_id].get('recommendation', 'Insufficient evidence')}"
            ),
            key="research_selected_candidate_id",
        )
        selected = shortlist_by_id[selected_id]
    else:
        st.caption("This card summarizes the single professor, lab, or research-group URL you provided and whether the evidence supports contacting now.")
        render_shortlist_card(selected, rank=1)

    render_selected_match(selected, result)
    render_research_debug_report(result)
