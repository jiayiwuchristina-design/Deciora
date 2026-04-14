from __future__ import annotations

import json
import os
from typing import Any

import requests


REQUIRED_KEYS = {
    "fit_score",
    "risk_level",
    "recommendation",
    "confidence",
    "strengths",
    "gaps",
    "job_reality",
    "company_signals",
    "next_steps",
}

RESEARCH_BLOCK_TYPES = {
    "person_profile",
    "research_area",
    "research_interest",
    "title_fragment",
    "page_title",
    "section_heading",
    "breadcrumb",
    "contact_label",
    "institution_label",
    "team_page_label",
    "unknown",
}


def _int_env(name: str, default: int) -> int:
    raw_value = os.getenv(name, "").strip()
    if not raw_value:
        return default
    try:
        return int(raw_value)
    except ValueError:
        return default


RESEARCH_STANDARD_MODEL = os.getenv("OPENAI_RESEARCH_MODEL", "gpt-5.4-mini")
RESEARCH_POLISH_MODEL = os.getenv("OPENAI_RESEARCH_POLISH_MODEL", "gpt-5.4")
JOB_ANALYSIS_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
DEFAULT_REQUEST_TIMEOUT_SECONDS = _int_env("OPENAI_LLM_TIMEOUT_SECONDS", 20)
RESEARCH_REQUEST_TIMEOUT_SECONDS = _int_env("OPENAI_RESEARCH_TIMEOUT_SECONDS", 18)
RESEARCH_POLISH_TIMEOUT_SECONDS = _int_env("OPENAI_RESEARCH_POLISH_TIMEOUT_SECONDS", 28)


def is_llm_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


def research_standard_model_name() -> str:
    return RESEARCH_STANDARD_MODEL


def research_polish_model_name() -> str:
    return RESEARCH_POLISH_MODEL


def _chat_endpoint(base_url: str) -> str:
    stripped = base_url.rstrip("/")
    if stripped.endswith("/chat/completions"):
        return stripped
    return f"{stripped}/chat/completions"


def _extract_json(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        content = content.strip("`")
        if content.lower().startswith("json"):
            content = content[4:].strip()
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("Model response did not contain a valid JSON object.")
    return json.loads(content[start : end + 1])


def _validate_result(data: dict[str, Any]) -> dict[str, Any]:
    missing = REQUIRED_KEYS - set(data.keys())
    if missing:
        raise ValueError(f"Missing required JSON keys: {', '.join(sorted(missing))}")

    data["fit_score"] = int(data["fit_score"])
    data["confidence"] = int(data["confidence"])
    data["risk_level"] = str(data["risk_level"]).title()
    data["recommendation"] = str(data["recommendation"]).title()

    if data["risk_level"] not in {"Low", "Medium", "High"}:
        raise ValueError("risk_level must be Low, Medium, or High.")
    if data["recommendation"] not in {"Apply", "Consider", "Skip"}:
        raise ValueError("recommendation must be Apply, Consider, or Skip.")

    return data


def _validate_research_block_result(data: dict[str, Any]) -> dict[str, Any]:
    required = {
        "block_type",
        "is_human_candidate",
        "person_name",
        "title",
        "email",
        "research_areas",
        "research_interests",
        "institution",
        "department_or_lab",
        "confidence",
        "evidence_used",
        "warnings",
    }
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Missing required JSON keys: {', '.join(sorted(missing))}")

    block_type = str(data["block_type"]).strip()
    if block_type not in RESEARCH_BLOCK_TYPES:
        raise ValueError(f"Invalid block_type: {block_type}")

    normalized = {
        "block_type": block_type,
        "is_human_candidate": bool(data["is_human_candidate"]),
        "person_name": str(data["person_name"]).strip(),
        "title": str(data["title"]).strip(),
        "email": str(data["email"]).strip(),
        "research_areas": [str(item).strip() for item in list(data.get("research_areas") or []) if str(item).strip()],
        "research_interests": [str(item).strip() for item in list(data.get("research_interests") or []) if str(item).strip()],
        "institution": str(data["institution"]).strip(),
        "department_or_lab": str(data["department_or_lab"]).strip(),
        "confidence": max(0, min(100, int(data["confidence"]))),
        "evidence_used": [str(item).strip() for item in list(data.get("evidence_used") or []) if str(item).strip()],
        "warnings": [str(item).strip() for item in list(data.get("warnings") or []) if str(item).strip()],
    }
    return normalized


def _validate_research_email_polish_result(data: dict[str, Any]) -> dict[str, Any]:
    required = {"subject_line", "email_draft"}
    missing = required - set(data.keys())
    if missing:
        raise ValueError(f"Missing required JSON keys: {', '.join(sorted(missing))}")
    subject_line = str(data["subject_line"]).strip()
    email_draft = str(data["email_draft"]).strip()
    if not subject_line or not email_draft:
        raise ValueError("The polished email response must include both a subject line and an email draft.")
    return {
        "subject_line": subject_line[:180],
        "email_draft": email_draft,
    }


def _post_chat_completion(
    *,
    model: str,
    messages: list[dict[str, str]],
    temperature: float,
    timeout: int,
) -> dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured.")

    request_body: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
    }
    if "api.openai.com" in base_url:
        request_body["response_format"] = {"type": "json_object"}

    response = requests.post(
        _chat_endpoint(base_url),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=request_body,
        timeout=timeout,
    )
    response.raise_for_status()
    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    return _extract_json(content)


def call_research_block_judge(
    payload: dict[str, Any],
    *,
    model: str | None = None,
    timeout: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    if not is_llm_configured():
        return None, "OPENAI_API_KEY is not configured."

    system_prompt = (
        "You classify local text blocks extracted from research-profile pages. "
        "Return JSON only. Be conservative: only label a block as person_profile if it clearly represents a real human researcher."
    )
    user_prompt = f"""
Classify this extracted research-page block and return strict JSON with exactly these keys:
block_type, is_human_candidate, person_name, title, email, research_areas, research_interests, institution, department_or_lab, confidence, evidence_used, warnings

Allowed block_type values:
person_profile, research_area, research_interest, title_fragment, page_title, section_heading, breadcrumb, contact_label, institution_label, team_page_label, unknown

Rules:
- Only use person_profile when the block clearly represents one real human researcher
- Do not treat topics, page titles, labels, breadcrumb text, or role-only fragments as person names
- Preserve Chinese names when visible
- Only return an email if it is explicitly present in the block or payload hints
- research_areas and research_interests must be short arrays of strings
- confidence must be an integer from 0 to 100
- evidence_used and warnings must be arrays of concise strings
- Do not add markdown or code fences

Payload:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()

    try:
        parsed = _post_chat_completion(
            model=model or RESEARCH_STANDARD_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0,
            timeout=timeout or RESEARCH_REQUEST_TIMEOUT_SECONDS,
        )
        return _validate_research_block_result(parsed), ""
    except Exception as exc:
        return None, str(exc)


def call_research_email_polish(
    payload: dict[str, Any],
    *,
    model: str | None = None,
    timeout: int | None = None,
) -> tuple[dict[str, Any] | None, str]:
    if not is_llm_configured():
        return None, "OPENAI_API_KEY is not configured."

    system_prompt = (
        "You polish a research outreach email using only supplied evidence. "
        "Return JSON only. Keep the email grounded, specific, concise, and professionally warm. "
        "Do not invent publications, experience, or contact details."
    )
    user_prompt = f"""
Rewrite the outreach email draft and return strict JSON with exactly these keys:
subject_line, email_draft

Rules:
- Keep the recipient, evidence, and topic alignment consistent with the payload
- Preserve factual grounding and do not add new claims
- Keep the tone professional and human, not salesy
- Keep the draft compact and ready to send
- Do not include markdown or code fences

Payload:
{json.dumps(payload, ensure_ascii=False, indent=2)}
""".strip()

    try:
        parsed = _post_chat_completion(
            model=model or RESEARCH_POLISH_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.35,
            timeout=timeout or RESEARCH_POLISH_TIMEOUT_SECONDS,
        )
        return _validate_research_email_polish_result(parsed), ""
    except Exception as exc:
        return None, str(exc)


def call_llm_analysis(payload: dict[str, Any]) -> tuple[dict[str, Any] | None, str]:
    if not is_llm_configured():
        return None, "OPENAI_API_KEY is not configured."

    system_prompt = (
        "You are analyzing whether an early-career job seeker should apply for a role. "
        "Return JSON only. Be concise, realistic, and consistent with the evidence provided."
    )
    user_prompt = f"""
Analyze this job decision payload and return strict JSON with exactly these keys:
fit_score, risk_level, recommendation, confidence, strengths, gaps, job_reality, company_signals, next_steps

Rules:
- risk_level must be one of Low, Medium, High
- recommendation must be one of Apply, Consider, Skip
- fit_score and confidence must be integers from 0 to 100
- strengths, gaps, job_reality, company_signals, next_steps must each be arrays of concise strings
- Do not add markdown or code fences
- Use the fallback result as the baseline if the evidence is ambiguous

Payload:
{json.dumps(payload, indent=2)}
""".strip()

    try:
        parsed = _post_chat_completion(
            model=JOB_ANALYSIS_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            timeout=DEFAULT_REQUEST_TIMEOUT_SECONDS,
        )
        return _validate_result(parsed), ""
    except Exception as exc:
        return None, str(exc)
