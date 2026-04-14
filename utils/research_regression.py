from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import utils.professor_search as professor_search
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
from utils.helpers import clean_text
from utils.outreach import generate_outreach_package
from utils.parsing import parse_resume_text


FIXTURE_DIR = Path(__file__).resolve().parent.parent / "tests" / "fixtures" / "research_pages"


QUANTUM_RESUME_TEXT = """
Alex Zhang
Hong Kong SAR | alex.zhang@email.com

EDUCATION
BSc Physics, Hong Kong University of Science and Technology
Relevant coursework: Quantum Mechanics, Condensed Matter Physics, Statistical Physics, Computational Physics

RESEARCH
Undergraduate Quantum Materials Project
- Studied quantum transport and topological materials using Python-based numerical analysis
- Reviewed recent literature on topological superconductors and mesoscopic transport
- Presented findings in a departmental research seminar

EXPERIENCE
Physics Research Intern
- Supported a condensed matter group with data analysis for low-temperature measurement results
- Helped organize plots and short written summaries for weekly lab meetings

SKILLS
Python, numerical simulation, data analysis, scientific writing, literature review
"""


@dataclass(frozen=True)
class ResearchRegressionCase:
    case_id: str
    label: str
    url: str
    fixture_file: str
    interests_text: str
    resume_text: str
    academic_stage: str
    opportunity_type: str
    funding_required: bool
    preferred_methods: list[str]
    existing_skills: str
    target_region: str = ""
    expected_page_type: str = ""
    expected_language: str = ""
    expected_selected_name: str = ""
    expected_selected_email: str = ""
    require_selected_email: bool = False
    expected_candidate_names: list[str] = field(default_factory=list)
    forbidden_names: list[str] = field(default_factory=list)
    expect_multi_profile: bool = False


def _fixture_text(filename: str) -> str:
    return (FIXTURE_DIR / filename).read_text(encoding="utf-8")


def get_research_regression_cases() -> list[ResearchRegressionCase]:
    return [
        ResearchRegressionCase(
            case_id="hkust_multi_profile",
            label="HKUST research staff directory",
            url="https://ccqs.hkust.edu.hk/people/research-staff-members",
            fixture_file="hkust_research_staff_members.html",
            interests_text="quantum transport, topological superconductors, condensed matter physics, quantum materials",
            resume_text=QUANTUM_RESUME_TEXT,
            academic_stage="Undergraduate",
            opportunity_type="Summer research",
            funding_required=False,
            preferred_methods=["Theory", "Computational"],
            existing_skills="Python, numerical simulation, scientific computing, condensed matter physics",
            target_region="Hong Kong",
            expected_page_type="directory_page",
            expected_language="English",
            expected_candidate_names=["Peng CHEN", "Shuo-Hui LI", "Jinfeng ZENG"],
            require_selected_email=True,
            forbidden_names=["Physics Tel", "Quantum Optics", "Research Staff Members", "Research Page"],
            expect_multi_profile=True,
        ),
        ResearchRegressionCase(
            case_id="sziqa_single_profile",
            label="SZIQA Chinese single researcher page",
            url="https://sziqa.ac.cn/category/1044/detail/4952",
            fixture_file="sziqa_wangshuo.html",
            interests_text="量子输运、拓扑超导、量子物态",
            resume_text=QUANTUM_RESUME_TEXT,
            academic_stage="Undergraduate",
            opportunity_type="RA / outreach",
            funding_required=False,
            preferred_methods=["Theory", "Computational"],
            existing_skills="Python, numerical simulation, condensed matter physics",
            target_region="China",
            expected_page_type="other",
            expected_language="Chinese",
            expected_selected_name="王硕",
            expected_selected_email="wangshuo@iqasz.cn",
            require_selected_email=True,
            expected_candidate_names=["王硕"],
            forbidden_names=["Research Page", "研究页面", "科研人员", "研究方向"],
            expect_multi_profile=False,
        ),
        ResearchRegressionCase(
            case_id="english_single_profile",
            label="Single-person English faculty page",
            url=SAMPLE_RESEARCH_TARGET_URL,
            fixture_file="english_single_faculty_profile.html",
            interests_text=SAMPLE_RESEARCH_INTERESTS,
            resume_text=SAMPLE_RESUME_TEXT,
            academic_stage=SAMPLE_RESEARCH_STAGE,
            opportunity_type=SAMPLE_RESEARCH_OPPORTUNITY_TYPE,
            funding_required=SAMPLE_RESEARCH_FUNDING_REQUIRED,
            preferred_methods=SAMPLE_RESEARCH_METHODS,
            existing_skills=SAMPLE_RESEARCH_SKILLS,
            target_region=SAMPLE_RESEARCH_REGION,
            expected_page_type="faculty_profile",
            expected_language="English",
            expected_selected_name="Susan Atherly",
            expected_selected_email="satherly@stanford.edu",
            require_selected_email=True,
            expected_candidate_names=["Susan Atherly"],
            forbidden_names=["Research Page", "Faculty", "People"],
            expect_multi_profile=False,
        ),
        ResearchRegressionCase(
            case_id="hkust_single_profile_email_binding",
            label="Single-person faculty page with same-profile visible email",
            url="https://physics.hkust.edu.hk/people/philip-yang",
            fixture_file="hkust_single_faculty_profile.html",
            interests_text="quantum materials, low-dimensional systems, topological transport, condensed matter theory",
            resume_text=QUANTUM_RESUME_TEXT,
            academic_stage="Undergraduate",
            opportunity_type="Summer research",
            funding_required=False,
            preferred_methods=["Theory", "Computational"],
            existing_skills="Python, numerical simulation, condensed matter physics",
            target_region="Hong Kong",
            expected_page_type="faculty_profile",
            expected_language="English",
            expected_selected_name="Philip H. Yang",
            expected_selected_email="phyang@ust.hk",
            require_selected_email=True,
            expected_candidate_names=["Philip H. Yang"],
            forbidden_names=["Research Page", "Faculty Directory", "People"],
            expect_multi_profile=False,
        ),
    ]


@contextmanager
def _patched_fixture_fetch(case: ResearchRegressionCase):
    fixture_map = {clean_text(case.url).rstrip("/"): _fixture_text(case.fixture_file)}
    original_fetch = professor_search.fetch_page_best_effort
    original_search = professor_search.search_duckduckgo_html

    def fake_fetch(url: str) -> tuple[str, str]:
        normalized = clean_text(url).rstrip("/")
        if normalized in fixture_map:
            return fixture_map[normalized], ""
        return "", f"No fixture registered for {url}"

    def fake_search(_query: str, max_results: int = 6) -> list[dict[str, str]]:
        return []

    professor_search.fetch_page_best_effort = fake_fetch
    professor_search.search_duckduckgo_html = fake_search
    try:
        yield
    finally:
        professor_search.fetch_page_best_effort = original_fetch
        professor_search.search_duckduckgo_html = original_search


def _contains_generic_target_label(name: str) -> bool:
    lowered = clean_text(name).lower()
    return lowered in {
        "",
        "research page",
        "official research page",
        "research staff members",
        "people",
        "faculty",
        "staff",
        "team",
        "members",
        "research page",
    }


def _surname_or_name(name: str) -> str:
    cleaned = clean_text(name)
    if any("\u4e00" <= char <= "\u9fff" for char in cleaned):
        return cleaned
    parts = cleaned.split()
    return parts[-1] if parts else cleaned


def _make_assertion(name: str, passed: bool, detail: str) -> dict[str, Any]:
    return {"name": name, "passed": bool(passed), "detail": detail}


def run_research_regression_case(case: ResearchRegressionCase) -> dict[str, Any]:
    resume_result = parse_resume_text(case.resume_text)
    resume_result["success"] = True

    with _patched_fixture_fetch(case):
        result = professor_search.analyze_research_target(
            target_url=case.url,
            resume_result=resume_result,
            interests_text=case.interests_text,
            target_region=case.target_region,
            academic_stage=case.academic_stage,
            opportunity_type=case.opportunity_type,
            funding_required=case.funding_required,
            preferred_methods=case.preferred_methods,
            existing_skills=case.existing_skills,
        )

    selected = result.get("target") or {}
    parser_report = result.get("parser_report", {})
    package = generate_outreach_package(selected, result.get("candidate_profile", {})) if selected else {}
    candidate_names = [candidate.get("name", "") for candidate in result.get("shortlist", [])]
    candidate_emails = [candidate.get("official_email", "") for candidate in result.get("shortlist", []) if candidate.get("official_email")]
    selected_name = clean_text(selected.get("name", ""))
    greeting = clean_text(package.get("greeting", ""))
    expected_salutation = _surname_or_name(selected_name)

    assertions = [
        _make_assertion(
            "selected_target_is_person_level",
            bool(selected_name) and not _contains_generic_target_label(selected_name),
            f"Selected target: {selected_name or 'None'}",
        ),
        _make_assertion(
            "selected_candidate_id_present",
            bool(result.get("selected_candidate_id")),
            f"selected_candidate_id={result.get('selected_candidate_id', '')}",
        ),
        _make_assertion(
            "selected_binding_valid",
            bool(parser_report.get("candidate_binding_valid", True)),
            f"binding_valid={parser_report.get('candidate_binding_valid', True)}",
        ),
        _make_assertion(
            "greeting_matches_selected_candidate",
            not greeting or expected_salutation in greeting or selected_name in greeting,
            f"greeting={greeting or 'None'} | selected={selected_name or 'None'}",
        ),
        _make_assertion(
            "email_action_uses_selected_candidate_email",
            package.get("recipient_email", "") == selected.get("official_email", ""),
            f"package_email={package.get('recipient_email', '') or 'None'} | selected_email={selected.get('official_email', '') or 'None'}",
        ),
        _make_assertion(
            "official_email_status_matches_selection",
            bool(parser_report.get("official_email_found")) == bool(clean_text(selected.get("official_email", ""))),
            f"official_email_found={parser_report.get('official_email_found')} | selected_email={selected.get('official_email', '') or 'None'}",
        ),
        _make_assertion(
            "email_not_missed_when_visible",
            "email_found_but_not_attributed" not in parser_report.get("failure_categories", []) + parser_report.get("warning_categories", []),
            f"categories={parser_report.get('failure_categories', []) + parser_report.get('warning_categories', [])}",
        ),
    ]

    for forbidden in case.forbidden_names:
        assertions.append(
            _make_assertion(
                f"forbidden_name_absent::{forbidden}",
                forbidden not in candidate_names and selected_name != forbidden,
                f"candidates={candidate_names}",
            )
        )

    if case.expect_multi_profile:
        assertions.append(
            _make_assertion(
                "multi_profile_detected",
                bool(result.get("multi_profile_detected")) and len(result.get("shortlist", [])) >= 2,
                f"multi={result.get('multi_profile_detected')} | shortlist={len(result.get('shortlist', []))}",
            )
        )

    if case.expected_page_type:
        assertions.append(
            _make_assertion(
                "expected_page_type",
                parser_report.get("page_type") == case.expected_page_type,
                f"page_type={parser_report.get('page_type', '')}",
            )
        )
    if case.expected_language:
        assertions.append(
            _make_assertion(
                "expected_page_language",
                parser_report.get("page_language") == case.expected_language,
                f"page_language={parser_report.get('page_language', '')}",
            )
        )
    if case.expected_selected_name:
        assertions.append(
            _make_assertion(
                "expected_selected_name",
                selected_name == case.expected_selected_name,
                f"selected_name={selected_name or 'None'}",
            )
        )
    if case.expected_selected_email:
        assertions.append(
            _make_assertion(
                "expected_selected_email",
                clean_text(selected.get("official_email", "")) == case.expected_selected_email,
                f"selected_email={selected.get('official_email', '') or 'None'}",
            )
        )
    elif case.require_selected_email:
        assertions.append(
            _make_assertion(
                "selected_email_present",
                bool(clean_text(selected.get("official_email", ""))),
                f"selected_email={selected.get('official_email', '') or 'None'}",
            )
        )
    if case.expected_candidate_names:
        for expected_name in case.expected_candidate_names:
            assertions.append(
                _make_assertion(
                    f"candidate_present::{expected_name}",
                    expected_name in candidate_names,
                    f"candidate_names={candidate_names}",
                )
            )

    passed = all(assertion["passed"] for assertion in assertions)
    return {
        "case_id": case.case_id,
        "label": case.label,
        "passed": passed,
        "url": case.url,
        "parser_report": parser_report,
        "candidate_names": candidate_names,
        "candidate_emails": candidate_emails,
        "selected_name": selected_name,
        "selected_email": clean_text(selected.get("official_email", "")),
        "selected_title": clean_text(selected.get("role_title", "")),
        "selected_candidate_id": result.get("selected_candidate_id", ""),
        "assertions": assertions,
        "result": result,
    }


def run_all_research_regressions(case_ids: list[str] | None = None) -> list[dict[str, Any]]:
    selected_ids = set(case_ids or [])
    results: list[dict[str, Any]] = []
    for case in get_research_regression_cases():
        if selected_ids and case.case_id not in selected_ids:
            continue
        results.append(run_research_regression_case(case))
    return results
