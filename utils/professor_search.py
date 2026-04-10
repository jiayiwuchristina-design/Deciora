from __future__ import annotations

import re
from collections import Counter
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup

from utils.helpers import STOPWORDS, clean_text, extract_keywords, split_sentences
from utils.llm import call_research_block_judge, is_llm_configured
from utils.scraping import (
    canonical_domain,
    extract_email_from_text,
    extract_page_text,
    fetch_page_best_effort,
    is_official_academic_domain,
    search_openalex_works,
    search_duckduckgo_html,
    try_bs4,
)


BLOCKED_RESULT_DOMAINS = {
    "x.com",
    "twitter.com",
    "youtube.com",
    "facebook.com",
    "instagram.com",
}

METHOD_PATTERNS = {
    "Theory": ("theory", "theoretical", "formal model"),
    "Empirical": ("empirical", "applied economics", "field data", "observational data", "causal inference"),
    "Experimental": ("experiment", "experimental", "lab study", "field experiment", "randomized", "trial"),
    "Computational": ("computational", "machine learning", "simulation", "data science", "nlp", "computer vision"),
    "Interdisciplinary": ("interdisciplinary", "cross-disciplinary", "social science", "behavioural", "behavioral"),
}

STAGE_HINTS = {
    "Undergraduate": ("undergraduate", "summer student", "bachelor", "college student", "research experience for undergraduates", "reu"),
    "Master": ("master", "msc", "postgraduate", "masters student"),
    "Pre-PhD": ("predoctoral", "pre-doctoral", "research assistant", "ra position", "project assistant"),
    "PhD interest": ("phd", "doctoral", "prospective students", "graduate student"),
}

PAGE_TYPE_PRIORITY = {
    "scholarly_profile": 0,
    "faculty_profile": 0,
    "opportunity_page": 1,
    "lab_page": 2,
    "center_page": 3,
    "department_page": 4,
    "directory_page": 5,
    "project_page": 6,
    "publication_page": 7,
    "other": 9,
}

PAGE_TYPE_LABELS = {
    "scholarly_profile": "Scholarly research profile",
    "faculty_profile": "Official faculty page",
    "opportunity_page": "Official opportunity page",
    "lab_page": "Official lab page",
    "center_page": "Official research center page",
    "department_page": "Official department page",
    "directory_page": "Official directory page",
    "project_page": "Official project page",
    "publication_page": "Official publication page",
    "other": "Official research page",
}

DISCIPLINE_PATTERNS = {
    "Economics": ("economics", "economic", "microeconomics", "macroeconomics", "econometrics"),
    "Business": ("business", "marketing", "finance", "management", "strategy", "operations"),
    "Computer Science": ("computer science", "machine learning", "ai", "artificial intelligence", "software", "computing", "nlp"),
    "Data Science": ("data science", "analytics", "statistical", "statistics", "quantitative", "data analysis"),
    "Psychology": ("psychology", "cognition", "cognitive", "behaviour", "behavior", "decision-making"),
    "Biology": ("biology", "biological", "genetics", "molecular", "ecology", "biomedical"),
    "Engineering": ("engineering", "robotics", "systems", "mechanical", "electrical", "civil"),
    "Medicine": ("medicine", "medical", "clinical", "health", "public health", "patient"),
    "Neuroscience": ("neuroscience", "neural", "brain", "cortex"),
    "Political Science": ("political science", "policy", "governance", "politics", "international relations"),
    "Sociology": ("sociology", "social", "inequality", "demography"),
    "Education": ("education", "learning sciences", "pedagogy", "teaching"),
}

FACULTY_PATH_HINTS = ("faculty", "people", "person", "staff", "profile", "biography", "bio", "member")
LAB_PATH_HINTS = ("lab", "labs", "group", "research-group", "team", "laboratory")
CENTER_PATH_HINTS = ("centre", "center", "research-center", "research-centre", "institute", "center-for", "centre-for")
DEPARTMENT_PATH_HINTS = ("department", "school", "faculty-of", "institute", "program")
DIRECTORY_PATH_HINTS = ("directory", "staff-directory", "people-finder")
OPPORTUNITY_HINTS = (
    "summer research",
    "undergraduate research",
    "research opportunity",
    "research opportunities",
    "research assistant",
    "assistantship",
    "predoctoral",
    "pre-doctoral",
    "studentship",
    "internship",
    "opening",
    "openings",
    "vacancy",
    "vacancies",
    "join the lab",
    "join our group",
    "prospective students",
    "how to apply",
)

PROJECT_HINTS = ("project", "grant", "initiative", "study", "studies", "research news", "lab news")
PUBLICATION_HINTS = ("publication", "publications", "paper", "papers", "selected work", "working paper", "article", "journal")
INSTITUTIONAL_TRUST_HINTS = (
    "university",
    "college",
    "department",
    "faculty",
    "school",
    "institute",
    "research center",
    "research centre",
    "lab",
    "laboratory",
    "research group",
    "academic",
)
CONTEXT_EXPANSION_PAGE_TYPES = {"lab_page", "center_page", "department_page", "directory_page", "project_page", "opportunity_page"}
GENERIC_NAME_WORDS = {
    "research",
    "lab",
    "group",
    "department",
    "center",
    "centre",
    "program",
    "programme",
    "opportunity",
    "opportunities",
    "faculty",
    "team",
    "staff",
    "directory",
    "school",
    "college",
    "university",
    "project",
    "projects",
    "institute",
}
ROLE_TITLE_HINTS = (
    "assistant professor",
    "associate professor",
    "full professor",
    "professor",
    "chair professor",
    "adjunct professor",
    "visiting professor",
    "research professor",
    "research assistant professor",
    "lecturer",
    "scientist",
    "research scientist",
    "postdoctoral",
    "postdoc",
    "fellow",
    "research fellow",
    "principal investigator",
    "pi",
    "director",
    "group leader",
    "lab manager",
    "staff",
    "faculty",
    "member",
)
RESEARCH_NOISE_TERMS = {
    "analysis",
    "analyst",
    "application",
    "coursework",
    "cv",
    "curriculum",
    "engine",
    "engineer",
    "github",
    "internship",
    "learning",
    "model",
    "portfolio",
    "programming",
    "python",
    "resume",
    "science",
    "student",
    "study",
    "studies",
    "systems",
    "university",
}
OPENALEX_SOURCE_LABEL = "Scholarly publication metadata"
CONTAINER_LABEL_PREFIXES = (
    "research staff",
    "staff",
    "faculty",
    "people",
    "team",
    "members",
    "research members",
    "group members",
    "lab members",
)

FALSE_NAME_TOKENS = {
    "tel",
    "telephone",
    "phone",
    "mobile",
    "email",
    "e-mail",
    "mail",
    "office",
    "address",
    "location",
    "room",
    "fax",
    "website",
    "webpage",
    "homepage",
    "contact",
    "research",
    "researcher",
    "researchers",
    "research page",
    "page",
    "profile",
    "people",
    "staff",
    "faculty",
    "team",
    "members",
    "department",
    "school",
    "institute",
    "university",
    "research area",
    "research areas",
    "research interest",
    "research interests",
    "research direction",
    "research directions",
}

FIELD_LABEL_PATTERNS = (
    "tel",
    "telephone",
    "phone",
    "mobile",
    "email",
    "e-mail",
    "office",
    "address",
    "room",
    "website",
    "homepage",
    "contact",
    "research area",
    "research areas",
    "research interest",
    "research interests",
    "research direction",
    "research directions",
    "publication",
    "publications",
    "project",
    "projects",
    "paper",
    "papers",
    "location",
    "fax",
    "office hour",
    "office hours",
    "邮箱",
    "电子邮箱",
    "邮件",
    "电话",
    "办公电话",
    "办公室",
    "办公地点",
    "研究方向",
    "研究领域",
    "研究兴趣",
    "研究内容",
    "个人简介",
    "简介",
    "联系方式",
    "主页",
    "地址",
)

CHINESE_ROLE_HINTS = (
    "研究员",
    "副研究员",
    "助理研究员",
    "博士后",
    "教授",
    "副教授",
    "助理教授",
    "讲师",
    "工程师",
    "工程技术人员",
    "研究助理",
    "课题组长",
    "团队负责人",
)

CHINESE_CONTAINER_HINTS = (
    "科研人员",
    "研究人员",
    "人才队伍",
    "成员",
    "团队",
    "师资",
    "教师",
    "研究团队",
    "研究页面",
    "科研队伍",
)

CHINESE_NAV_HINTS = (
    "首页",
    "科学研究",
    "人才队伍",
    "研究团队",
    "科研人员",
    "当前位置",
)

PERSON_BLOCK_TYPE = "person_profile"
NON_PERSON_BLOCK_TYPES = {
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


def _normalize_tokens(values: list[str]) -> list[str]:
    return sorted({clean_text(value).lower() for value in values if clean_text(value)})


def _normalized_result_url(url: str) -> str:
    parsed = urlparse(url)
    path = parsed.path.rstrip("/") or "/"
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _same_domain_family(domain_a: str, domain_b: str) -> bool:
    a = (domain_a or "").replace("www.", "")
    b = (domain_b or "").replace("www.", "")
    return bool(a and b and (a == b or a.endswith(f".{b}") or b.endswith(f".{a}")))


def _extract_all_emails(text: str) -> list[str]:
    found = re.findall(r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})", text or "", flags=re.IGNORECASE)
    emails: list[str] = []
    seen: set[str] = set()
    for email in found:
        lowered = email.lower()
        if lowered not in seen:
            emails.append(email)
            seen.add(lowered)
    return emails


def _regex_detect_emails(text: str) -> list[str]:
    emails = _extract_all_emails(text)
    single = extract_email_from_text(text or "")
    if single and single.lower() not in {email.lower() for email in emails}:
        emails.insert(0, single)
    return emails


def _email_confidence(name: str, email: str, local_emails: list[str], block_text: str) -> str:
    if not email:
        return "missing"
    lowered_pool = {item.lower() for item in local_emails}
    if email.lower() in lowered_pool:
        if _contains_cjk(name) and len(local_emails) == 1:
            return "high"
        if _email_name_score(email, name) > 0:
            return "high"
        if len(local_emails) == 1 and clean_text(block_text):
            return "moderate"
    return "low"


def _extract_emails_from_node(node: BeautifulSoup, page_domain: str, *, allow_any_visible: bool = False) -> list[str]:
    emails: list[str] = []
    seen: set[str] = set()
    for link in node.select("a[href^='mailto:']"):
        href = link.get("href", "").replace("mailto:", "").strip().split("?")[0].strip()
        if not href:
            continue
        email_domain = canonical_domain(f"https://{href.split('@')[-1]}") if "@" in href else ""
        if allow_any_visible or not email_domain or _same_domain_family(email_domain, page_domain):
            lowered = href.lower()
            if lowered not in seen:
                emails.append(href)
                seen.add(lowered)
    for email in _extract_all_emails(node.get_text(" ", strip=True)):
        email_domain = canonical_domain(f"https://{email.split('@')[-1]}") if "@" in email else ""
        if allow_any_visible or not email_domain or _same_domain_family(email_domain, page_domain):
            lowered = email.lower()
            if lowered not in seen:
                emails.append(email)
                seen.add(lowered)
    return emails


def _email_name_score(email: str, name: str) -> int:
    local = clean_text(email.split("@")[0]).lower()
    name_tokens = [token.lower() for token in re.findall(r"[A-Za-z]{2,}", clean_text(name))]
    if not local or not name_tokens:
        return 0
    score = 0
    for token in name_tokens:
        if token in local:
            score += 2
    if len(name_tokens) >= 2:
        first, last = name_tokens[0], name_tokens[-1]
        if local.startswith(first[0] + last):
            score += 4
        if local.startswith(first) and last in local:
            score += 3
        if local.startswith(last):
            score += 2
    return score


def _best_email_for_name(emails: list[str], name: str) -> tuple[str, str]:
    if not emails:
        return "", ""
    ranked = sorted(emails, key=lambda email: (-_email_name_score(email, name), email.lower()))
    chosen = ranked[0]
    if _email_name_score(chosen, name) > 0:
        return chosen, "Visible email matched to the researcher block"
    if len(emails) == 1:
        return chosen, "Only visible email found in the researcher block"
    return "", ""


def _source_credibility(url: str, page_type: str, text: str = "", title: str = "") -> tuple[str, str]:
    domain = canonical_domain(url)
    path = urlparse(url).path.lower()
    haystack = clean_text(" ".join([title, text[:1800], path, domain])).lower()
    if is_official_academic_domain(url):
        return "High", "The source appears to be an official academic or university-affiliated page."
    if page_type in {"faculty_profile", "lab_page", "center_page", "department_page", "directory_page"} and any(
        token in haystack for token in ("research", "lab", "group", "faculty", "department", "institute", "center", "centre", "team")
    ):
        return "Moderate", "The source appears to be an official organizational research page, but not a clearly academic faculty page."
    if any(token in path for token in ("research", "lab", "group", "team", "people", "faculty", "scientist")):
        return "Moderate", "The source shows strong research-profile cues, but full official affiliation confidence is limited."
    return "Limited", "The source could be useful, but official profile confidence is limited from the available signals."


def _quote_if_phrase(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    return f'"{cleaned}"' if " " in cleaned else cleaned


def _extract_interest_phrases(interests_text: str) -> list[str]:
    phrases: list[str] = []
    for part in re.split(r"[\n,;/|]+", interests_text):
        cleaned = clean_text(part)
        if len(cleaned.split()) < 2 or len(cleaned) < 6:
            continue
        if cleaned not in phrases:
            phrases.append(cleaned)
        if len(phrases) >= 6:
            break
    return phrases


def _contains_cjk(text: str) -> bool:
    return bool(re.search(r"[\u3400-\u9fff]", text or ""))


def _looks_like_field_label(text: str) -> bool:
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    if not cleaned:
        return False
    if any(pattern in lowered for pattern in FIELD_LABEL_PATTERNS if pattern.isascii()):
        return True
    if any(pattern in cleaned for pattern in FIELD_LABEL_PATTERNS if not pattern.isascii()):
        return True
    if lowered.endswith(":") or cleaned.endswith("："):
        return True
    return False


def _looks_like_role_only_text(text: str) -> bool:
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    if not cleaned:
        return False
    if _looks_like_field_label(cleaned):
        return False
    if any(hint in lowered for hint in ROLE_TITLE_HINTS):
        return True
    if any(hint in cleaned for hint in CHINESE_ROLE_HINTS):
        return True
    return False


def _strip_field_label_artifacts(text: str) -> str:
    cleaned = clean_text(text)
    if not cleaned:
        return ""
    cleaned = re.sub(r"[\|｜/•]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -—:：|")
    for splitter in (
        r"\b(?:Tel|Telephone|Phone|Mobile|Email|E-mail|Office|Address|Room|Website|Homepage|Contact)\b[:：]?",
        r"(?:邮箱|电子邮箱|电话|办公电话|办公室|办公地点|研究方向|研究领域|研究兴趣|个人简介|联系方式|主页|地址)[:：]?",
    ):
        cleaned = re.split(splitter, cleaned, maxsplit=1, flags=re.IGNORECASE)[0]
    cleaned = clean_text(cleaned)
    return cleaned.strip(" -—:：|,，;；")


def _normalize_person_name(text: str) -> str:
    cleaned = _strip_field_label_artifacts(text)
    cleaned = re.sub(r"^(?:Name|姓名)[:：]\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^(?:Prof(?:essor)?|Dr)\.?\s+", "", cleaned, flags=re.IGNORECASE)
    english_name_with_role = re.match(
        r"^([A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){1,2})(?=\s+(?:Assistant|Associate|Research|Postdoctoral|Professor|Scientist|Fellow|Lecturer)\b)",
        cleaned,
    )
    if english_name_with_role:
        cleaned = english_name_with_role.group(1)
    chinese_name_with_role = re.match(
        r"^([\u4e00-\u9fff]{2,4})(?=\s*(?:研究员|副研究员|助理研究员|教授|副教授|助理教授|博士后|工程师|工程技术人员))",
        cleaned,
    )
    if chinese_name_with_role:
        cleaned = chinese_name_with_role.group(1)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if "首页" in cleaned and _contains_cjk(cleaned):
        chinese_names = re.findall(r"[\u4e00-\u9fff]{2,4}", cleaned)
        if chinese_names:
            cleaned = chinese_names[-1]
    return cleaned.strip(" -—:：|,，;；")


def _looks_like_person_name(text: str) -> bool:
    cleaned = _normalize_person_name(text)
    if not cleaned:
        return False
    if "@" in cleaned or re.search(r"\d", cleaned):
        return False
    lowered = cleaned.lower()
    if _looks_like_field_label(cleaned):
        return False
    if _looks_like_role_only_text(cleaned):
        return False
    if any(token in lowered for token in FALSE_NAME_TOKENS):
        return False
    if any(token in cleaned for token in CHINESE_CONTAINER_HINTS + CHINESE_NAV_HINTS):
        return False
    if _contains_cjk(cleaned):
        chinese_name = re.fullmatch(r"[\u4e00-\u9fff]{2,4}", cleaned)
        if not chinese_name:
            return False
        if any(token in cleaned for token in ("研究", "量子", "学院", "中心", "团队", "方向", "简介", "邮箱", "电话", "办公室", "成员", "人员", "科学")):
            return False
        return True
    words = cleaned.split()
    if not 2 <= len(words) <= 4:
        return False
    lowered_words = [word.lower() for word in words]
    if any(word in GENERIC_NAME_WORDS or word in FALSE_NAME_TOKENS for word in lowered_words):
        return False
    if any(word in {"of", "for", "and", "the"} for word in lowered_words):
        return False
    capitalized = sum(1 for word in words if word and word[0].isupper())
    return capitalized >= max(2, len(words) - 1)


def _looks_like_container_label(text: str) -> bool:
    cleaned = clean_text(text).lower()
    if not cleaned:
        return False
    if cleaned in {"people", "faculty", "staff", "team", "members"}:
        return True
    if any(cleaned.startswith(prefix) for prefix in CONTAINER_LABEL_PREFIXES):
        return True
    if any(hint in cleaned for hint in CHINESE_CONTAINER_HINTS):
        return True
    words = cleaned.split()
    return bool(words) and all(word in GENERIC_NAME_WORDS or word in {"research"} for word in words)


def _name_tokens(text: str) -> list[str]:
    normalized = _normalize_person_name(text)
    if _contains_cjk(normalized):
        cjk_names = re.findall(r"[\u4e00-\u9fff]{2,4}", normalized)
        if cjk_names:
            return [cjk_names[0]]
    return [token.lower() for token in re.findall(r"[A-Za-z]{2,}", normalized) if token.lower() not in GENERIC_NAME_WORDS]


def _names_compatible(expected: str, actual: str) -> bool:
    expected_clean = _normalize_person_name(expected)
    actual_clean = _normalize_person_name(actual)
    if _contains_cjk(expected_clean) or _contains_cjk(actual_clean):
        expected_cjk = re.findall(r"[\u4e00-\u9fff]{2,4}", expected_clean)
        actual_cjk = re.findall(r"[\u4e00-\u9fff]{2,4}", actual_clean)
        if expected_cjk and actual_cjk:
            return expected_cjk[0] == actual_cjk[0]
    expected_tokens = _name_tokens(expected)
    actual_tokens = _name_tokens(actual)
    if not expected_tokens or not actual_tokens:
        return False
    if expected_tokens[-1] != actual_tokens[-1]:
        return False
    if expected_tokens[0] == actual_tokens[0]:
        return True
    return expected_tokens[0][0] == actual_tokens[0][0]


def _candidate_uid(candidate: dict) -> str:
    name = _normalize_person_name(candidate.get("lead_contact_name") or candidate.get("name", "")).lower()
    role = clean_text(candidate.get("role_title", "")).lower()
    primary_url = clean_text(candidate.get("official_profile_url") or candidate.get("primary_source_url", "")).lower()
    university = clean_text(candidate.get("university", "")).lower()
    email = clean_text(candidate.get("official_email", "")).lower()
    return "|".join(part for part in (name, role, university, primary_url or email) if part)


def _canonical_person_name(candidate: dict) -> str:
    name = _normalize_person_name(candidate.get("name", ""))
    lead = _normalize_person_name(candidate.get("lead_contact_name", ""))
    if lead and not _looks_like_container_label(lead):
        if not name or _looks_like_container_label(name):
            return lead
        if _names_compatible(name, lead):
            return lead if len(lead) >= len(name) else name
    if name and not _looks_like_container_label(name):
        return name
    return ""


def _is_person_candidate(candidate: dict) -> bool:
    canonical_name = _canonical_person_name(candidate)
    return bool(canonical_name and _looks_like_person_name(canonical_name))


def _enforce_candidate_consistency(candidate: dict) -> dict:
    normalized = {**candidate}
    canonical_name = _canonical_person_name(normalized)
    if canonical_name:
        normalized["name"] = canonical_name
        normalized["lead_contact_name"] = canonical_name
        if normalized.get("entity_type") in {"Directory", "Research page", "Research Match"}:
            role_title = clean_text(normalized.get("role_title", "")).lower()
            normalized["entity_type"] = "Professor" if "professor" in role_title else "Researcher"
    if _looks_like_container_label(normalized.get("role_title", "")):
        normalized["role_title"] = ""
    if normalized.get("official_email") and canonical_name and _email_name_score(normalized["official_email"], canonical_name) <= 0:
        if normalized.get("page_type") in {"directory_page", "lab_page", "department_page", "center_page"}:
            normalized["official_email"] = ""
            normalized["email_source"] = "Email attribution was ambiguous on the multi-person source page."
    normalized["candidate_id"] = _candidate_uid(normalized)
    return normalized


def _detect_page_language(text: str, title: str = "") -> str:
    sample = clean_text(f"{title}\n{text[:2400]}")
    cjk_count = len(re.findall(r"[\u3400-\u9fff]", sample))
    latin_count = len(re.findall(r"[A-Za-z]", sample))
    if cjk_count >= 20 and latin_count <= max(8, cjk_count // 3):
        return "Chinese"
    if cjk_count >= 8 and latin_count >= 10:
        return "Mixed"
    if latin_count >= 24 and cjk_count == 0:
        return "English"
    if latin_count >= 14 and cjk_count < 4:
        return "English"
    return "Unknown"


def _looks_like_generic_target_label(text: str) -> bool:
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    if not cleaned:
        return True
    if _looks_like_container_label(cleaned):
        return True
    return lowered in {
        "research page",
        "official research page",
        "research match",
        "research profile",
        "directory",
        "opportunity",
        "department",
        "lab",
        "research center",
    }


def _name_has_field_label_pollution(text: str) -> bool:
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    if not cleaned:
        return True
    if _looks_like_field_label(cleaned):
        return True
    if any(token in lowered for token in FALSE_NAME_TOKENS):
        return True
    if any(token in cleaned for token in CHINESE_CONTAINER_HINTS + CHINESE_NAV_HINTS):
        return True
    if any(token in lowered for token in (" tel", " email", " office", " research area", " research interest")):
        return True
    return False


def _candidate_debug_snapshot(candidate: dict) -> dict:
    normalized = _enforce_candidate_consistency(candidate)
    return {
        "candidate_id": normalized.get("candidate_id", ""),
        "name": normalized.get("name", ""),
        "title": normalized.get("role_title", ""),
        "email": normalized.get("official_email", ""),
        "email_confidence": normalized.get("email_confidence", ""),
        "profile_url": normalized.get("official_profile_url") or normalized.get("primary_source_url", ""),
        "page_type": normalized.get("page_type", ""),
        "candidate_type": normalized.get("candidate_type", ""),
        "extraction_confidence": normalized.get("extraction_confidence", 0),
        "attribution_confidence": normalized.get("attribution_confidence", ""),
        "warnings": normalized.get("warnings", []),
        "person_like": _is_person_candidate(normalized),
    }


def _new_parser_report(target_url: str, page_context: dict, page_text: str) -> dict:
    return {
        "input_url": target_url,
        "page_type": page_context.get("page_type", "other"),
        "page_language": _detect_page_language(page_text, page_context.get("name", "")),
        "page_word_count": len(clean_text(page_text).split()),
        "raw_person_block_count": 0,
        "visible_text_candidate_count": 0,
        "candidate_objects_built_count": 0,
        "candidate_names": [],
        "candidate_emails": [],
        "candidate_snapshots": [],
        "contact_names": [],
        "page_title_fallback_used": False,
        "page_level_fallback_used": False,
        "fallback_path_used": "",
        "person_level_extraction_succeeded": False,
        "multi_profile_detected": False,
        "selected_candidate_id": "",
        "selected_candidate_name": "",
        "selected_candidate_email": "",
        "selected_candidate_title": "",
        "selected_candidate_profile_url": "",
        "selected_candidate_person_like": False,
        "candidate_binding_valid": True,
        "related_pages_checked": 0,
        "related_pages_used": [],
        "linked_profile_candidate_count": len(page_context.get("related_candidate_links", [])),
        "official_email_found": bool(page_context.get("official_email")),
        "failure_categories": [],
        "warning_categories": [],
        "events": [],
    }


def _record_parser_category(report: dict, category: str, detail: str, severity: str = "warning") -> None:
    target_key = "failure_categories" if severity == "failure" else "warning_categories"
    if category not in report[target_key]:
        report[target_key].append(category)
    report["events"].append({"category": category, "detail": detail, "severity": severity})


def _selected_binding_issues(candidate: dict) -> list[str]:
    issues: list[str] = []
    name = _normalize_person_name(candidate.get("lead_contact_name") or candidate.get("name", ""))
    email = clean_text(candidate.get("official_email", ""))
    role_title = clean_text(candidate.get("role_title", ""))
    if not _looks_like_person_name(name):
        issues.append("fallback_to_generic_target")
    if email and name and not _contains_cjk(name) and _email_name_score(email, name) <= 0:
        issues.append("selected_candidate_binding_mismatch")
    if role_title and (_looks_like_field_label(role_title) or _looks_like_container_label(role_title)):
        issues.append("selected_candidate_binding_mismatch")
    return issues


def _classify_non_person_block_type(text: str, page_context: dict) -> str:
    cleaned = clean_text(text)
    lowered = cleaned.lower()
    if not cleaned:
        return "unknown"
    if any(token in cleaned for token in CHINESE_NAV_HINTS) or " / " in cleaned or " > " in cleaned:
        return "breadcrumb"
    if _looks_like_container_label(cleaned):
        return "team_page_label"
    if _looks_like_field_label(cleaned):
        if any(token in lowered for token in ("research area", "research direction", "research interest")) or any(
            token in cleaned for token in ("研究方向", "研究领域", "研究兴趣", "研究内容")
        ):
            return "research_area"
        return "contact_label"
    if _looks_like_role_only_text(cleaned):
        return "title_fragment"
    if clean_text(page_context.get("name", "")) == cleaned or cleaned == clean_text(page_context.get("page_type_label", "")):
        return "page_title"
    if any(token in lowered for token in ("department", "university", "institute", "school", "faculty")):
        return "institution_label"
    if any(token in cleaned for token in ("学院", "研究院", "大学", "实验室", "研究中心")):
        return "institution_label"
    if len(cleaned.split()) <= 8:
        return "section_heading"
    return "unknown"


def _extract_labeled_topics(block_text: str) -> tuple[list[str], list[str]]:
    research_areas: list[str] = []
    research_interests: list[str] = []
    lines = [clean_text(line) for line in re.split(r"[\n\r]+", block_text) if clean_text(line)]
    for line in lines[:10]:
        lowered = line.lower()
        area_value = ""
        if any(token in lowered for token in ("research area", "research direction", "research directions")):
            parts = re.split(r"research area[s]?[:：]?|research direction[s]?[:：]?", line, maxsplit=1, flags=re.IGNORECASE)
            area_value = clean_text(parts[-1])
        elif any(token in line for token in ("研究方向", "研究领域")):
            parts = re.split(r"研究方向[:：]?|研究领域[:：]?", line, maxsplit=1)
            area_value = clean_text(parts[-1])
        if area_value:
            research_areas.extend([clean_text(item) for item in re.split(r"[;,/，、]", area_value) if clean_text(item)])

        interest_value = ""
        if "research interest" in lowered or "research interests" in lowered:
            parts = re.split(r"research interest[s]?[:：]?", line, maxsplit=1, flags=re.IGNORECASE)
            interest_value = clean_text(parts[-1])
        elif "研究兴趣" in line:
            parts = re.split(r"研究兴趣[:：]?", line, maxsplit=1)
            interest_value = clean_text(parts[-1])
        if interest_value:
            research_interests.extend([clean_text(item) for item in re.split(r"[;,/，、]", interest_value) if clean_text(item)])

    return _merge_ordered_unique(research_areas, [], limit=6), _merge_ordered_unique(research_interests, [], limit=6)


def _heuristic_block_judge(
    *,
    block_text: str,
    page_context: dict,
    forced_name: str = "",
    name_hint: str = "",
    local_emails: list[str] | None = None,
    profile_url: str = "",
    block_index: int = -1,
) -> dict:
    normalized_forced_name = _normalize_person_name(forced_name)
    normalized_name_hint = _normalize_person_name(name_hint)
    name = normalized_forced_name or normalized_name_hint
    title = _guess_role_title(block_text, name)
    local_emails = list(dict.fromkeys(local_emails or _regex_detect_emails(block_text)))
    if not name and local_emails:
        # Try one more pass when the block only yielded an email but likely contains a person nearby.
        candidate_from_text = _normalize_person_name(block_text.split("\n", 1)[0])
        if _looks_like_person_name(candidate_from_text):
            name = candidate_from_text
    email = ""
    email_source = ""
    if name:
        email, email_source = _best_email_for_name(local_emails, name)
    if not email and len(local_emails) == 1:
        email = local_emails[0]
        email_source = "Only regex-detected email found in the local block"

    research_areas, research_interests = _extract_labeled_topics(block_text)
    if not research_areas and not research_interests:
        extracted_tags, _disciplines, extracted_recent = _extract_block_topics(block_text, page_context)
        research_areas = extracted_tags[:6]
        research_interests = extracted_recent[:4]

    evidence_used: list[str] = []
    if name:
        evidence_used.append("visible local name")
    if title:
        evidence_used.append("same-block role/title")
    if email:
        evidence_used.append("same-block email regex")
    if profile_url:
        evidence_used.append("linked same-domain profile")
    if research_areas or research_interests:
        evidence_used.append("same-block research descriptors")

    block_type = PERSON_BLOCK_TYPE if name and _looks_like_person_name(name) else _classify_non_person_block_type(block_text, page_context)
    is_human_candidate = block_type == PERSON_BLOCK_TYPE and bool(name)
    warnings: list[str] = []
    if name and _name_has_field_label_pollution(name):
        warnings.append("Name candidate contains label-like pollution.")
    if local_emails and not email:
        warnings.append("Emails were present but person-level attribution stayed uncertain.")
    if title and _looks_like_field_label(title):
        warnings.append("Role/title extraction is weak.")

    confidence = 25
    confidence += 28 if name and _looks_like_person_name(name) else 0
    confidence += 18 if title else 0
    confidence += 18 if email else 0
    confidence += 8 if research_areas or research_interests else 0
    confidence += 8 if profile_url else 0
    if not is_human_candidate:
        confidence = min(confidence, 42)

    return {
        "block_type": block_type,
        "is_human_candidate": is_human_candidate,
        "person_name": name,
        "title": title,
        "email": email,
        "email_source": email_source,
        "email_confidence": _email_confidence(name, email, local_emails, block_text),
        "research_areas": research_areas[:6],
        "research_interests": research_interests[:6],
        "institution": page_context.get("university", ""),
        "department_or_lab": page_context.get("department_or_lab", ""),
        "confidence": max(0, min(100, confidence)),
        "evidence_used": evidence_used,
        "warnings": warnings,
        "judge_mode": "heuristic",
        "source_block_index": block_index,
    }


def _ai_block_judge(
    *,
    block_text: str,
    page_context: dict,
    heuristic_judgment: dict,
    local_emails: list[str],
    profile_url: str,
) -> tuple[dict | None, str]:
    if not is_llm_configured():
        return None, "LLM not configured."

    payload = {
        "page_type": page_context.get("page_type", "other"),
        "page_language": _detect_page_language(block_text, page_context.get("name", "")),
        "page_context_name": page_context.get("name", ""),
        "institution_hint": page_context.get("university", ""),
        "department_or_lab_hint": page_context.get("department_or_lab", ""),
        "heuristic_hint": {
            "block_type": heuristic_judgment.get("block_type", "unknown"),
            "person_name": heuristic_judgment.get("person_name", ""),
            "title": heuristic_judgment.get("title", ""),
            "email": heuristic_judgment.get("email", ""),
            "research_areas": heuristic_judgment.get("research_areas", []),
            "research_interests": heuristic_judgment.get("research_interests", []),
        },
        "regex_detected_emails": local_emails,
        "profile_url_hint": profile_url,
        "block_text": clean_text(block_text)[:1800],
    }
    judged, error = call_research_block_judge(payload)
    if not judged:
        return None, error
    judged["judge_mode"] = "llm"
    judged["email_source"] = ""
    judged["email_confidence"] = _email_confidence(
        judged.get("person_name", ""),
        judged.get("email", ""),
        local_emails,
        block_text,
    )
    return judged, ""


def _post_validate_block_judgment(judgment: dict, block_text: str, page_context: dict) -> tuple[dict, bool]:
    normalized = {**judgment}
    name = _normalize_person_name(normalized.get("person_name", ""))
    title = clean_text(normalized.get("title", ""))
    email = clean_text(normalized.get("email", ""))
    block_type = normalized.get("block_type", "unknown")
    warnings = list(normalized.get("warnings", []))
    normalized["person_name"] = name
    normalized["title"] = "" if _looks_like_field_label(title) or _looks_like_container_label(title) else title
    normalized["email"] = email if re.fullmatch(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", email, flags=re.IGNORECASE) else ""
    normalized["institution"] = clean_text(normalized.get("institution", "")) or page_context.get("university", "")
    normalized["department_or_lab"] = clean_text(normalized.get("department_or_lab", "")) or page_context.get("department_or_lab", "")
    normalized["research_areas"] = [clean_text(item) for item in normalized.get("research_areas", []) if clean_text(item)]
    normalized["research_interests"] = [clean_text(item) for item in normalized.get("research_interests", []) if clean_text(item)]

    is_valid_person = bool(normalized.get("is_human_candidate")) and block_type == PERSON_BLOCK_TYPE
    if not _looks_like_person_name(name) or _looks_like_container_label(name) or _name_has_field_label_pollution(name):
        is_valid_person = False
        warnings.append("Post-validation rejected the proposed name as non-human or label-like.")
    if block_type in NON_PERSON_BLOCK_TYPES:
        is_valid_person = False
        warnings.append("The judged block type is non-person content.")
    supporting_signals = sum(
        [
            bool(normalized.get("title")),
            bool(normalized.get("email")),
            bool(normalized.get("research_areas") or normalized.get("research_interests")),
            bool(clean_text(block_text).split()),
        ]
    )
    if is_valid_person and supporting_signals < 2:
        is_valid_person = False
        warnings.append("The block lacked enough supporting person-specific evidence after validation.")
    normalized["warnings"] = list(dict.fromkeys(warnings))[:6]
    normalized["is_human_candidate"] = is_valid_person
    normalized["extraction_confidence"] = normalized.get("confidence", 0)
    return normalized, is_valid_person


def _judge_research_block(
    *,
    block_text: str,
    page_context: dict,
    forced_name: str = "",
    name_hint: str = "",
    local_emails: list[str] | None = None,
    profile_url: str = "",
    block_index: int = -1,
) -> dict:
    heuristic = _heuristic_block_judge(
        block_text=block_text,
        page_context=page_context,
        forced_name=forced_name,
        name_hint=name_hint,
        local_emails=local_emails or [],
        profile_url=profile_url,
        block_index=block_index,
    )
    ai_judgment, ai_error = _ai_block_judge(
        block_text=block_text,
        page_context=page_context,
        heuristic_judgment=heuristic,
        local_emails=list(local_emails or []),
        profile_url=profile_url,
    )
    judgment = ai_judgment or heuristic
    if ai_error and not ai_judgment:
        judgment["warnings"] = list(dict.fromkeys(judgment.get("warnings", []) + [f"AI judge unavailable: {ai_error}"]))[:6]
    merged_evidence = heuristic.get("evidence_used", []) + judgment.get("evidence_used", [])
    judgment["evidence_used"] = list(dict.fromkeys(merged_evidence))[:6]
    if not judgment.get("person_name") and heuristic.get("person_name"):
        judgment["person_name"] = heuristic["person_name"]
    if not judgment.get("title") and heuristic.get("title"):
        judgment["title"] = heuristic["title"]
    if not judgment.get("email") and heuristic.get("email"):
        judgment["email"] = heuristic["email"]
        judgment["email_source"] = heuristic.get("email_source", "")
        judgment["email_confidence"] = heuristic.get("email_confidence", "missing")
    if not judgment.get("research_areas"):
        judgment["research_areas"] = heuristic.get("research_areas", [])
    if not judgment.get("research_interests"):
        judgment["research_interests"] = heuristic.get("research_interests", [])
    if not judgment.get("institution"):
        judgment["institution"] = heuristic.get("institution", "")
    if not judgment.get("department_or_lab"):
        judgment["department_or_lab"] = heuristic.get("department_or_lab", "")
    judgment["source_block_index"] = block_index
    validated, is_valid_person = _post_validate_block_judgment(judgment, block_text, page_context)
    validated["is_human_candidate"] = is_valid_person
    return validated


def _looks_trustworthy_research_result(url: str, title: str = "", snippet: str = "") -> bool:
    if is_official_academic_domain(url):
        return True
    domain = canonical_domain(url)
    if not domain or domain in BLOCKED_RESULT_DOMAINS:
        return False
    haystack = clean_text(" ".join([title, snippet, url])).lower()
    path = urlparse(url).path.lower()
    if domain.endswith((".org", ".net")) and any(hint in haystack or hint in path or hint in domain for hint in INSTITUTIONAL_TRUST_HINTS):
        return True
    if any(token in domain for token in ("research", "lab", "center", "centre", "institute")) and any(
        hint in haystack for hint in INSTITUTIONAL_TRUST_HINTS
    ):
        return True
    return False


def _first_resume_line(resume_text: str) -> str:
    for line in resume_text.splitlines():
        cleaned = clean_text(line)
        if cleaned:
            return cleaned
    return "The student"


def _extract_resume_name(resume_text: str) -> str:
    first_line = _first_resume_line(resume_text)
    if "@" in first_line or "|" in first_line or len(first_line.split()) > 5:
        return "The student"
    return first_line


def _extract_discipline_tags(text: str) -> list[str]:
    lowered = clean_text(text).lower()
    tags = [label for label, patterns in DISCIPLINE_PATTERNS.items() if any(pattern in lowered for pattern in patterns)]
    return sorted(tags)[:4]


def _filter_research_terms(values: list[str], limit: int = 12) -> list[str]:
    filtered: list[str] = []
    seen: set[str] = set()
    for value in values:
        cleaned = clean_text(value).lower()
        cleaned = re.sub(r"[^a-z0-9+\-/# ]+", " ", cleaned)
        cleaned = clean_text(cleaned)
        if not cleaned or cleaned in seen:
            continue
        if cleaned in STOPWORDS or cleaned in RESEARCH_NOISE_TERMS:
            continue
        if len(cleaned) < 3 or cleaned.isdigit():
            continue
        if len(cleaned.split()) == 1 and cleaned.endswith(("ing", "ed")) and cleaned not in {"nlp"}:
            continue
        seen.add(cleaned)
        filtered.append(cleaned)
        if len(filtered) >= limit:
            break
    return filtered


def _normalize_topic_profile(
    interests_text: str,
    resume_sections: dict,
    existing_skills: str,
    preferred_methods: list[str],
) -> dict[str, list[str]]:
    interest_phrases = _extract_interest_phrases(interests_text)
    interests_keywords = list(extract_keywords(interests_text, limit=16))
    project_text = "\n".join(
        [
            resume_sections.get("projects", ""),
            resume_sections.get("research", ""),
            resume_sections.get("experience", ""),
            resume_sections.get("summary", ""),
        ]
    )
    project_keywords = list(extract_keywords(project_text, limit=18))
    skill_keywords = list(extract_keywords(f"{resume_sections.get('skills', '')}\n{existing_skills}", limit=14))
    method_terms = _filter_research_terms(preferred_methods + list(extract_keywords(project_text, limit=12)), limit=8)
    topic_terms = _filter_research_terms(
        interest_phrases
        + interests_keywords
        + project_keywords
        + skill_keywords[:4],
        limit=16,
    )
    tool_terms = _filter_research_terms(skill_keywords + method_terms, limit=10)
    return {
        "interest_phrases": interest_phrases[:6],
        "topic_terms": topic_terms,
        "method_terms": method_terms,
        "tool_terms": tool_terms,
    }


def _build_scholarly_queries(candidate_profile: dict) -> list[str]:
    topics = candidate_profile.get("normalized_topics", [])[:6]
    phrases = candidate_profile.get("interest_phrases", [])[:4]
    methods = candidate_profile.get("normalized_methods", [])[:2]
    tools = candidate_profile.get("normalized_tools", [])[:2]
    disciplines = [tag.lower() for tag in candidate_profile.get("discipline_tags", [])[:2]]

    query_variants: list[str] = []
    if phrases:
        query_variants.extend(phrases[:3])
    if topics:
        query_variants.append(" ".join(topics[:3]))
        if len(topics) >= 4:
            query_variants.append(" ".join(topics[1:4]))
    if disciplines:
        query_variants.append(" ".join(topics[:2] + disciplines[:1]).strip())
    if methods:
        query_variants.append(" ".join(topics[:2] + methods[:1]).strip())
    if tools:
        query_variants.append(" ".join(topics[:2] + tools[:1]).strip())

    cleaned_queries = _filter_research_terms(query_variants, limit=8)
    fallback = clean_text(candidate_profile.get("interests_text", ""))
    if fallback and fallback.lower() not in cleaned_queries:
        cleaned_queries.append(fallback.lower())
    return [query for query in cleaned_queries if clean_text(query)][:6]


def _extract_work_topics(work: dict) -> list[str]:
    topics: list[str] = []
    primary_topic = work.get("primary_topic") or {}
    for key in ("display_name",):
        value = clean_text(primary_topic.get(key, "")) if isinstance(primary_topic, dict) else ""
        if value:
            topics.append(value)
    for nested_key in ("subfield", "field", "domain"):
        nested = primary_topic.get(nested_key, {}) if isinstance(primary_topic, dict) else {}
        if isinstance(nested, dict):
            value = clean_text(nested.get("display_name", ""))
            if value:
                topics.append(value)
    for item in work.get("concepts", [])[:6]:
        if isinstance(item, dict):
            score = item.get("score", 1)
            name = clean_text(item.get("display_name", ""))
            if name and score >= 0.2:
                topics.append(name)
    for item in work.get("keywords", [])[:6]:
        if isinstance(item, dict):
            name = clean_text(item.get("display_name") or item.get("keyword", ""))
        else:
            name = clean_text(str(item))
        if name:
            topics.append(name)
    title = clean_text(work.get("display_name") or work.get("title", ""))
    if title:
        topics.extend(extract_keywords(title, limit=8))
    return _filter_research_terms(topics, limit=10)


def _work_title(work: dict) -> str:
    return clean_text(work.get("display_name") or work.get("title", "") or "Untitled work")


def _work_year(work: dict) -> int:
    year = work.get("publication_year") or work.get("year") or 0
    return int(year) if isinstance(year, int) or (isinstance(year, str) and year.isdigit()) else 0


def _work_source_url(work: dict) -> str:
    primary_location = work.get("primary_location") or {}
    if isinstance(primary_location, dict):
        for key in ("landing_page_url", "pdf_url"):
            value = clean_text(primary_location.get(key, ""))
            if value:
                return value
        source = primary_location.get("source", {})
        if isinstance(source, dict):
            homepage = clean_text(source.get("homepage_url", ""))
            if homepage:
                return homepage
    ids = work.get("ids", {})
    if isinstance(ids, dict):
        openalex_url = clean_text(ids.get("openalex", ""))
        if openalex_url:
            return openalex_url
    return clean_text(work.get("id", ""))


def _author_role_weight(authorship: dict) -> float:
    position = clean_text(authorship.get("author_position", "")).lower()
    if position in {"first", "last"}:
        return 1.35
    if authorship.get("is_corresponding"):
        return 1.3
    if position == "middle":
        return 0.9
    return 1.0


def _region_matches(target_region: str, institution_name: str, country_code: str) -> bool:
    region = clean_text(target_region).lower()
    institution = clean_text(institution_name).lower()
    code = clean_text(country_code).lower()
    if not region:
        return False
    if any(token in region for token in ("united kingdom", "uk", "england", "scotland")):
        return code == "gb" or any(token in institution for token in ("united kingdom", "uk", "england", "scotland"))
    if any(token in region for token in ("united states", "usa", "us")):
        return code == "us" or "united states" in institution
    if "canada" in region:
        return code == "ca" or "canada" in institution
    if "europe" in region:
        return code in {"gb", "ie", "fr", "de", "nl", "be", "se", "no", "dk", "it", "es", "pt", "ch", "at", "fi"} or "europe" in institution
    return region in institution


def _extract_candidate_profile(
    *,
    resume_result: dict,
    interests_text: str,
    academic_stage: str,
    preferred_methods: list[str],
    existing_skills: str,
    opportunity_type: str,
    funding_required: bool,
) -> dict:
    resume_text = resume_result.get("text", "")
    resume_sections = resume_result.get("sections", {})
    education_text = resume_sections.get("education", "")
    normalized_profile = _normalize_topic_profile(
        interests_text=interests_text,
        resume_sections=resume_sections,
        existing_skills=existing_skills,
        preferred_methods=preferred_methods,
    )
    combined = "\n".join(
        [
            interests_text,
            resume_text,
            education_text,
            resume_sections.get("projects", ""),
            resume_sections.get("experience", ""),
            existing_skills,
        ]
    )
    interest_keywords = list(extract_keywords(interests_text, limit=12))
    topic_keywords = list(extract_keywords(combined, limit=20))
    methods = sorted(
        {
            method
            for method, patterns in METHOD_PATTERNS.items()
            if method in preferred_methods or any(pattern in combined.lower() for pattern in patterns)
        }
    )
    if preferred_methods:
        methods = sorted(set(methods).union(set(preferred_methods)))
    tools = list(extract_keywords(f"{resume_sections.get('skills', '')}\n{existing_skills}", limit=12))
    discipline_tags = _extract_discipline_tags("\n".join([interests_text, education_text, resume_sections.get("experience", ""), existing_skills]))
    research_exposure = []
    lowered = combined.lower()
    for signal, patterns in (
        ("Research experience", ("research", "research assistant", "lab")),
        ("Project work", ("project", "capstone", "thesis", "dissertation", "independent study")),
        ("Data analysis", ("analysis", "analytics", "model", "dashboard", "experiment", "causal", "regression")),
        ("Communication", ("presented", "stakeholder", "report", "wrote", "paper", "poster")),
    ):
        if any(term in lowered for term in patterns):
            research_exposure.append(signal)

    return {
        "name": _extract_resume_name(resume_text),
        "resume_text": resume_text,
        "resume_sections": resume_sections,
        "interest_keywords": sorted(interest_keywords),
        "topic_keywords": sorted(_filter_research_terms(list(topic_keywords), limit=18)),
        "interests_text": clean_text(interests_text),
        "methods": sorted(methods),
        "tools": sorted(_filter_research_terms(list(tools), limit=10)),
        "discipline_tags": discipline_tags,
        "research_exposure": research_exposure,
        "academic_stage": academic_stage,
        "opportunity_type": opportunity_type,
        "funding_required": funding_required,
        "interest_phrases": normalized_profile["interest_phrases"],
        "normalized_topics": normalized_profile["topic_terms"],
        "normalized_methods": normalized_profile["method_terms"],
        "normalized_tools": normalized_profile["tool_terms"],
    }


def _region_hints(region: str) -> tuple[str, str]:
    normalized = region.lower().strip()
    if not normalized:
        return "", ""
    if "united kingdom" in normalized or normalized in {"uk", "britain", "england", "scotland"}:
        return '"United Kingdom"', "site:.ac.uk"
    if "united states" in normalized or normalized in {"us", "usa"}:
        return '"United States"', "site:.edu"
    if "canada" in normalized:
        return '"Canada"', '"university"'
    if "europe" in normalized:
        return '"Europe"', '"university"'
    return f'"{region.strip()}"', '"university"'


def _stage_query_hint(stage: str) -> str:
    return {
        "Undergraduate": '"undergraduate research" "summer research"',
        "Master": '"master student" postgraduate research',
        "Pre-PhD": '"research assistant" predoctoral',
        "PhD interest": '"prospective students" phd',
        "Other": "",
    }.get(stage, "")


def _opportunity_query_hint(opportunity_type: str) -> str:
    return {
        "Summer research": '"summer research" "undergraduate research"',
        "RA / outreach": '"research assistant" "project assistant" "lab opening"',
        "Long-term research": '"research group" lab "join the lab"',
        "PhD interest": '"prospective students" phd "research group"',
    }.get(opportunity_type, '"research opportunity"')


def build_search_queries(candidate_profile: dict, filters: dict) -> list[str]:
    interest_phrases = _extract_interest_phrases(candidate_profile.get("interests_text", ""))
    interests = interest_phrases[:3] + (candidate_profile.get("interest_keywords", [])[:5] or candidate_profile["topic_keywords"][:5])
    secondary_terms = interest_phrases[3:5] + candidate_profile["topic_keywords"][5:10]
    methods = [method.lower() for method in (filters.get("preferred_methods", [])[:2] or candidate_profile.get("methods", [])[:2])]
    disciplines = [tag.lower() for tag in candidate_profile.get("discipline_tags", [])[:2]]
    tools = [tool.lower() for tool in candidate_profile.get("tools", [])[:2]]
    region_hint, domain_hint = _region_hints(filters.get("target_region", ""))
    stage_hint = _stage_query_hint(filters.get("academic_stage", "").strip())
    opportunity_hint = _opportunity_query_hint(filters.get("opportunity_type", "").strip())

    primary_terms = " ".join(_quote_if_phrase(term) for term in interests[:3] if clean_text(term))
    fallback_terms = " ".join(_quote_if_phrase(term) for term in interests[3:6] if clean_text(term))
    secondary_topic_terms = " ".join(_quote_if_phrase(term) for term in secondary_terms[:3] if clean_text(term))
    method_terms = " ".join(_quote_if_phrase(term) for term in methods)
    tool_terms = " ".join(_quote_if_phrase(term) for term in tools)
    discipline_terms = " ".join(_quote_if_phrase(term) for term in disciplines)
    base_topic_terms = primary_terms or fallback_terms or clean_text(candidate_profile["interests_text"])
    people_hint = "professor faculty researcher principal investigator"
    lab_hint = "lab research group laboratory"
    center_hint = "research center institute center"
    directory_hint = "faculty directory people staff profile"
    department_hint = "department school institute research"
    project_hint = "project research initiative publications"

    query_templates = [
        [base_topic_terms, people_hint, discipline_terms, region_hint, domain_hint],
        [base_topic_terms, lab_hint, method_terms, region_hint, domain_hint],
        [base_topic_terms, center_hint, region_hint, domain_hint],
        [base_topic_terms or discipline_terms, department_hint, region_hint, domain_hint],
        [discipline_terms or base_topic_terms, directory_hint, region_hint, domain_hint],
        [base_topic_terms, tool_terms, lab_hint, region_hint, domain_hint],
        [secondary_topic_terms or base_topic_terms, project_hint, method_terms, region_hint, domain_hint],
        [base_topic_terms, stage_hint, lab_hint, region_hint, domain_hint],
        [base_topic_terms, opportunity_hint, region_hint, domain_hint],
        [discipline_terms or base_topic_terms, "university research program group", stage_hint, region_hint, domain_hint],
        [base_topic_terms, "summer undergraduate research lab project", region_hint, domain_hint],
        [base_topic_terms, "industry research lab scientist group", method_terms, region_hint],
    ]

    queries = [
        clean_text(" ".join(part for part in parts if clean_text(part)))
        for parts in query_templates
        if clean_text(" ".join(part for part in parts if clean_text(part)))
    ]
    cleaned_queries = sorted(dict.fromkeys(queries))
    return cleaned_queries[:12]


def _classify_page_type(url: str, title: str, snippet: str = "", text: str = "") -> str:
    path = urlparse(url).path.lower()
    haystack = clean_text(" ".join([path, title, snippet, text[:1600]])).lower()
    title_primary = clean_text(re.split(r"[\-|–|:|·|\|]+", clean_text(title))[0]) if title else ""
    person_like_title = _looks_like_person_name(title_primary)
    explicit_opportunity_terms = (
        "summer research",
        "undergraduate research",
        "research opportunity",
        "research opportunities",
        "assistantship",
        "predoctoral",
        "pre-doctoral",
        "studentship",
        "internship",
        "opening",
        "openings",
        "vacancy",
        "vacancies",
        "join the lab",
        "join our group",
        "prospective students",
        "how to apply",
        "apply now",
    )
    directory_like = any(
        token in haystack
        for token in (
            "staff members",
            "research staff",
            "faculty members",
            "team members",
            "people",
            "directory",
            "members",
            "staff",
            "team",
        )
    )
    if any(hint in haystack for hint in explicit_opportunity_terms) or (
        "research assistant" in haystack and not any(token in haystack for token in ("professor", "faculty", "staff members", "research staff"))
    ):
        return "opportunity_page"
    if (any(hint in path for hint in DIRECTORY_PATH_HINTS) or directory_like) and not person_like_title:
        return "directory_page"
    if any(hint in path for hint in FACULTY_PATH_HINTS) or any(token in title.lower() for token in ("professor", "faculty profile", "staff profile", "profile")):
        return "faculty_profile"
    if person_like_title and any(token in haystack for token in ("professor", "faculty", "department", "research interests", "biography", "bio")):
        return "faculty_profile"
    if any(hint in path for hint in CENTER_PATH_HINTS) or any(token in haystack for token in ("research center", "research centre", "center for", "centre for")):
        return "center_page"
    if any(hint in path for hint in LAB_PATH_HINTS) or any(token in haystack for token in ("lab", "laboratory", "research group")):
        return "lab_page"
    if any(hint in path for hint in DIRECTORY_PATH_HINTS) or "directory" in haystack:
        return "directory_page"
    if any(hint in path for hint in DEPARTMENT_PATH_HINTS) or any(token in haystack for token in ("department of", "school of", "faculty of", "institute of")):
        return "department_page"
    if any(token in haystack for token in PROJECT_HINTS):
        return "project_page"
    if any(token in haystack for token in PUBLICATION_HINTS):
        return "publication_page"
    return "other"


def _search_result_relevance(result: dict[str, str], candidate_profile: dict) -> int:
    haystack = clean_text(" ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")])).lower()
    tokens = (
        candidate_profile.get("interest_keywords", [])[:6]
        + candidate_profile.get("discipline_tags", [])[:3]
        + candidate_profile.get("methods", [])[:2]
        + candidate_profile.get("tools", [])[:2]
    )
    overlap_score = sum(1 for token in tokens if token and token.lower() in haystack)
    page_type = result.get("source_type") or _classify_page_type(result.get("url", ""), result.get("title", ""), result.get("snippet", ""))
    research_context_bonus = sum(
        1 for token in ("professor", "faculty", "lab", "research group", "center", "centre", "department", "project")
        if token in haystack
    )
    return overlap_score + research_context_bonus + max(0, 7 - PAGE_TYPE_PRIORITY.get(page_type, 9))


def _looks_like_research_result(result: dict[str, str], candidate_profile: dict) -> bool:
    url = result.get("url", "")
    title = result.get("title", "")
    snippet = result.get("snippet", "")
    domain = canonical_domain(url)
    page_type = result.get("source_type") or _classify_page_type(url, title, snippet)
    haystack = clean_text(f"{title} {snippet} {url}").lower()
    if not url or domain in BLOCKED_RESULT_DOMAINS or not _looks_trustworthy_research_result(url, title, snippet):
        return False
    if page_type != "other":
        return True
    topic_tokens = candidate_profile.get("interest_keywords", [])[:4] or candidate_profile.get("topic_keywords", [])[:4]
    if any(token in haystack for token in topic_tokens):
        return True
    return any(token in haystack for token in ("research", "lab", "group", "center", "centre", "faculty", "department", "institute"))


def _select_trusted_results(raw_results: list[dict[str, str]], limit: int = 28) -> list[dict[str, str]]:
    selected: list[dict[str, str]] = []
    selected_urls: set[str] = set()
    type_limits = {
        "faculty_profile": 10,
        "lab_page": 7,
        "center_page": 5,
        "opportunity_page": 5,
        "department_page": 5,
        "directory_page": 4,
        "project_page": 4,
        "publication_page": 3,
        "other": 4,
    }
    counts: Counter[str] = Counter()

    for result in raw_results:
        normalized_url = _normalized_result_url(result.get("url", ""))
        page_type = result.get("source_type", "other")
        if not normalized_url or normalized_url in selected_urls:
            continue
        if counts[page_type] >= type_limits.get(page_type, 3):
            continue
        selected.append(result)
        selected_urls.add(normalized_url)
        counts[page_type] += 1
        if len(selected) >= limit:
            return selected

    for result in raw_results:
        normalized_url = _normalized_result_url(result.get("url", ""))
        if not normalized_url or normalized_url in selected_urls:
            continue
        selected.append(result)
        selected_urls.add(normalized_url)
        if len(selected) >= limit:
            break
    return selected


def _merge_ordered_unique(primary: list[str], secondary: list[str], limit: int = 8) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for value in primary + secondary:
        cleaned = clean_text(value)
        if not cleaned or cleaned in seen:
            continue
        ordered.append(cleaned)
        seen.add(cleaned)
        if len(ordered) >= limit:
            break
    return ordered


def _dominant_counter_key(counter: Counter[str], fallback: str = "") -> str:
    if not counter:
        return fallback
    return sorted(counter.items(), key=lambda item: (-item[1], item[0].lower()))[0][0]


def _build_scholarly_profile_text(candidate: dict) -> str:
    return clean_text(
        " ".join(
            candidate.get("research_tags", [])
            + candidate.get("discipline_tags", [])
            + candidate.get("recent_topics", [])
            + candidate.get("publications", [])
            + ([candidate.get("university", "")] if candidate.get("university") else [])
            + ([candidate.get("department_or_lab", "")] if candidate.get("department_or_lab") else [])
        )
    )


def _build_scholarly_candidates(candidate_profile: dict) -> tuple[list[dict], dict[str, int], list[str]]:
    scholarly_queries = _build_scholarly_queries(candidate_profile)
    works_by_id: dict[str, dict] = {}
    author_buckets: dict[str, dict] = {}
    institution_buckets: dict[str, dict] = {}

    for query in scholarly_queries:
        for work in search_openalex_works(query, per_page=12):
            work_id = clean_text(work.get("id", "")) or _work_title(work)
            if not work_id:
                continue
            if work_id not in works_by_id:
                works_by_id[work_id] = {**work, "_matched_queries": [query]}
            else:
                works_by_id[work_id].setdefault("_matched_queries", []).append(query)

    for work in works_by_id.values():
        title = _work_title(work)
        topics = _extract_work_topics(work)
        year = _work_year(work)
        source_url = _work_source_url(work)
        work_text = clean_text(" ".join([title] + topics))
        work_disciplines = _extract_discipline_tags(work_text)
        institutions_in_work: list[tuple[str, str]] = []

        for authorship in work.get("authorships", [])[:10]:
            if not isinstance(authorship, dict):
                continue
            author = authorship.get("author", {}) if isinstance(authorship.get("author"), dict) else {}
            name = clean_text(author.get("display_name") or authorship.get("raw_author_name", ""))
            if not name or not _looks_like_person_name(name):
                continue

            institution_entries = authorship.get("institutions", []) if isinstance(authorship.get("institutions"), list) else []
            institution_name = ""
            country_code = ""
            if institution_entries:
                first_inst = institution_entries[0] if isinstance(institution_entries[0], dict) else {}
                institution_name = clean_text(first_inst.get("display_name", ""))
                country_code = clean_text(first_inst.get("country_code", ""))
                if institution_name:
                    institutions_in_work.append((institution_name, country_code))

            author_id = clean_text(author.get("id", "")) or f"{name.lower()}|{institution_name.lower()}"
            bucket = author_buckets.setdefault(
                author_id,
                {
                    "name": name,
                    "author_id": clean_text(author.get("id", "")),
                    "institutions": Counter(),
                    "countries": Counter(),
                    "topic_counts": Counter(),
                    "discipline_counts": Counter(),
                    "publications": [],
                    "recent_topics": [],
                    "years": [],
                    "source_urls": [],
                    "weight": 0.0,
                    "matched_queries": set(),
                },
            )
            if institution_name:
                bucket["institutions"][institution_name] += 1
            if country_code:
                bucket["countries"][country_code] += 1
            for topic in topics:
                bucket["topic_counts"][topic] += 1
            for discipline in work_disciplines:
                bucket["discipline_counts"][discipline] += 1
            if title and title not in bucket["publications"]:
                bucket["publications"].append(title)
            for topic in topics[:4]:
                if topic not in bucket["recent_topics"]:
                    bucket["recent_topics"].append(topic)
            if year:
                bucket["years"].append(year)
            if source_url and source_url not in bucket["source_urls"]:
                bucket["source_urls"].append(source_url)
            bucket["weight"] += _author_role_weight(authorship)
            bucket["matched_queries"].update(work.get("_matched_queries", []))

        for institution_name, country_code in institutions_in_work:
            institution_bucket = institution_buckets.setdefault(
                institution_name,
                {
                    "name": institution_name,
                    "countries": Counter(),
                    "topic_counts": Counter(),
                    "discipline_counts": Counter(),
                    "publications": [],
                    "source_urls": [],
                    "years": [],
                },
            )
            if country_code:
                institution_bucket["countries"][country_code] += 1
            for topic in topics:
                institution_bucket["topic_counts"][topic] += 1
            for discipline in work_disciplines:
                institution_bucket["discipline_counts"][discipline] += 1
            if title and title not in institution_bucket["publications"]:
                institution_bucket["publications"].append(title)
            if source_url and source_url not in institution_bucket["source_urls"]:
                institution_bucket["source_urls"].append(source_url)
            if year:
                institution_bucket["years"].append(year)

    scholarly_candidates: list[dict] = []
    for bucket in author_buckets.values():
        institution_name = _dominant_counter_key(bucket["institutions"], "Institution not clearly identified")
        country_code = _dominant_counter_key(bucket["countries"], "")
        research_tags = [topic for topic, _count in bucket["topic_counts"].most_common(8)]
        discipline_tags = [topic for topic, _count in bucket["discipline_counts"].most_common(4)] or _extract_discipline_tags(" ".join(research_tags + [institution_name]))
        recent_years = sorted({year for year in bucket["years"] if year}, reverse=True)
        activity_signals = []
        if recent_years:
            activity_signals.append(f"Recent publication activity is visible through {', '.join(str(year) for year in recent_years[:2])}.")
        if _region_matches(candidate_profile.get("target_region", ""), institution_name, country_code):
            activity_signals.append("The institution aligns with the selected target region.")
        source_urls = [url for url in bucket["source_urls"] if url]
        scholarly_profile_url = source_urls[0] if source_urls else clean_text(bucket.get("author_id", ""))
        candidate = {
            "name": bucket["name"],
            "entity_type": "Researcher",
            "lead_contact_name": bucket["name"],
            "university": institution_name,
            "department_or_lab": _dominant_counter_key(Counter(discipline_tags), "Scholarly research profile"),
            "primary_source_url": scholarly_profile_url,
            "scholarly_profile_url": scholarly_profile_url,
            "official_profile_url": "",
            "department_page_url": "",
            "opportunity_page_url": "",
            "official_email": "",
            "email_source": "",
            "opportunity_type": "Scholarly outreach",
            "page_type": "scholarly_profile",
            "page_type_label": PAGE_TYPE_LABELS["scholarly_profile"],
            "research_tags": research_tags[:8],
            "discipline_tags": discipline_tags[:4],
            "publications": bucket["publications"][:3],
            "project_signals": [],
            "recent_topics": _merge_ordered_unique(bucket["recent_topics"], research_tags, limit=4),
            "student_signals": [],
            "opportunity_signals": [],
            "activity_signals": activity_signals[:3],
            "academic_background": [],
            "profile_signal_count": sum(
                [
                    bool(research_tags),
                    bool(discipline_tags),
                    bool(bucket["publications"]),
                    bool(institution_name),
                    bool(source_urls),
                ]
            ),
            "source_types": [OPENALEX_SOURCE_LABEL, "Institution affiliation", "Publication evidence"],
            "profile_text": clean_text(" ".join(research_tags + discipline_tags + bucket["publications"][:4] + [institution_name])),
            "raw_text_excerpt": clean_text(" ".join(bucket["publications"][:4])),
            "scholarly_work_count": len(bucket["publications"]),
            "scholarly_query_hits": len(bucket["matched_queries"]),
            "target_region_match": _region_matches(candidate_profile.get("target_region", ""), institution_name, country_code),
            "country_code": country_code,
        }
        candidate["source_summary"] = _summarize_source_types(candidate)
        scholarly_candidates.append(candidate)

    if len(scholarly_candidates) < 3:
        for institution_name, bucket in sorted(
            institution_buckets.items(),
            key=lambda item: (-len(item[1]["publications"]), item[0].lower()),
        )[:3]:
            discipline_tags = [topic for topic, _count in bucket["discipline_counts"].most_common(4)]
            research_tags = [topic for topic, _count in bucket["topic_counts"].most_common(8)]
            candidate = {
                "name": institution_name,
                "entity_type": "Research institution",
                "lead_contact_name": "",
                "university": institution_name,
                "department_or_lab": _dominant_counter_key(Counter(discipline_tags), "Institution-linked research cluster"),
                "primary_source_url": bucket["source_urls"][0] if bucket["source_urls"] else "",
                "scholarly_profile_url": bucket["source_urls"][0] if bucket["source_urls"] else "",
                "official_profile_url": "",
                "department_page_url": "",
                "opportunity_page_url": "",
                "official_email": "",
                "email_source": "",
                "opportunity_type": "Institution-linked research target",
                "page_type": "scholarly_profile",
                "page_type_label": PAGE_TYPE_LABELS["scholarly_profile"],
                "research_tags": research_tags[:8],
                "discipline_tags": discipline_tags[:4],
                "publications": bucket["publications"][:3],
                "project_signals": [],
                "recent_topics": _merge_ordered_unique(bucket["publications"][:2], research_tags, limit=4),
                "student_signals": [],
                "opportunity_signals": [],
                "activity_signals": [],
                "academic_background": [],
                "profile_signal_count": 3 if bucket["publications"] else 2,
                "source_types": [OPENALEX_SOURCE_LABEL, "Institution affiliation", "Publication evidence"],
                "profile_text": clean_text(" ".join(research_tags + discipline_tags + bucket["publications"][:4] + [institution_name])),
                "raw_text_excerpt": clean_text(" ".join(bucket["publications"][:4])),
                "scholarly_work_count": len(bucket["publications"]),
                "scholarly_query_hits": 1,
                "target_region_match": _region_matches(
                    candidate_profile.get("target_region", ""),
                    institution_name,
                    _dominant_counter_key(bucket["countries"], ""),
                ),
                "country_code": _dominant_counter_key(bucket["countries"], ""),
            }
            candidate["source_summary"] = _summarize_source_types(candidate)
            scholarly_candidates.append(candidate)
            if len(scholarly_candidates) >= 6:
                break

    counts = {
        "scholarly_work_count": len(works_by_id),
        "scholarly_candidate_count": len(author_buckets),
        "institution_count": len(institution_buckets),
        "publication_backed_candidate_count": sum(1 for candidate in scholarly_candidates if candidate.get("publications")),
    }
    return scholarly_candidates, counts, scholarly_queries


def _build_official_enrichment_queries(candidate: dict) -> list[str]:
    name = clean_text(candidate.get("lead_contact_name") or candidate.get("name", ""))
    university = clean_text(candidate.get("university", ""))
    tags = candidate.get("research_tags", [])[:2]
    if candidate.get("entity_type") == "Research institution":
        base = _quote_if_phrase(candidate.get("name", ""))
        return [
            clean_text(f"{base} research group {university}"),
            clean_text(f"{base} faculty people {university}"),
        ]
    return [
        clean_text(f'{_quote_if_phrase(name)} {_quote_if_phrase(university)} faculty research'),
        clean_text(f'{_quote_if_phrase(name)} {_quote_if_phrase(university)} {" ".join(_quote_if_phrase(tag) for tag in tags)}'),
        clean_text(f'{_quote_if_phrase(name)} {_quote_if_phrase(university)} lab group'),
    ]


def _result_matches_candidate(result: dict[str, str], candidate: dict) -> bool:
    haystack = clean_text(" ".join([result.get("title", ""), result.get("snippet", ""), result.get("url", "")])).lower()
    university = clean_text(candidate.get("university", "")).lower()
    if candidate.get("entity_type") == "Research institution":
        return bool(university and university in haystack)
    name = clean_text(candidate.get("lead_contact_name") or candidate.get("name", "")).lower()
    name_tokens = [token for token in re.findall(r"[a-z]{3,}", name) if token not in GENERIC_NAME_WORDS]
    if not name_tokens:
        return False
    last_name = name_tokens[-1]
    if last_name not in haystack:
        return False
    if university and university in haystack:
        return True
    return any(tag in haystack for tag in candidate.get("research_tags", [])[:2]) or "faculty" in haystack or "professor" in haystack


def _merge_candidate_enrichment(base_candidate: dict, enriched: dict | None) -> dict:
    if not enriched:
        candidate = {**base_candidate}
        candidate["source_types"] = list(dict.fromkeys(candidate.get("source_types", []) + [OPENALEX_SOURCE_LABEL]))
        candidate["source_summary"] = _summarize_source_types(candidate)
        return candidate

    candidate = {**base_candidate}
    candidate["entity_type"] = enriched.get("entity_type") or base_candidate.get("entity_type", "Researcher")
    candidate["lead_contact_name"] = enriched.get("lead_contact_name") or base_candidate.get("lead_contact_name", "")
    if candidate["entity_type"] == "Professor":
        candidate["name"] = candidate["lead_contact_name"] or enriched.get("name") or base_candidate.get("name", "")
    candidate["official_profile_url"] = enriched.get("official_profile_url", "")
    candidate["primary_source_url"] = enriched.get("official_profile_url") or base_candidate.get("primary_source_url", "")
    candidate["department_page_url"] = enriched.get("department_page_url", "")
    candidate["opportunity_page_url"] = enriched.get("opportunity_page_url", "")
    candidate["official_email"] = enriched.get("official_email", "")
    candidate["email_source"] = enriched.get("email_source", "")
    candidate["opportunity_type"] = enriched.get("opportunity_type") or base_candidate.get("opportunity_type", "Scholarly outreach")
    candidate["page_type"] = enriched.get("page_type") or base_candidate.get("page_type", "scholarly_profile")
    candidate["page_type_label"] = PAGE_TYPE_LABELS.get(candidate["page_type"], "Research profile")
    candidate["department_or_lab"] = (
        enriched.get("department_or_lab")
        if enriched.get("department_or_lab") and enriched.get("department_or_lab") != "Official research context"
        else base_candidate.get("department_or_lab", "Scholarly research profile")
    )
    candidate["research_tags"] = _merge_ordered_unique(
        enriched.get("research_tags", []),
        base_candidate.get("research_tags", []),
        limit=8,
    )
    candidate["discipline_tags"] = _merge_ordered_unique(
        enriched.get("discipline_tags", []),
        base_candidate.get("discipline_tags", []),
        limit=4,
    )
    candidate["publications"] = _merge_ordered_unique(
        base_candidate.get("publications", []),
        enriched.get("publications", []),
        limit=3,
    )
    candidate["project_signals"] = _merge_ordered_unique(enriched.get("project_signals", []), base_candidate.get("project_signals", []), limit=3)
    candidate["recent_topics"] = _merge_ordered_unique(
        enriched.get("recent_topics", []),
        base_candidate.get("recent_topics", []),
        limit=4,
    )
    candidate["student_signals"] = _merge_ordered_unique(enriched.get("student_signals", []), base_candidate.get("student_signals", []), limit=3)
    candidate["opportunity_signals"] = _merge_ordered_unique(enriched.get("opportunity_signals", []), base_candidate.get("opportunity_signals", []), limit=4)
    candidate["activity_signals"] = _merge_ordered_unique(enriched.get("activity_signals", []), base_candidate.get("activity_signals", []), limit=3)
    candidate["academic_background"] = _merge_ordered_unique(enriched.get("academic_background", []), base_candidate.get("academic_background", []), limit=2)
    candidate["source_types"] = list(
        dict.fromkeys(
            base_candidate.get("source_types", [])
            + [OPENALEX_SOURCE_LABEL]
            + enriched.get("source_types", [])
            + (["Official enrichment"] if enriched.get("official_profile_url") else [])
        )
    )
    candidate["profile_text"] = clean_text(" ".join([base_candidate.get("profile_text", ""), enriched.get("profile_text", "")]))
    candidate["raw_text_excerpt"] = enriched.get("raw_text_excerpt", "") or base_candidate.get("raw_text_excerpt", "")
    candidate["profile_signal_count"] = max(base_candidate.get("profile_signal_count", 0), enriched.get("profile_signal_count", 0)) + int(
        bool(enriched.get("official_profile_url"))
    )
    candidate["official_enrichment_found"] = bool(enriched.get("official_profile_url"))
    candidate["source_summary"] = _summarize_source_types(candidate)
    return candidate


def _enrich_scholarly_candidates(candidates: list[dict], candidate_profile: dict) -> tuple[list[dict], Counter[str], int]:
    enriched_candidates: list[dict] = []
    official_source_counts: Counter[str] = Counter()
    official_enrichment_count = 0

    for candidate in candidates:
        best_enrichment: dict | None = None
        best_score = -1
        for query in _build_official_enrichment_queries(candidate):
            if not clean_text(query):
                continue
            for result in search_duckduckgo_html(query, max_results=6):
                if not _looks_trustworthy_research_result(result.get("url", ""), result.get("title", ""), result.get("snippet", "")):
                    continue
                if not _result_matches_candidate(result, candidate):
                    continue
                parsed = _parse_research_page(
                    {
                        **result,
                        "source_type": _classify_page_type(result.get("url", ""), result.get("title", ""), result.get("snippet", "")),
                    }
                )
                if not parsed:
                    continue
                score = 0
                if parsed.get("entity_type") == "Professor":
                    score += 4
                if parsed.get("official_email"):
                    score += 3
                if candidate.get("university") and candidate.get("university", "").lower() in clean_text(
                    f"{parsed.get('university', '')} {parsed.get('department_or_lab', '')}"
                ).lower():
                    score += 2
                score += max(0, 4 - PAGE_TYPE_PRIORITY.get(parsed.get("page_type", "other"), 9))
                if score > best_score:
                    best_score = score
                    best_enrichment = parsed
        merged = _merge_candidate_enrichment(candidate, best_enrichment)
        if best_enrichment and best_enrichment.get("official_profile_url"):
            official_enrichment_count += 1
            official_source_counts[best_enrichment.get("page_type", "other")] += 1
        enriched_candidates.append(merged)

    return enriched_candidates, official_source_counts, official_enrichment_count


def _extract_heading_sections(soup: BeautifulSoup) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    for heading_tag in soup.find_all(re.compile(r"^h[1-4]$")):
        heading = clean_text(heading_tag.get_text(" ", strip=True))
        if not heading:
            continue
        content_lines: list[str] = []
        for sibling in heading_tag.find_next_siblings():
            if sibling.name and re.fullmatch(r"h[1-4]", sibling.name.lower()):
                break
            if sibling.name in {"script", "style", "nav", "footer", "header", "noscript", "svg", "form"}:
                continue
            text = clean_text(sibling.get_text(" ", strip=True))
            if text:
                content_lines.append(text)
        sections.append((heading, clean_text("\n".join(content_lines))))
    return sections


def _guess_page_heading(soup: BeautifulSoup, page_title: str) -> str:
    for selector in ("h1", "h2"):
        tag = soup.select_one(selector)
        if tag:
            text = clean_text(tag.get_text(" ", strip=True))
            if text:
                return text
    title = clean_text(page_title)
    for part in re.split(r"[\-|–|:|·|\|]+", title):
        cleaned = clean_text(part)
        if cleaned:
            return cleaned
    return title or "Research page"


def _guess_professor_name(soup: BeautifulSoup, page_title: str) -> str:
    for selector in ("h1", "h2"):
        tag = soup.select_one(selector)
        if tag:
            text = _normalize_person_name(tag.get_text(" ", strip=True))
            if _looks_like_person_name(text):
                return text
    title = clean_text(page_title)
    for part in re.split(r"[\-|–|:|·|\|]+", title):
        cleaned = _normalize_person_name(part)
        if _looks_like_person_name(cleaned):
            return cleaned
    return "Professor profile"


def _guess_university(url: str, page_title: str) -> str:
    title = clean_text(page_title)
    for part in re.split(r"[\-|–|:|·|\|]+", title):
        cleaned = clean_text(part)
        if any(token in cleaned.lower() for token in ("university", "college", "institute", "school")):
            return cleaned
    domain = canonical_domain(url)
    pieces = [piece for piece in re.split(r"[.\-]", domain) if piece and piece not in {"www", "edu", "ac", "uk"}]
    return " ".join(piece.capitalize() for piece in pieces[:3]) or domain


def _guess_department(sections: list[tuple[str, str]], text: str, page_heading: str) -> str:
    for heading, content in sections:
        combined = f"{heading} {content}".lower()
        match = re.search(r"(department of [a-z&,\- ]+)", combined, flags=re.IGNORECASE)
        if match:
            return clean_text(match.group(1))
    for source in (page_heading, text):
        match = re.search(r"(department of [A-Za-z&,\- ]+)", source)
        if match:
            return clean_text(match.group(1))
    if any(token in page_heading.lower() for token in ("lab", "group", "center", "centre", "institute")):
        return clean_text(page_heading)
    if any(token in text.lower() for token in ("lab", "group", "center", "centre", "institute")):
        for sentence in split_sentences(text)[:12]:
            if any(token in sentence.lower() for token in ("lab", "group", "center", "centre", "institute")):
                return clean_text(sentence[:110])
    return "Official research context"


def _guess_role_title(block_text: str, name: str = "") -> str:
    lines = [clean_text(line) for line in re.split(r"[\n|]+", block_text) if clean_text(line)]
    cleaned_name = clean_text(name)
    for line in lines[:8]:
        lowered = line.lower()
        if cleaned_name and cleaned_name.lower() in lowered and len(lines) > 1:
            continue
        if _looks_like_field_label(line):
            continue
        if any(hint in lowered for hint in ROLE_TITLE_HINTS) or any(hint in line for hint in CHINESE_ROLE_HINTS):
            return line[:120]
    for sentence in split_sentences(block_text)[:6]:
        lowered = sentence.lower()
        if cleaned_name and cleaned_name.lower() in lowered:
            continue
        if _looks_like_field_label(sentence):
            continue
        if any(hint in lowered for hint in ROLE_TITLE_HINTS) or any(hint in sentence for hint in CHINESE_ROLE_HINTS):
            return sentence[:140]
    return ""


def _best_candidate_container(node: BeautifulSoup) -> BeautifulSoup:
    fallback = node
    best = node
    best_score = -999
    for parent in node.parents:
        tag_name = getattr(parent, "name", "") or ""
        if tag_name not in {"li", "article", "tr", "div", "section", "td", "dd"}:
            continue
        text = clean_text(parent.get_text("\n", strip=True))
        word_count = len(text.split())
        if word_count < 3 or word_count > 220:
            continue
        score = 0
        if 8 <= word_count <= 90:
            score += 5
        elif word_count <= 140:
            score += 3
        if any(hint in text.lower() for hint in ROLE_TITLE_HINTS):
            score += 2
        email_count = len(_extract_all_emails(text))
        if email_count == 1:
            score += 2
        elif email_count > 1:
            score -= 3
        person_anchor_count = sum(
            1
            for link in parent.find_all("a", href=True)[:12]
            if _looks_like_person_name(clean_text(link.get_text(" ", strip=True)))
        )
        if person_anchor_count > 1:
            score -= 4
        if score > best_score:
            best_score = score
            best = parent
        fallback = parent
    return best or fallback


def _find_mailto_email(soup: BeautifulSoup, page_domain: str) -> tuple[str, str]:
    source_domain = page_domain.replace("www.", "")
    emails = _extract_emails_from_node(soup, source_domain, allow_any_visible=True)
    if not emails:
        return "", ""
    preferred = [email for email in emails if _same_domain_family(canonical_domain(f"https://{email.split('@')[-1]}"), source_domain)]
    if preferred:
        return preferred[0], "Official page mailto link" if any(link.get("href", "").startswith("mailto:") and preferred[0] in link.get("href", "") for link in soup.select("a[href^='mailto:']")) else "Official page visible text"
    return emails[0], "Visible email on the provided page"


def _find_related_page(soup: BeautifulSoup, base_url: str, keywords: tuple[str, ...]) -> str:
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        text = clean_text(link.get_text(" ", strip=True)).lower()
        if any(keyword in text for keyword in keywords):
            return urljoin(base_url, href)
    return ""


def _extract_related_candidate_links(soup: BeautifulSoup, base_url: str, page_type: str) -> list[dict[str, str]]:
    if page_type not in CONTEXT_EXPANSION_PAGE_TYPES:
        return []

    base_domain = canonical_domain(base_url)
    candidates: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link.get("href", "").strip())
        normalized_url = _normalized_result_url(href)
        anchor_text = clean_text(link.get_text(" ", strip=True))
        link_domain = canonical_domain(href)
        if not href or normalized_url in seen_urls:
            continue
        if not _same_domain_family(base_domain, link_domain):
            continue
        if not _looks_trustworthy_research_result(href, anchor_text, ""):
            continue
        lowered_anchor = anchor_text.lower()
        link_type = _classify_page_type(href, anchor_text, anchor_text)
        person_like = _looks_like_person_name(anchor_text)
        has_profile_hint = any(hint in urlparse(href).path.lower() for hint in FACULTY_PATH_HINTS + DIRECTORY_PATH_HINTS)
        has_context_hint = any(token in lowered_anchor for token in ("professor", "faculty", "research group", "lab", "center", "centre", "institute"))
        if not (link_type != "other" or person_like or has_profile_hint or has_context_hint):
            continue
        if link_type == "other" and person_like:
            link_type = "faculty_profile"
        candidates.append(
            {
                "title": anchor_text or PAGE_TYPE_LABELS.get(link_type, "Research page"),
                "url": href,
                "snippet": "",
                "source_type": link_type,
            }
        )
        seen_urls.add(normalized_url)
        if len(candidates) >= 8:
            break
    return candidates


def _candidate_display_name(node: BeautifulSoup) -> str:
    explicit_text = clean_text(node.get_text("\n", strip=True))
    for pattern in (
        re.compile(r"(?:^|[\n ])(?:Name|姓名)[:：]\s*([^\n]+)", flags=re.IGNORECASE),
        re.compile(r"(?:^|[\n ])(?:Professor|Prof\.?|Dr\.?)\s+([A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){0,3})"),
        re.compile(r"\b([A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){1,2})(?=\s+(?:Research|Assistant|Associate|Professor|Postdoctoral|Scientist|Fellow|Tel|Email|Office)\b)"),
    ):
        match = pattern.search(explicit_text[:800])
        if match:
            candidate = _normalize_person_name(match.group(1))
            if _looks_like_person_name(candidate) and not _looks_like_container_label(candidate):
                return candidate
    chinese_names = re.findall(r"[\u4e00-\u9fff]{2,4}", explicit_text[:600])
    for candidate in chinese_names:
        normalized = _normalize_person_name(candidate)
        if _looks_like_person_name(normalized) and not _looks_like_container_label(normalized):
            return normalized
    for selector in ("h1", "h2", "h3", "h4", "strong", "b", "a", "dt", "th", "td", "span", "p"):
        for tag in node.select(selector):
            text = _normalize_person_name(tag.get_text(" ", strip=True))
            if _looks_like_person_name(text) and not _looks_like_container_label(text):
                return text
    lines = [clean_text(line) for line in re.split(r"[\n\r]+", explicit_text) if clean_text(line)]
    for line in lines[:10]:
        candidate = _normalize_person_name(line)
        if _looks_like_person_name(candidate) and not _looks_like_container_label(candidate):
            return candidate
    text = clean_text(node.get_text(" ", strip=True))
    for pattern in (
        re.compile(r"\b(?:Professor|Prof\.?|Dr\.?)\s+([A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){0,3})"),
        re.compile(r"\b([A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){1,3})\b"),
    ):
        for match in pattern.findall(text[:300]):
            candidate = _normalize_person_name(match)
            if _looks_like_person_name(candidate) and not _looks_like_container_label(candidate):
                return candidate
    return ""


def _local_profile_link_for_name(node: BeautifulSoup, base_url: str, name: str) -> str:
    name_lower = clean_text(name).lower()
    name_tokens = _name_tokens(name)
    best_url = ""
    for link in node.find_all("a", href=True):
        href = urljoin(base_url, link.get("href", "").strip())
        anchor = clean_text(link.get_text(" ", strip=True))
        if not href or href.startswith("mailto:"):
            continue
        if name_lower and name_lower in anchor.lower():
            return href
        path = urlparse(href).path.lower()
        if name_tokens and all(token in path for token in name_tokens[-2:]):
            return href
        if _looks_like_person_name(anchor) and _names_compatible(name, anchor):
            best_url = href
    return best_url


def _extract_block_topics(block_text: str, page_context: dict) -> tuple[list[str], list[str], list[str]]:
    local_keywords = _extract_research_tags(block_text)
    discipline_tags = _extract_discipline_tags(block_text)
    publications = []
    for sentence in split_sentences(block_text)[:8]:
        lowered = sentence.lower()
        if any(token in lowered for token in PUBLICATION_HINTS + PROJECT_HINTS) or re.search(r"\b20(2[0-9]|3[0-1])\b", sentence):
            publications.append(clean_text(sentence))
        if len(publications) >= 3:
            break
    recent_topics = _extract_recent_topics(publications, [], local_keywords or page_context.get("research_tags", []))
    return local_keywords[:6], discipline_tags[:4], recent_topics[:4]


def _build_candidate_from_block(block: BeautifulSoup, base_url: str, page_context: dict, forced_name: str = "") -> dict | None:
    block_text = clean_text(block.get_text("\n", strip=True))
    if len(block_text.split()) < 4:
        return None
    page_domain = canonical_domain(base_url)
    emails = _extract_emails_from_node(block, page_domain, allow_any_visible=True) or _regex_detect_emails(block_text)
    profile_url = _local_profile_link_for_name(block, base_url, _normalize_person_name(forced_name) or _candidate_display_name(block))
    judgment = _judge_research_block(
        block_text=block_text,
        page_context=page_context,
        forced_name=forced_name,
        name_hint=_candidate_display_name(block),
        local_emails=emails,
        profile_url=profile_url,
    )
    if not judgment.get("is_human_candidate"):
        return None
    name = judgment.get("person_name", "")
    email = judgment.get("email", "")
    email_source = judgment.get("email_source", "")
    role_title = judgment.get("title", "") or _guess_role_title(block_text, name)
    profile_url = _local_profile_link_for_name(block, base_url, name)
    research_tags, discipline_tags, recent_topics = _extract_block_topics(block_text, page_context)
    research_areas = _merge_ordered_unique(judgment.get("research_areas", []), research_tags, limit=8)
    research_interests = _merge_ordered_unique(judgment.get("research_interests", []), recent_topics, limit=6)
    source_credibility_label = page_context.get("source_credibility_label", "Limited")
    source_credibility_detail = page_context.get("source_credibility_detail", "The candidate was extracted from the provided source page.")
    candidate = {
        "name": name,
        "entity_type": "Professor" if any(token in role_title.lower() for token in ("professor", "faculty", "lecturer", "scientist", "fellow", "researcher")) else "Researcher",
        "lead_contact_name": name,
        "role_title": role_title or "Role not clearly labeled on the source page",
        "university": page_context.get("university", "Institution not clearly identified"),
        "department_or_lab": page_context.get("department_or_lab", "Research context from source page"),
        "primary_source_url": base_url,
        "scholarly_profile_url": "",
        "official_profile_url": profile_url if profile_url and profile_url != base_url else "",
        "department_page_url": page_context.get("department_page_url", ""),
        "opportunity_page_url": page_context.get("opportunity_page_url", ""),
        "official_email": email,
        "email_source": email_source or "",
        "email_confidence": judgment.get("email_confidence", _email_confidence(name, email, emails, block_text)),
        "opportunity_type": "Faculty outreach",
        "page_type": "faculty_profile" if profile_url else page_context.get("page_type", "directory_page"),
        "page_type_label": PAGE_TYPE_LABELS.get("faculty_profile" if profile_url else page_context.get("page_type", "directory_page"), "Research profile"),
        "research_tags": _merge_ordered_unique(research_tags, page_context.get("research_tags", []), limit=8),
        "research_areas": research_areas,
        "research_interests": research_interests,
        "discipline_tags": _merge_ordered_unique(discipline_tags, page_context.get("discipline_tags", []), limit=4),
        "publications": [],
        "project_signals": [],
        "recent_topics": _merge_ordered_unique(recent_topics, page_context.get("recent_topics", []), limit=4),
        "student_signals": [],
        "opportunity_signals": [],
        "activity_signals": page_context.get("activity_signals", [])[:2],
        "academic_background": [],
        "profile_signal_count": sum(
            [
                bool(profile_url),
                bool(email),
                bool(research_tags or recent_topics),
                bool(role_title),
                bool(block_text),
            ]
        ),
        "source_types": list(
            dict.fromkeys(
                [page_context.get("page_type_label", "Directory page"), "Candidate block extraction"]
                + (["Local email"] if email else [])
                + (["Linked profile"] if profile_url else [])
            )
        ),
        "profile_text": clean_text(" ".join([block_text[:1200], page_context.get("profile_text", "")[:600]])),
        "bio_or_summary": " ".join(split_sentences(block_text)[:2])[:320],
        "raw_text_excerpt": block_text[:1400],
        "related_candidate_links": [],
        "official_enrichment_found": False,
        "source_credibility_label": source_credibility_label,
        "source_credibility_detail": source_credibility_detail,
        "page_word_count": len(block_text.split()),
        "attribution_confidence": "High" if judgment.get("email_confidence") == "high" else ("Moderate" if email else "Low"),
        "candidate_type": judgment.get("block_type", PERSON_BLOCK_TYPE),
        "extraction_confidence": judgment.get("extraction_confidence", judgment.get("confidence", 0)),
        "warnings": judgment.get("warnings", []),
        "source_summary": "",
    }
    candidate["source_summary"] = _summarize_source_types(candidate)
    candidate["candidate_id"] = _candidate_uid(candidate)
    return _enforce_candidate_consistency(candidate)


def _extract_text_profile_candidates(page_text: str, base_url: str, page_context: dict) -> list[dict]:
    lines = [clean_text(line) for line in str(page_text or "").splitlines() if clean_text(line)]
    if not lines:
        return []

    name_positions = [
        index
        for index, line in enumerate(lines)
        if _looks_like_person_name(_normalize_person_name(line)) and not _looks_like_container_label(line)
    ]
    extracted: list[dict] = []
    seen_names: set[str] = set()

    for idx, start in enumerate(name_positions[:20]):
        name = _normalize_person_name(lines[start])
        end = name_positions[idx + 1] if idx + 1 < len(name_positions) else min(len(lines), start + 12)
        block_lines = lines[start:end]
        if len(block_lines) <= 1:
            block_lines = lines[start : min(len(lines), start + 10)]
        block_text = "\n".join(block_lines)
        if len(clean_text(block_text).split()) < 4:
            continue
        emails = _regex_detect_emails(block_text)
        judgment = _judge_research_block(
            block_text=block_text,
            page_context=page_context,
            forced_name=name,
            name_hint=name,
            local_emails=emails,
            profile_url="",
            block_index=len(extracted),
        )
        if not judgment.get("is_human_candidate"):
            continue
        name = judgment.get("person_name", name)
        email = judgment.get("email", "")
        email_source = judgment.get("email_source", "")
        role_title = judgment.get("title", "") or _guess_role_title(block_text, name)
        research_tags, discipline_tags, recent_topics = _extract_block_topics(block_text, page_context)
        candidate = {
            "name": name,
            "entity_type": "Professor" if any(token in role_title.lower() for token in ("professor", "faculty", "lecturer", "scientist", "fellow", "researcher")) else "Researcher",
            "lead_contact_name": name,
            "role_title": role_title or "Role not clearly labeled on the source page",
            "university": page_context.get("university", "Institution not clearly identified"),
            "department_or_lab": page_context.get("department_or_lab", "Research context from source page"),
            "primary_source_url": base_url,
            "scholarly_profile_url": "",
            "official_profile_url": "",
            "department_page_url": page_context.get("department_page_url", ""),
            "opportunity_page_url": page_context.get("opportunity_page_url", ""),
            "official_email": email,
            "email_source": email_source or "",
            "email_confidence": judgment.get("email_confidence", _email_confidence(name, email, emails, block_text)),
            "opportunity_type": "Faculty outreach",
            "page_type": "directory_page",
            "page_type_label": PAGE_TYPE_LABELS.get("directory_page", "Research profile"),
            "research_tags": research_tags[:8],
            "research_areas": _merge_ordered_unique(judgment.get("research_areas", []), research_tags, limit=8),
            "research_interests": _merge_ordered_unique(judgment.get("research_interests", []), recent_topics, limit=6),
            "discipline_tags": discipline_tags[:4],
            "publications": [],
            "project_signals": [],
            "recent_topics": recent_topics[:4],
            "student_signals": [],
            "opportunity_signals": [],
            "activity_signals": page_context.get("activity_signals", [])[:2],
            "academic_background": [],
            "profile_signal_count": sum([bool(email), bool(role_title), bool(research_tags or recent_topics), bool(block_text)]),
            "source_types": list(dict.fromkeys([page_context.get("page_type_label", "Directory page"), "Visible text profile extraction"] + (["Local email"] if email else []))),
            "profile_text": block_text[:1400],
            "bio_or_summary": " ".join(split_sentences(block_text)[:2])[:320],
            "raw_text_excerpt": block_text[:1400],
            "related_candidate_links": [],
            "official_enrichment_found": False,
            "source_credibility_label": page_context.get("source_credibility_label", "Limited"),
            "source_credibility_detail": "The candidate was extracted from visible person-specific text on the provided page.",
            "page_word_count": len(block_text.split()),
            "attribution_confidence": "High" if judgment.get("email_confidence") == "high" else ("Moderate" if email else "Low"),
            "candidate_type": judgment.get("block_type", PERSON_BLOCK_TYPE),
            "extraction_confidence": judgment.get("extraction_confidence", judgment.get("confidence", 0)),
            "warnings": judgment.get("warnings", []),
            "source_summary": "",
            "source_block_index": len(extracted),
        }
        candidate["source_summary"] = _summarize_source_types(candidate)
        candidate["candidate_id"] = _candidate_uid(candidate)
        candidate = _enforce_candidate_consistency(candidate)
        if not _is_person_candidate(candidate):
            continue
        key = candidate.get("name", "").lower()
        if key in seen_names:
            continue
        seen_names.add(key)
        extracted.append(candidate)
    return extracted[:15]


def _merge_person_candidates(candidates: list[dict]) -> list[dict]:
    merged: list[dict] = []
    for candidate in candidates:
        normalized = _enforce_candidate_consistency(candidate)
        if not _is_person_candidate(normalized):
            continue
        matched = False
        for idx, existing in enumerate(merged):
            if _names_compatible(existing.get("name", ""), normalized.get("name", "")):
                merged[idx] = _merge_target_fields(existing, normalized)
                matched = True
                break
        if not matched:
            merged.append(normalized)
    return merged


def _extract_multi_profile_candidates(soup: BeautifulSoup, base_url: str, page_context: dict) -> list[dict]:
    extracted: list[dict] = []
    seen_ids: set[tuple[str, str]] = set()
    candidate_nodes: list[BeautifulSoup] = []
    contact_names = _extract_named_contacts(
        soup,
        page_context.get("profile_text", ""),
        page_context.get("name", ""),
        page_context.get("page_type", "other"),
    )
    for link in soup.find_all("a", href=True):
        anchor_text = clean_text(link.get_text(" ", strip=True))
        href = link.get("href", "").strip()
        if not href or href.startswith("mailto:"):
            continue
        if _looks_like_person_name(anchor_text):
            candidate_nodes.append(link)
    for mail_link in soup.select("a[href^='mailto:']"):
        candidate_nodes.append(mail_link)
    if not candidate_nodes:
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b", "dt"]):
            text = _normalize_person_name(tag.get_text(" ", strip=True))
            if _looks_like_person_name(text):
                candidate_nodes.append(tag)
    for name in contact_names:
        for tag in soup.find_all(["a", "h1", "h2", "h3", "h4", "strong", "b", "dt", "td", "th", "span", "p", "div", "li"]):
            text = clean_text(tag.get_text(" ", strip=True))
            if not text:
                continue
            if text == name or name in text:
                candidate_nodes.append(tag)
    for node in candidate_nodes[:80]:
        container = _best_candidate_container(node)
        forced_name = ""
        visible_text = clean_text(node.get_text(" ", strip=True))
        for contact_name in contact_names:
            if contact_name == visible_text or contact_name in visible_text:
                forced_name = contact_name
                break
        candidate = _build_candidate_from_block(container, base_url, page_context, forced_name=forced_name)
        if not candidate:
            continue
        if not _is_person_candidate(candidate):
            continue
        key = (
            candidate.get("name", "").lower(),
            _normalized_result_url(candidate.get("official_profile_url") or candidate.get("primary_source_url") or base_url),
        )
        if key in seen_ids:
            continue
        seen_ids.add(key)
        candidate["source_block_index"] = len(extracted)
        extracted.append(candidate)
    return extracted[:15]


def _extract_primary_profile_candidate(soup: BeautifulSoup, base_url: str, page_context: dict) -> dict | None:
    primary_node = soup.find("main") or soup.find("article") or soup.body or soup
    block_text = clean_text(primary_node.get_text("\n", strip=True))
    if len(block_text.split()) < 8:
        return None
    name_hint = _candidate_display_name(primary_node) or _normalize_person_name(page_context.get("lead_contact_name") or page_context.get("name", ""))
    local_emails = _extract_emails_from_node(primary_node, canonical_domain(base_url), allow_any_visible=True) or _regex_detect_emails(block_text)
    profile_url = clean_text(page_context.get("official_profile_url", "")) or base_url
    judgment = _judge_research_block(
        block_text=block_text,
        page_context=page_context,
        forced_name=name_hint,
        name_hint=name_hint,
        local_emails=local_emails,
        profile_url=profile_url,
        block_index=0,
    )
    if not judgment.get("is_human_candidate"):
        return None
    role_title = judgment.get("title", "") or _guess_role_title(block_text, judgment.get("person_name", ""))
    research_tags, discipline_tags, recent_topics = _extract_block_topics(block_text, page_context)
    candidate = {
        "name": judgment.get("person_name", ""),
        "entity_type": "Professor" if any(token in role_title.lower() for token in ("professor", "faculty", "lecturer", "scientist", "fellow", "researcher")) else "Researcher",
        "lead_contact_name": judgment.get("person_name", ""),
        "role_title": role_title or "Role not clearly labeled on the source page",
        "university": judgment.get("institution", "") or page_context.get("university", "Institution not clearly identified"),
        "department_or_lab": judgment.get("department_or_lab", "") or page_context.get("department_or_lab", "Research context from source page"),
        "primary_source_url": base_url,
        "scholarly_profile_url": "",
        "official_profile_url": profile_url,
        "department_page_url": page_context.get("department_page_url", ""),
        "opportunity_page_url": page_context.get("opportunity_page_url", ""),
        "official_email": judgment.get("email", ""),
        "email_source": judgment.get("email_source", ""),
        "email_confidence": judgment.get("email_confidence", _email_confidence(judgment.get("person_name", ""), judgment.get("email", ""), local_emails, block_text)),
        "opportunity_type": page_context.get("opportunity_type", "Faculty outreach"),
        "page_type": "faculty_profile" if page_context.get("page_type") != "directory_page" else page_context.get("page_type", "other"),
        "page_type_label": PAGE_TYPE_LABELS.get("faculty_profile" if page_context.get("page_type") != "directory_page" else page_context.get("page_type", "other"), "Research profile"),
        "research_tags": _merge_ordered_unique(research_tags, page_context.get("research_tags", []), limit=8),
        "research_areas": _merge_ordered_unique(judgment.get("research_areas", []), research_tags + discipline_tags, limit=8),
        "research_interests": _merge_ordered_unique(judgment.get("research_interests", []), recent_topics + research_tags, limit=6),
        "discipline_tags": _merge_ordered_unique(discipline_tags, page_context.get("discipline_tags", []), limit=4),
        "publications": page_context.get("publications", [])[:3],
        "project_signals": page_context.get("project_signals", [])[:3],
        "recent_topics": _merge_ordered_unique(recent_topics, page_context.get("recent_topics", []), limit=4),
        "student_signals": page_context.get("student_signals", [])[:3],
        "opportunity_signals": page_context.get("opportunity_signals", [])[:4],
        "activity_signals": page_context.get("activity_signals", [])[:3],
        "academic_background": page_context.get("academic_background", [])[:2],
        "profile_signal_count": max(page_context.get("profile_signal_count", 0), 3),
        "source_types": list(dict.fromkeys(page_context.get("source_types", []) + ["Primary profile block extraction"])),
        "profile_text": block_text[:1800],
        "bio_or_summary": " ".join(split_sentences(block_text)[:2])[:320],
        "raw_text_excerpt": block_text[:1800],
        "related_candidate_links": page_context.get("related_candidate_links", []),
        "official_enrichment_found": bool(judgment.get("email")) or bool(profile_url),
        "source_credibility_label": page_context.get("source_credibility_label", "Limited"),
        "source_credibility_detail": page_context.get("source_credibility_detail", ""),
        "page_word_count": len(block_text.split()),
        "attribution_confidence": "High" if judgment.get("email_confidence") == "high" else ("Moderate" if judgment.get("email") else "Low"),
        "candidate_type": judgment.get("block_type", PERSON_BLOCK_TYPE),
        "extraction_confidence": judgment.get("extraction_confidence", judgment.get("confidence", 0)),
        "warnings": judgment.get("warnings", []),
        "source_summary": "",
        "source_block_index": 0,
    }
    candidate["source_summary"] = _summarize_source_types(candidate)
    candidate["candidate_id"] = _candidate_uid(candidate)
    return _enforce_candidate_consistency(candidate)


def _extract_lines_from_sections(sections: list[tuple[str, str]], keywords: tuple[str, ...], limit: int = 4) -> list[str]:
    results: list[str] = []
    for heading, content in sections:
        combined = f"{heading}\n{content}".lower()
        if any(keyword in combined for keyword in keywords):
            for sentence in split_sentences(content):
                if sentence and sentence not in results:
                    results.append(sentence)
                if len(results) >= limit:
                    return results
    return results


def _extract_publications(soup: BeautifulSoup, sections: list[tuple[str, str]]) -> list[str]:
    publications = _extract_lines_from_sections(sections, PUBLICATION_HINTS, limit=4)
    if publications:
        return publications
    link_titles: list[str] = []
    for link in soup.find_all("a", href=True):
        text = clean_text(link.get_text(" ", strip=True))
        if len(text.split()) >= 4 and any(year in text for year in ("2023", "2024", "2025", "2026")):
            link_titles.append(text)
        if len(link_titles) >= 4:
            break
    return link_titles


def _extract_project_signals(sections: list[tuple[str, str]]) -> list[str]:
    return _extract_lines_from_sections(sections, PROJECT_HINTS, limit=4)


def _extract_recent_topics(publications: list[str], project_signals: list[str], research_tags: list[str]) -> list[str]:
    topics = publications[:2] + project_signals[:2]
    if not topics:
        topics = [tag for tag in research_tags[:4]]
    return [clean_text(topic) for topic in topics if clean_text(topic)][:4]


def _extract_named_contacts(soup: BeautifulSoup, text: str, page_title: str, page_type: str) -> list[str]:
    names: list[str] = []
    if page_type == "faculty_profile":
        guessed = _guess_professor_name(soup, page_title)
        if guessed != "Professor profile":
            names.append(guessed)
    for pattern in (
        re.compile(r"\b(?:Principal Investigator|PI|Director|Head of Lab|Lab Director|Group Leader)[:\s]+([A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){0,3})"),
        re.compile(r"\b(?:Professor|Prof\.?|Dr\.?)\s+([A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){0,3})"),
        re.compile(r"(?:姓名|Name)[:：]\s*([\u4e00-\u9fff]{2,4}|[A-Z][A-Za-z'`\-]+(?:\s+[A-Z][A-Za-z'`\-]+){0,3})", flags=re.IGNORECASE),
        re.compile(r"(?:研究员|副研究员|助理研究员|教授|副教授|助理教授|博士后)[:：\s]+([\u4e00-\u9fff]{2,4})"),
    ):
        for match in pattern.findall(text[:5000]):
            cleaned = _normalize_person_name(match)
            if cleaned and cleaned not in names and _looks_like_person_name(cleaned):
                names.append(cleaned)
            if len(names) >= 4:
                return names[:4]
    for link in soup.find_all("a", href=True):
        anchor = _normalize_person_name(link.get_text(" ", strip=True))
        href = link.get("href", "").lower()
        if not anchor or anchor in names or not _looks_like_person_name(anchor):
            continue
        if any(hint in href for hint in FACULTY_PATH_HINTS + DIRECTORY_PATH_HINTS) or any(token in anchor.lower() for token in ("prof", "dr")):
            names.append(anchor)
        if len(names) >= 4:
            break
    if len(names) < 4:
        for tag in soup.find_all(["h1", "h2", "h3", "h4", "strong", "b", "dt", "td", "th", "span", "p"]):
            candidate = _normalize_person_name(tag.get_text(" ", strip=True))
            if not candidate or candidate in names or not _looks_like_person_name(candidate) or _looks_like_container_label(candidate):
                continue
            names.append(candidate)
            if len(names) >= 4:
                break
    return names[:4]


def _extract_student_signals(text: str) -> list[str]:
    lowered = text.lower()
    signals: list[str] = []
    for label, patterns in (
        ("Mentions opportunities for prospective students or people interested in joining.", ("prospective students", "join the lab", "join our group", "students interested")),
        ("Mentions undergraduate or summer research access.", ("undergraduate", "summer research", "reu", "research experience for undergraduates")),
        ("Mentions research assistant or project roles.", ("research assistant", "ra position", "project assistant", "assistantship")),
    ):
        if any(pattern in lowered for pattern in patterns):
            signals.append(label)
    return signals[:3]


def _extract_opportunity_signals(text: str, sections: list[tuple[str, str]], page_type: str) -> list[str]:
    lowered = text.lower()
    signals: list[str] = []
    if page_type == "opportunity_page":
        signals.append("The main page itself is an opportunity or recruitment page.")
    signal_patterns = (
        ("Shows explicit application or recruitment language.", ("apply", "application", "opening", "openings", "vacancy", "vacancies", "how to apply")),
        ("Shows student-facing research opportunity language.", ("research opportunity", "research opportunities", "summer research", "undergraduate research")),
        ("Shows research-assistant or project-opening language.", ("research assistant", "project assistant", "assistantship", "predoctoral")),
        ("Shows funded-position language.", ("funded", "funding", "studentship", "stipend", "scholarship")),
    )
    for label, patterns in signal_patterns:
        if any(pattern in lowered for pattern in patterns):
            signals.append(label)
    if not signals:
        section_lines = _extract_lines_from_sections(sections, OPPORTUNITY_HINTS, limit=2)
        signals.extend(section_lines)
    return list(dict.fromkeys(signals))[:4]


def _extract_activity_signals(text: str, publications: list[str], project_signals: list[str]) -> list[str]:
    lowered = text.lower()
    signals: list[str] = []
    years = sorted(set(re.findall(r"\b(20(?:2[3-9]|3[0-1]))\b", " ".join(publications + project_signals + [text[:2000]]))))
    if years:
        signals.append(f"Recent activity is visible through {', '.join(years[-2:])} outputs or project references.")
    if any(term in lowered for term in ("recent", "ongoing", "current project", "current work", "lab news", "news")):
        signals.append("The page includes current or ongoing research language.")
    if any(term in lowered for term in ("opening", "openings", "apply now", "deadline")):
        signals.append("The page looks active enough to support near-term outreach.")
    return list(dict.fromkeys(signals))[:3]


def _extract_research_tags(profile_text: str) -> list[str]:
    keywords = extract_keywords(profile_text, limit=18)
    cleaned = [keyword for keyword in keywords if len(keyword) > 2]
    return sorted(dict.fromkeys(cleaned))[:10]


def _extract_academic_background(sections: list[tuple[str, str]], text: str) -> list[str]:
    background_lines = _extract_lines_from_sections(
        sections,
        ("biography", "bio", "education", "about", "background", "cv"),
        limit=5,
    )
    academic_lines = []
    for sentence in background_lines + split_sentences(text[:2500]):
        lowered = sentence.lower()
        if any(token in lowered for token in ("phd", "doctorate", "doctoral", "msc", "m.sc", "bsc", "b.sc", "earned", "received")):
            cleaned = clean_text(sentence)
            if cleaned and cleaned not in academic_lines:
                academic_lines.append(cleaned)
        if len(academic_lines) >= 2:
            break
    return academic_lines[:2]


def _infer_opportunity_type(page_type: str, text: str) -> str:
    lowered = text.lower()
    if any(term in lowered for term in ("summer research", "undergraduate research", "reu")):
        return "Summer research"
    if any(term in lowered for term in ("research assistant", "ra position", "assistantship", "predoctoral", "project assistant")):
        return "RA / opening"
    if any(term in lowered for term in ("internship", "intern")):
        return "Research internship"
    if any(term in lowered for term in ("phd", "prospective students", "doctoral")):
        return "PhD pathway"
    if page_type == "faculty_profile":
        return "Faculty outreach"
    if page_type == "lab_page":
        return "Lab outreach"
    if page_type == "center_page":
        return "Research center outreach"
    if page_type == "department_page":
        return "Department opportunity"
    if page_type == "directory_page":
        return "Directory lead"
    return "Research opportunity"


def _determine_entity_name(page_type: str, page_heading: str, page_title: str, contacts: list[str]) -> tuple[str, str, str]:
    normalized_heading = _normalize_person_name(page_heading)
    normalized_title = _normalize_person_name(page_title)
    lead = contacts[0] if contacts else ""
    prefer_contact = bool(lead and (_looks_like_container_label(normalized_heading) or not _looks_like_person_name(normalized_heading)))
    if page_type == "faculty_profile":
        name = lead if lead else normalized_heading or normalized_title
        return name, "Professor", lead
    if page_type == "lab_page":
        return (lead if prefer_contact else normalized_heading or normalized_title), "Lab", lead
    if page_type == "center_page":
        return (lead if prefer_contact else normalized_heading or normalized_title), "Research center", lead
    if page_type == "opportunity_page":
        return (lead if prefer_contact else normalized_heading or normalized_title), "Opportunity", lead
    if page_type == "department_page":
        return (lead if prefer_contact else normalized_heading or normalized_title), "Department", lead
    if page_type == "directory_page":
        return lead or normalized_heading or normalized_title, "Directory", lead
    if lead and (_looks_like_person_name(lead) or prefer_contact):
        return lead, "Researcher", lead
    return normalized_heading or normalized_title, "Research Match", lead


def _summarize_source_types(candidate: dict) -> str:
    labels = [PAGE_TYPE_LABELS.get(candidate.get("page_type", "other"), "Official research page")]
    if candidate.get("page_type") == "scholarly_profile":
        labels = [OPENALEX_SOURCE_LABEL]
    if candidate.get("official_profile_url"):
        labels.append("Official enrichment")
    if candidate.get("department_page_url"):
        labels.append("Department/lab context")
    if candidate.get("university"):
        labels.append("Institution affiliation")
    if candidate.get("opportunity_signals"):
        labels.append("Opportunity signals")
    if candidate.get("publications"):
        labels.append("Publications")
    if candidate.get("project_signals"):
        labels.append("Projects")
    if candidate.get("official_email"):
        labels.append("Official email")
    return " + ".join(dict.fromkeys(labels))


def _method_overlap(candidate_methods: list[str], page_text: str) -> list[str]:
    matches: list[str] = []
    lowered = page_text.lower()
    for method in sorted(candidate_methods):
        if any(pattern in lowered for pattern in METHOD_PATTERNS.get(method, ())):
            matches.append(method)
    return matches


def _stage_suitability_score(academic_stage: str, profile_text: str, opportunity_signals: list[str]) -> tuple[int, str]:
    if not academic_stage or academic_stage == "Other":
        return 10, "No stage filter was applied."
    lowered = profile_text.lower()
    patterns = STAGE_HINTS.get(academic_stage, ())
    if any(pattern in lowered for pattern in patterns):
        return 18, f"The page shows signals that {academic_stage.lower()} outreach could be appropriate."
    if academic_stage == "Undergraduate" and any(pattern in lowered for pattern in STAGE_HINTS["Master"] + STAGE_HINTS["PhD interest"]):
        return 7, "The page looks more graduate-facing than undergraduate-facing."
    if opportunity_signals:
        return 13, "The page looks student-facing, but stage fit is still only partially explicit."
    return 10, "The page does not clearly confirm stage fit, but it also does not rule it out."


def _build_source_coverage(candidate: dict, resume_result: dict) -> tuple[list[dict[str, str]], int]:
    rows: list[dict[str, str]] = []
    coverage_strength = 0
    primary_label = PAGE_TYPE_LABELS.get(candidate.get("page_type", "other"), "Official research page")
    primary_source_url = candidate.get("primary_source_url") or candidate.get("official_profile_url")

    rows.append(
        {
            "label": "Primary source page",
            "status": "Found" if primary_source_url else "Missing",
            "tone": "success" if primary_source_url else "missing",
            "detail": (
                f"{primary_label} was used as the main evidence source."
                if primary_source_url
                else "No trustworthy primary research source was confirmed."
            ),
        }
    )
    if primary_source_url:
        coverage_strength += 1

    rows.append(
        {
            "label": "Official enrichment",
            "status": "Found" if candidate.get("official_profile_url") else "Limited",
            "tone": "success" if candidate.get("official_profile_url") else "partial",
            "detail": (
                "An official faculty, department, lab, or directory page was found and used to enrich the scholarly match."
                if candidate.get("official_profile_url")
                else "No official faculty or lab page was confirmed, so the match relies more on scholarly metadata than official profile enrichment."
            ),
        }
    )
    if candidate.get("official_profile_url"):
        coverage_strength += 1

    rows.append(
        {
            "label": "Source credibility",
            "status": candidate.get("source_credibility_label", "Limited"),
            "tone": "success" if candidate.get("source_credibility_label") == "High" else ("partial" if candidate.get("source_credibility_label") == "Moderate" else "info"),
            "detail": candidate.get(
                "source_credibility_detail",
                "Source credibility was not fully characterized from the available evidence.",
            ),
        }
    )
    if candidate.get("source_credibility_label") in {"High", "Moderate"}:
        coverage_strength += 1

    rows.append(
        {
            "label": "Official email",
            "status": "Found" if candidate.get("official_email") else "Not found",
            "tone": "success" if candidate.get("official_email") else "missing",
            "detail": "The email address was found on an official or clearly attributable page." if candidate.get("official_email") else "Email not found from official or attributable sources.",
        }
    )
    if candidate.get("official_email"):
        coverage_strength += 1

    rows.append(
        {
            "label": "Institution affiliation",
            "status": "Found" if candidate.get("university") and candidate.get("university") != "Institution not clearly identified" else "Limited",
            "tone": "success" if candidate.get("university") and candidate.get("university") != "Institution not clearly identified" else "partial",
            "detail": (
                f"Institutional affiliation was identified as {candidate.get('university')}."
                if candidate.get("university") and candidate.get("university") != "Institution not clearly identified"
                else "The candidate's institution was only weakly visible from the available evidence."
            ),
        }
    )
    if candidate.get("university") and candidate.get("university") != "Institution not clearly identified":
        coverage_strength += 1

    department_found = candidate.get("department_page_url") or candidate.get("page_type") in {"lab_page", "center_page", "department_page"}
    rows.append(
        {
            "label": "Department / lab context",
            "status": "Found" if department_found else "Limited",
            "tone": "success" if department_found else "partial",
            "detail": "Department or lab context was confirmed and used in matching." if department_found else "Department or lab context was thin beyond the main page.",
        }
    )
    if department_found:
        coverage_strength += 1

    rows.append(
        {
            "label": "Opportunity / recruitment signal",
            "status": "Found" if candidate.get("opportunity_signals") else "Limited",
            "tone": "success" if candidate.get("opportunity_signals") else "partial",
            "detail": candidate["opportunity_signals"][0] if candidate.get("opportunity_signals") else "No explicit opening, application, or invitation signal was clearly found.",
        }
    )
    if candidate.get("opportunity_signals"):
        coverage_strength += 1

    rows.append(
        {
            "label": "Publication evidence",
            "status": "Found" if candidate.get("publications") else "Limited",
            "tone": "success" if candidate.get("publications") else "partial",
            "detail": "Publication or paper signals were found and used for research-output fit." if candidate.get("publications") else "Publication evidence was limited on the available pages.",
        }
    )
    if candidate.get("publications"):
        coverage_strength += 1

    rows.append(
        {
            "label": "Recent project signals",
            "status": "Found" if candidate.get("project_signals") else "Limited",
            "tone": "success" if candidate.get("project_signals") else "partial",
            "detail": "Project, grant, or lab activity signals were found on the available pages." if candidate.get("project_signals") else "Recent projects or current work were only weakly visible.",
        }
    )
    if candidate.get("project_signals"):
        coverage_strength += 1

    rows.append(
        {
            "label": "Academic background",
            "status": "Found" if candidate.get("academic_background") else "Not found",
            "tone": "success" if candidate.get("academic_background") else "info",
            "detail": "Academic-background information was found and may help interpret fit." if candidate.get("academic_background") else "Professor educational background was not clearly found from the fetched sources.",
        }
    )
    if candidate.get("academic_background"):
        coverage_strength += 1

    rows.append(
        {
            "label": "Public supervision signal",
            "status": "Not fetched",
            "tone": "info",
            "detail": "No supervision-style public signal was fetched or inferred.",
        }
    )
    rows.append(
        {
            "label": "External reputation",
            "status": "Not used",
            "tone": "info",
            "detail": "External reputation or social sentiment was not used in ranking.",
        }
    )
    rows.append(
        {
            "label": "CV PDF",
            "status": "Parsed successfully" if resume_result.get("success") else "Missing",
            "tone": "success" if resume_result.get("success") else "missing",
            "detail": "The uploaded resume was parsed and used for fit scoring."
            if resume_result.get("success")
            else "No usable CV evidence was available for the research-fit calculation.",
        }
    )
    return rows, coverage_strength


def _recommendation(priority_score: int, research_fit_score: int, feasibility_score: int, coverage_strength: int) -> str:
    if coverage_strength <= 1:
        return "Insufficient evidence"
    if priority_score >= 74 and research_fit_score >= 68 and feasibility_score >= 54:
        return "Reach out now"
    if priority_score >= 58 and research_fit_score >= 54:
        return "Reach out after tailoring"
    if priority_score >= 44:
        return "Save for later"
    return "Low-priority contact"


def _candidate_evidence_count(candidate: dict) -> int:
    return sum(
        [
            bool(candidate.get("research_tags")),
            bool(candidate.get("discipline_tags")),
            bool(candidate.get("recent_topics") or candidate.get("publications") or candidate.get("project_signals")),
            bool(candidate.get("department_or_lab") and candidate.get("department_or_lab") not in {"Official research context", "Scholarly research profile"}),
            bool(candidate.get("primary_source_url") or candidate.get("official_profile_url")),
            bool(candidate.get("official_email") or candidate.get("lead_contact_name")),
        ]
    )


def _eligible_by_alignment(scored_candidate: dict) -> bool:
    fit = scored_candidate.get("research_fit_score", 0)
    alignment_count = scored_candidate.get("alignment_signal_count", 0)
    evidence_count = scored_candidate.get("profile_evidence_count", 0)
    if evidence_count < 2:
        return False
    if fit >= 62:
        return True
    if fit >= 52 and alignment_count >= 2:
        return True
    if fit >= 46 and alignment_count >= 3:
        return True
    return False


def _score_candidate(candidate: dict, profile: dict) -> dict:
    candidate_keywords = set(profile["interest_keywords"] + profile["topic_keywords"][:10])
    candidate_disciplines = set(profile.get("discipline_tags", []))
    page_text = " ".join(
        candidate.get("research_tags", [])
        + candidate.get("discipline_tags", [])
        + candidate.get("recent_topics", [])
        + candidate.get("publications", [])
        + candidate.get("project_signals", [])
        + candidate.get("opportunity_signals", [])
        + candidate.get("academic_background", [])
        + [candidate.get("university", ""), candidate.get("department_or_lab", ""), candidate.get("profile_text", "")]
    )
    page_keywords = set(extract_keywords(page_text, limit=28))
    research_keywords = set(_normalize_tokens(candidate.get("research_tags", []) + candidate.get("recent_topics", [])))
    topic_overlap = sorted((candidate_keywords & page_keywords) | (candidate_keywords & research_keywords))
    output_keywords = set(extract_keywords(" ".join(candidate.get("publications", []) + candidate.get("project_signals", [])), limit=24))
    output_overlap = sorted(candidate_keywords & output_keywords)
    method_matches = _method_overlap(profile.get("methods", []), page_text)
    tool_matches = sorted(set(profile.get("tools", [])) & page_keywords)
    discipline_overlap = sorted(candidate_disciplines & set(candidate.get("discipline_tags", [])))
    background_overlap = sorted(candidate_disciplines & set(_extract_discipline_tags(" ".join(candidate.get("academic_background", [])))))
    stage_score, stage_note = _stage_suitability_score(profile["academic_stage"], candidate["profile_text"], candidate.get("opportunity_signals", []))

    alignment_signal_count = sum(
        [
            bool(topic_overlap),
            bool(method_matches or tool_matches),
            bool(discipline_overlap or background_overlap),
            bool(output_overlap or candidate.get("publications") or candidate.get("project_signals")),
        ]
    )
    profile_evidence_count = _candidate_evidence_count(candidate)
    public_opportunity_signal_found = bool(candidate.get("opportunity_signals"))

    fit_score = 28
    fit_score += min(40, len(topic_overlap) * 8 + (6 if output_overlap else 0))
    fit_score += min(14, len(method_matches) * 5)
    fit_score += min(8, len(tool_matches) * 4)
    fit_score += min(12, len(discipline_overlap) * 6)
    fit_score += 8 if candidate.get("publications") else 0
    fit_score += 6 if candidate.get("project_signals") else 0
    fit_score += 4 if background_overlap else 0
    fit_score += 4 if candidate.get("target_region_match") else 0
    fit_score += 6 if any(exposure in profile.get("research_exposure", []) for exposure in ("Research experience", "Project work")) else 2
    research_fit_score = max(20, min(98, fit_score))

    feasibility_score = 22
    feasibility_score += {
        "scholarly_profile": 8,
        "faculty_profile": 12,
        "opportunity_page": 12,
        "lab_page": 11,
        "center_page": 10,
        "department_page": 9,
        "directory_page": 7,
        "project_page": 7,
        "publication_page": 5,
    }.get(candidate.get("page_type", "other"), 5)
    feasibility_score += 16 if candidate.get("official_email") else 0
    feasibility_score += 6 if candidate.get("lead_contact_name") and not candidate.get("official_email") else 0
    feasibility_score += 5 if candidate.get("official_profile_url") else 0
    feasibility_score += 6 if candidate.get("department_page_url") else 0
    feasibility_score += min(6, len(candidate.get("opportunity_signals", [])) * 2)
    feasibility_score += min(6, len(candidate.get("student_signals", [])) * 2)
    feasibility_score += min(6, len(candidate.get("activity_signals", [])) * 3)
    feasibility_score += min(6, len(set(candidate.get("source_types", []))))
    feasibility_score += min(5, candidate.get("scholarly_work_count", 0))
    feasibility_score += stage_score
    if profile["funding_required"] and not any("fund" in signal.lower() or "stipend" in signal.lower() or "studentship" in signal.lower() for signal in candidate.get("opportunity_signals", []) + candidate.get("project_signals", [])):
        feasibility_score -= 4
    outreach_feasibility_score = max(16, min(98, feasibility_score))

    coverage_rows, coverage_strength = _build_source_coverage(candidate, profile["resume_result"])
    actionability_bonus = min(
        6,
        3 * bool(candidate.get("official_email") or candidate.get("lead_contact_name"))
        + 3 * bool(candidate.get("activity_signals")),
    )
    priority_score = max(18, min(98, int(round(research_fit_score * 0.72 + outreach_feasibility_score * 0.22 + actionability_bonus))))
    recommendation = _recommendation(priority_score, research_fit_score, outreach_feasibility_score, coverage_strength)

    why_match = []
    if topic_overlap:
        why_match.append(f"Topic fit is visible across {', '.join(topic_overlap[:4])}.")
    if discipline_overlap:
        why_match.append(f"Discipline fit is reinforced by overlap in {', '.join(discipline_overlap[:3])}.")
    if method_matches or tool_matches:
        pieces = []
        if method_matches:
            pieces.append(f"methods such as {', '.join(method_matches[:3])}")
        if tool_matches:
            pieces.append(f"tools such as {', '.join(tool_matches[:3])}")
        why_match.append(f"Method and technical fit show up through {' and '.join(pieces)}.")
    if output_overlap:
        why_match.append(f"Recent outputs connect to {', '.join(output_overlap[:3])}.")
    elif candidate.get("publications") or candidate.get("project_signals"):
        why_match.append("The page includes recent outputs or project signals rather than only static profile text.")
    if candidate.get("opportunity_signals"):
        why_match.append(candidate["opportunity_signals"][0])
    if profile.get("research_exposure"):
        why_match.append(f"Your CV already shows {', '.join(profile['research_exposure'][:2]).lower()} that can support outreach.")
    if not why_match:
        why_match.append("The match is based on limited but still relevant research and opportunity signals.")

    weaknesses = []
    if not candidate.get("official_email"):
        weaknesses.append("Official email not found from official or attributable sources.")
    if not topic_overlap:
        weaknesses.append("The topic overlap is broad rather than clearly subfield-specific.")
    if candidate_disciplines and not discipline_overlap:
        weaknesses.append("The department or academic home is not clearly aligned with your strongest discipline signals.")
    if not candidate.get("publications") and not candidate.get("project_signals"):
        weaknesses.append("Recent outputs or live project signals are thin on the available pages.")
    if "graduate-facing" in stage_note.lower():
        weaknesses.append(stage_note)
    if profile["funding_required"] and not any("fund" in signal.lower() or "stipend" in signal.lower() or "studentship" in signal.lower() for signal in candidate.get("opportunity_signals", []) + candidate.get("project_signals", [])):
        weaknesses.append("Funding support is not clearly visible from the current sources.")
    if not weaknesses:
        weaknesses.append("No major risk dominated, but the decision still depends on tailoring your outreach to the available evidence.")

    contact_feasibility = []
    if candidate.get("official_email"):
        contact_feasibility.append("Official email is available on a trustworthy source.")
    elif candidate.get("lead_contact_name"):
        contact_feasibility.append(f"A named contact is visible ({candidate['lead_contact_name']}), but no official email was confirmed.")
    else:
        contact_feasibility.append("No direct official contact route was visible on the main sources.")
    contact_feasibility.append(stage_note)
    if candidate.get("opportunity_signals"):
        contact_feasibility.append(candidate["opportunity_signals"][0])
    else:
        contact_feasibility.append("No public opportunity signal was found, so any outreach would be proactive rather than opening-led.")
    if candidate.get("activity_signals"):
        contact_feasibility.append(candidate["activity_signals"][0])

    quick_source_summary = candidate["source_summary"]
    source_rows = [row["label"] for row in coverage_rows if row["tone"] == "success"][:3]
    return {
        **candidate,
        "candidate_id": candidate.get("candidate_id") or _candidate_uid(candidate),
        "research_fit_score": research_fit_score,
        "outreach_feasibility_score": outreach_feasibility_score,
        "priority_score": priority_score,
        "recommendation": recommendation,
        "public_opportunity_signal_found": public_opportunity_signal_found,
        "alignment_signal_count": alignment_signal_count,
        "profile_evidence_count": profile_evidence_count,
        "why_match": why_match[:5],
        "weaknesses": weaknesses[:5],
        "contact_feasibility": contact_feasibility[:4],
        "source_coverage": coverage_rows,
        "why_match_topline": why_match[0],
        "main_watchout": weaknesses[0],
        "why_matched_summary": f"{why_match[0]} {weaknesses[0]}",
        "quick_source_summary": quick_source_summary,
        "source_comparison_labels": source_rows,
    }


def _parse_research_page(result: dict[str, str], *, allow_non_official: bool = False, min_words: int = 40) -> dict | None:
    url = result["url"]
    if not allow_non_official and not _looks_trustworthy_research_result(url, result.get("title", ""), result.get("snippet", "")):
        return None

    html_text, _error = fetch_page_best_effort(url)
    if not html_text:
        return None

    soup = try_bs4(html_text)
    text = extract_page_text(soup)
    if len(text.split()) < min_words and result.get("source_type") not in {"faculty_profile", "directory_page"}:
        return None

    page_title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else result.get("title", "")
    page_heading = _guess_page_heading(soup, page_title)
    page_type = _classify_page_type(url, page_title or result.get("title", ""), result.get("snippet", ""), text)
    sections = _extract_heading_sections(soup)
    contacts = _extract_named_contacts(soup, text, page_title, page_type)
    name, entity_type, lead_contact = _determine_entity_name(page_type, page_heading, page_title, contacts)
    role_title = _guess_role_title(text[:1600], lead_contact or name)
    university = _guess_university(url, page_title or result.get("title", ""))
    department = _guess_department(sections, text, page_heading)
    email, email_source = _find_mailto_email(soup, canonical_domain(url))
    if page_type in {"directory_page", "lab_page", "department_page", "center_page"} and len(contacts) > 1:
        email = ""
        email_source = ""
    department_page_url = _find_related_page(soup, url, ("department", "lab", "group", "research"))
    opportunity_page_url = _find_related_page(soup, url, ("opportunity", "apply", "join", "students", "opening", "research assistant"))

    research_focus = []
    for heading, content in sections:
        lowered = heading.lower()
        if any(
            keyword in lowered
            for keyword in (
                "research",
                "about",
                "interests",
                "lab",
                "group",
                "publications",
                "projects",
                "opportunities",
                "people",
                "team",
                "members",
                "director",
                "overview",
                "mission",
                "current work",
            )
        ):
            research_focus.append(content)
    research_text = clean_text("\n".join(research_focus) or text[:2600])
    research_tags = _extract_research_tags(research_text)
    publications = _extract_publications(soup, sections)
    project_signals = _extract_project_signals(sections)
    recent_topics = _extract_recent_topics(publications, project_signals, research_tags)
    student_signals = _extract_student_signals(text)
    opportunity_signals = _extract_opportunity_signals(text, sections, page_type)
    activity_signals = _extract_activity_signals(text, publications, project_signals)
    discipline_tags = _extract_discipline_tags("\n".join([page_heading, department, research_text]))
    academic_background = _extract_academic_background(sections, text)
    opportunity_type = _infer_opportunity_type(page_type, text)
    related_candidate_links = _extract_related_candidate_links(soup, url, page_type)
    source_credibility_label, source_credibility_detail = _source_credibility(url, page_type, text, page_title)

    profile_signal_count = sum(
        [
            bool(research_tags),
            bool(discipline_tags),
            bool(publications or project_signals or recent_topics),
            bool(contacts),
            bool(department and department != "Official research context"),
            bool(email),
            bool(related_candidate_links),
        ]
    )
    if profile_signal_count < 2 and not (allow_non_official and (research_tags or recent_topics or contacts or email or len(text.split()) >= 80)):
        return None

    source_types = [PAGE_TYPE_LABELS.get(page_type, "Official research page")]
    if opportunity_signals:
        source_types.append("Opportunity signals")
    if publications:
        source_types.append("Publications")
    if project_signals:
        source_types.append("Projects")
    if email:
        source_types.append("Official email")

    candidate = {
        "name": clean_text(name) or page_heading or "Research page",
        "entity_type": entity_type,
        "lead_contact_name": clean_text(lead_contact),
        "role_title": role_title or "",
        "university": university,
        "department_or_lab": department,
        "primary_source_url": url,
        "scholarly_profile_url": "",
        "official_profile_url": url,
        "department_page_url": department_page_url,
        "opportunity_page_url": opportunity_page_url if opportunity_page_url != url else "",
        "official_email": email,
        "email_source": email_source,
        "email_confidence": _email_confidence(clean_text(lead_contact or name), email, _regex_detect_emails(text), text),
        "opportunity_type": opportunity_type,
        "page_type": page_type,
        "page_type_label": PAGE_TYPE_LABELS.get(page_type, "Official research page"),
        "research_tags": research_tags[:8],
        "research_areas": _merge_ordered_unique(research_tags, discipline_tags, limit=8),
        "research_interests": _merge_ordered_unique(recent_topics, research_tags, limit=6),
        "discipline_tags": discipline_tags[:4],
        "publications": publications[:3],
        "project_signals": project_signals[:3],
        "recent_topics": recent_topics[:4],
        "student_signals": student_signals[:3],
        "opportunity_signals": opportunity_signals[:4],
        "activity_signals": activity_signals[:3],
        "academic_background": academic_background[:2],
        "profile_signal_count": profile_signal_count,
        "source_types": list(dict.fromkeys(source_types)),
        "profile_text": research_text,
        "bio_or_summary": " ".join(split_sentences(research_text)[:2])[:320],
        "raw_text_excerpt": text[:2600],
        "related_candidate_links": related_candidate_links,
        "official_enrichment_found": True,
        "source_credibility_label": source_credibility_label,
        "source_credibility_detail": source_credibility_detail,
        "page_word_count": len(text.split()),
        "attribution_confidence": "High" if email and _email_name_score(email, clean_text(lead_contact or name)) > 0 else "Moderate",
        "candidate_type": PERSON_BLOCK_TYPE if _looks_like_person_name(clean_text(lead_contact or name)) else page_type,
        "extraction_confidence": 64 if _looks_like_person_name(clean_text(lead_contact or name)) else 38,
        "warnings": [],
    }
    candidate["source_summary"] = _summarize_source_types(candidate)
    candidate["candidate_id"] = _candidate_uid(candidate)
    return _enforce_candidate_consistency(candidate)


def search_professor_opportunities(
    *,
    resume_result: dict,
    interests_text: str,
    target_region: str,
    academic_stage: str,
    opportunity_type: str,
    funding_required: bool,
    preferred_methods: list[str],
    existing_skills: str,
) -> dict:
    candidate_profile = _extract_candidate_profile(
        resume_result=resume_result,
        interests_text=interests_text,
        academic_stage=academic_stage,
        preferred_methods=preferred_methods,
        existing_skills=existing_skills,
        opportunity_type=opportunity_type,
        funding_required=funding_required,
    )
    candidate_profile["resume_result"] = resume_result
    candidate_profile["target_region"] = target_region

    scholarly_candidates, scholarly_counts, queries = _build_scholarly_candidates(candidate_profile)
    preliminary_candidates = [_score_candidate(candidate, candidate_profile) for candidate in scholarly_candidates]
    preliminary_candidates.sort(
        key=lambda candidate: (
            -candidate["research_fit_score"],
            -candidate["priority_score"],
            candidate["name"].lower(),
        )
    )

    enrichment_pool = preliminary_candidates[:12]
    enriched_candidates, official_source_counts, official_enrichment_count = _enrich_scholarly_candidates(enrichment_pool, candidate_profile)
    untouched_candidates = preliminary_candidates[12:]
    combined_candidates = enriched_candidates + untouched_candidates

    rescored_candidates = [_score_candidate(candidate, candidate_profile) for candidate in combined_candidates]
    best_by_identity: dict[tuple[str, str, str], dict] = {}
    for scored in rescored_candidates:
        identity = (
            scored.get("entity_type", "Research Match").lower(),
            (scored.get("lead_contact_name") or scored.get("name") or "").lower(),
            scored.get("university", "").lower(),
        )
        existing = best_by_identity.get(identity)
        if not existing or scored["priority_score"] > existing["priority_score"]:
            best_by_identity[identity] = scored

    ranked_candidates = list(best_by_identity.values())
    ranked_candidates.sort(
        key=lambda candidate: (
            -candidate["priority_score"],
            -candidate["research_fit_score"],
            -candidate["outreach_feasibility_score"],
            candidate["name"].lower(),
        )
    )

    eligible_candidates = [candidate for candidate in ranked_candidates if _eligible_by_alignment(candidate)]
    fallback_alignment_shortlist_used = False
    if not eligible_candidates and ranked_candidates:
        fallback_alignment_shortlist_used = True
        eligible_candidates = [candidate for candidate in ranked_candidates if candidate.get("research_fit_score", 0) >= 42][:8]
        if not eligible_candidates:
            eligible_candidates = ranked_candidates[:5]

    source_type_counts = Counter(official_source_counts)
    candidate_type_counts = Counter(candidate.get("page_type", "other") for candidate in eligible_candidates)
    errors: list[str] = []
    if scholarly_counts["scholarly_work_count"] == 0:
        errors.append("The scholarly discovery step did not find enough publication-backed signals for the current topic profile.")
    elif not ranked_candidates:
        errors.append("Scholarly works were found, but they did not yield enough researcher or institution evidence to build candidates.")
    elif official_enrichment_count == 0 and eligible_candidates:
        errors.append("The shortlist is built from scholarly research alignment because official faculty or lab enrichment stayed limited.")
    elif fallback_alignment_shortlist_used:
        errors.append("The shortlist was built from strong scholarly-fit signals because the evidence base stayed partial.")
    elif len(eligible_candidates) < 3:
        errors.append("Only a small set of usable research targets were found, so the shortlist is narrower than ideal.")

    summary = {
        "candidate_profile": candidate_profile,
        "queries": queries,
        "search_result_count": scholarly_counts["scholarly_work_count"],
        "trusted_result_count": scholarly_counts["scholarly_work_count"],
        "official_result_count": official_enrichment_count,
        "scholarly_work_count": scholarly_counts["scholarly_work_count"],
        "scholarly_candidate_count": scholarly_counts["scholarly_candidate_count"],
        "publication_backed_candidate_count": scholarly_counts["publication_backed_candidate_count"],
        "institution_count": scholarly_counts["institution_count"],
        "official_enrichment_count": official_enrichment_count,
        "faculty_page_count": source_type_counts.get("faculty_profile", 0),
        "lab_page_count": source_type_counts.get("lab_page", 0),
        "center_page_count": source_type_counts.get("center_page", 0),
        "department_page_count": source_type_counts.get("department_page", 0),
        "directory_page_count": source_type_counts.get("directory_page", 0),
        "opportunity_page_count": source_type_counts.get("opportunity_page", 0),
        "project_page_count": source_type_counts.get("project_page", 0),
        "publication_page_count": source_type_counts.get("publication_page", 0),
        "source_type_counts": dict(source_type_counts),
        "candidate_type_counts": dict(candidate_type_counts),
        "parsed_candidate_count": len(eligible_candidates),
        "official_email_count": sum(1 for candidate in eligible_candidates if candidate.get("official_email")),
        "recent_topic_profile_count": sum(1 for candidate in eligible_candidates if candidate.get("recent_topics")),
        "shortlist_count": len(eligible_candidates),
        "fallback_alignment_shortlist_used": fallback_alignment_shortlist_used,
        "errors": errors,
        "shortlist": eligible_candidates[:8],
    }
    return summary


def _normalize_target_url(target_url: str) -> str:
    cleaned = clean_text(target_url)
    if not cleaned:
        return ""
    if cleaned.startswith(("http://", "https://")):
        return cleaned
    return f"https://{cleaned}"


def _normalize_outreach_recommendation(label: str) -> str:
    if label in {"Save for later", "Low-priority contact"}:
        return "Low priority"
    return label


def _compute_research_confidence(candidate: dict, resume_result: dict) -> tuple[int, str, str]:
    score = 24
    if resume_result.get("success"):
        score += 18
    if len((resume_result.get("text") or "").split()) >= 120:
        score += 8
    score += min(18, candidate.get("profile_signal_count", 0) * 4)
    if candidate.get("official_profile_url"):
        score += 10
    if candidate.get("official_email"):
        score += 8
    if candidate.get("publications"):
        score += 8
    if candidate.get("recent_topics") or candidate.get("project_signals"):
        score += 6
    if candidate.get("source_credibility_label") == "High":
        score += 10
    elif candidate.get("source_credibility_label") == "Moderate":
        score += 5
    if candidate.get("related_pages_checked", 0):
        score += 4
    confidence_score = max(24, min(96, score))
    if confidence_score >= 78:
        return confidence_score, "High", "The decision is grounded in parsed CV evidence plus a strong source page or official enrichment."
    if confidence_score >= 58:
        return confidence_score, "Moderate", "The decision is usable, but some source or contact evidence is still incomplete."
    return confidence_score, "Low", "The decision is tentative because the page or CV evidence base is still limited."


def _collect_related_pages_for_target(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    base_domain = canonical_domain(base_url)
    related_pages: list[dict[str, str]] = []
    seen_urls: set[str] = set()
    keywords = (
        "contact",
        "email",
        "people",
        "faculty",
        "staff",
        "team",
        "member",
        "lab",
        "group",
        "research",
        "department",
        "directory",
        "profile",
    )
    for link in soup.find_all("a", href=True):
        href = urljoin(base_url, link.get("href", "").strip())
        normalized_url = _normalized_result_url(href)
        if not href or normalized_url in seen_urls:
            continue
        if not _same_domain_family(base_domain, canonical_domain(href)):
            continue
        anchor = clean_text(link.get_text(" ", strip=True))
        haystack = clean_text(f"{anchor} {href}").lower()
        if not any(keyword in haystack for keyword in keywords):
            continue
        related_pages.append({"url": href, "label": anchor or href})
        seen_urls.add(normalized_url)
        if len(related_pages) >= 6:
            break
    return related_pages


def _merge_target_fields(base: dict, related: dict) -> dict:
    merged = {**base}
    base_entity_type = merged.get("entity_type")
    base_name = _normalize_person_name(merged.get("lead_contact_name") or merged.get("name", ""))
    related_name = _normalize_person_name(related.get("lead_contact_name") or related.get("name", ""))
    if (
        base_name
        and related_name
        and _looks_like_person_name(base_name)
        and _looks_like_person_name(related_name)
        and not _names_compatible(base_name, related_name)
    ):
        return _enforce_candidate_consistency(merged)
    if related.get("page_type") == "faculty_profile":
        merged["lead_contact_name"] = related.get("lead_contact_name") or merged.get("lead_contact_name", "")
        if merged.get("entity_type") != "Professor":
            merged["entity_type"] = "Professor"
        if not merged.get("name") or base_entity_type in {"Directory", "Research page", "Research Match"}:
            merged["name"] = related.get("name") or merged.get("name", "")
    merged["role_title"] = related.get("role_title") or merged.get("role_title", "")
    if (
        related.get("department_or_lab")
        and merged.get("department_or_lab") in {"Official research context", "Research context from source page", "Scholarly research profile"}
    ):
        merged["department_or_lab"] = related["department_or_lab"]
    if related.get("official_email") and not merged.get("official_email"):
        merged["official_email"] = related["official_email"]
        merged["email_source"] = related.get("email_source", "")
        merged["email_confidence"] = related.get("email_confidence", merged.get("email_confidence", "missing"))
    if related.get("official_profile_url") and not merged.get("official_profile_url"):
        merged["official_profile_url"] = related["official_profile_url"]
    if related.get("department_page_url") and not merged.get("department_page_url"):
        merged["department_page_url"] = related["department_page_url"]
    if related.get("opportunity_page_url") and not merged.get("opportunity_page_url"):
        merged["opportunity_page_url"] = related["opportunity_page_url"]
    merged["research_tags"] = _merge_ordered_unique(base.get("research_tags", []), related.get("research_tags", []), limit=8)
    merged["research_areas"] = _merge_ordered_unique(base.get("research_areas", []), related.get("research_areas", []) or related.get("research_tags", []), limit=8)
    merged["research_interests"] = _merge_ordered_unique(base.get("research_interests", []), related.get("research_interests", []) or related.get("recent_topics", []), limit=6)
    merged["discipline_tags"] = _merge_ordered_unique(base.get("discipline_tags", []), related.get("discipline_tags", []), limit=4)
    merged["publications"] = _merge_ordered_unique(base.get("publications", []), related.get("publications", []), limit=3)
    merged["project_signals"] = _merge_ordered_unique(base.get("project_signals", []), related.get("project_signals", []), limit=3)
    merged["recent_topics"] = _merge_ordered_unique(base.get("recent_topics", []), related.get("recent_topics", []), limit=4)
    merged["student_signals"] = _merge_ordered_unique(base.get("student_signals", []), related.get("student_signals", []), limit=3)
    merged["opportunity_signals"] = _merge_ordered_unique(base.get("opportunity_signals", []), related.get("opportunity_signals", []), limit=4)
    merged["activity_signals"] = _merge_ordered_unique(base.get("activity_signals", []), related.get("activity_signals", []), limit=3)
    merged["academic_background"] = _merge_ordered_unique(base.get("academic_background", []), related.get("academic_background", []), limit=2)
    merged["source_types"] = list(dict.fromkeys(base.get("source_types", []) + related.get("source_types", []) + ["Related official page"]))
    merged["source_summary"] = _summarize_source_types(merged)
    merged["profile_signal_count"] = max(base.get("profile_signal_count", 0), related.get("profile_signal_count", 0))
    merged["profile_text"] = clean_text(" ".join([base.get("profile_text", ""), related.get("profile_text", "")]))
    merged["bio_or_summary"] = related.get("bio_or_summary") or merged.get("bio_or_summary", "")
    merged["raw_text_excerpt"] = related.get("raw_text_excerpt") or merged.get("raw_text_excerpt", "")
    merged["page_word_count"] = max(base.get("page_word_count", 0), related.get("page_word_count", 0))
    merged["related_candidate_links"] = base.get("related_candidate_links", []) or related.get("related_candidate_links", [])
    merged["source_credibility_label"] = related.get("source_credibility_label") or merged.get("source_credibility_label", "Limited")
    merged["source_credibility_detail"] = related.get("source_credibility_detail") or merged.get("source_credibility_detail", "")
    merged["attribution_confidence"] = related.get("attribution_confidence") or merged.get("attribution_confidence", "Moderate")
    merged["candidate_type"] = related.get("candidate_type") or merged.get("candidate_type", "")
    merged["extraction_confidence"] = max(base.get("extraction_confidence", 0), related.get("extraction_confidence", 0))
    merged["warnings"] = _merge_ordered_unique(base.get("warnings", []), related.get("warnings", []), limit=6)
    merged["candidate_id"] = _candidate_uid(merged)
    return _enforce_candidate_consistency(merged)


def _candidate_identity(candidate: dict) -> tuple[str, str]:
    return (
        clean_text(candidate.get("name", "")).lower(),
        clean_text(candidate.get("university", "")).lower(),
    )


def _build_page_context_from_html(url: str, soup: BeautifulSoup) -> dict:
    page_title = clean_text(soup.title.get_text(" ", strip=True)) if soup.title else ""
    text = extract_page_text(soup)
    page_heading = _guess_page_heading(soup, page_title)
    page_type = _classify_page_type(url, page_title, "", text)
    sections = _extract_heading_sections(soup)
    contacts = _extract_named_contacts(soup, text, page_title, page_type)
    name, entity_type, lead_contact = _determine_entity_name(page_type, page_heading, page_title, contacts)
    university = _guess_university(url, page_title)
    department = _guess_department(sections, text, page_heading)
    email, email_source = _find_mailto_email(soup, canonical_domain(url))
    if page_type in {"directory_page", "lab_page", "department_page", "center_page"} and len(contacts) > 1:
        email = ""
        email_source = ""
    department_page_url = _find_related_page(soup, url, ("department", "lab", "group", "research"))
    opportunity_page_url = _find_related_page(soup, url, ("opportunity", "apply", "join", "students", "opening", "research assistant"))
    research_tags = _extract_research_tags(text[:2600])
    publications = _extract_publications(soup, sections)
    project_signals = _extract_project_signals(sections)
    recent_topics = _extract_recent_topics(publications, project_signals, research_tags)
    activity_signals = _extract_activity_signals(text, publications, project_signals)
    discipline_tags = _extract_discipline_tags("\n".join([page_heading, department, text[:1600]]))
    source_credibility_label, source_credibility_detail = _source_credibility(url, page_type, text, page_title)
    role_title = _guess_role_title(text[:1400], lead_contact or name or page_heading)
    context = {
        "name": name or page_heading or page_title or "Research page",
        "entity_type": entity_type or "Research page",
        "lead_contact_name": lead_contact,
        "role_title": role_title or "",
        "university": university,
        "department_or_lab": department,
        "primary_source_url": url,
        "official_profile_url": url if source_credibility_label in {"High", "Moderate"} else "",
        "department_page_url": department_page_url,
        "opportunity_page_url": opportunity_page_url if opportunity_page_url != url else "",
        "official_email": email,
        "email_source": email_source,
        "email_confidence": _email_confidence(clean_text(lead_contact or name), email, _regex_detect_emails(text), text),
        "opportunity_type": _infer_opportunity_type(page_type, text),
        "page_type": page_type,
        "page_type_label": PAGE_TYPE_LABELS.get(page_type, "Research page"),
        "research_tags": research_tags[:8],
        "research_areas": _merge_ordered_unique(research_tags, discipline_tags, limit=8),
        "research_interests": _merge_ordered_unique(recent_topics, research_tags, limit=6),
        "discipline_tags": discipline_tags[:4],
        "publications": publications[:3],
        "project_signals": project_signals[:3],
        "recent_topics": recent_topics[:4],
        "student_signals": _extract_student_signals(text),
        "opportunity_signals": _extract_opportunity_signals(text, sections, page_type),
        "activity_signals": activity_signals[:3],
        "academic_background": _extract_academic_background(sections, text)[:2],
        "profile_signal_count": sum([bool(research_tags), bool(discipline_tags), bool(publications or project_signals or recent_topics), bool(email)]),
        "source_types": [PAGE_TYPE_LABELS.get(page_type, "Research page")],
        "profile_text": text[:2600],
        "bio_or_summary": " ".join(split_sentences(text[:1200])[:2])[:320],
        "raw_text_excerpt": text[:2600],
        "related_candidate_links": _extract_related_candidate_links(soup, url, page_type),
        "official_enrichment_found": bool(email),
        "source_credibility_label": source_credibility_label,
        "source_credibility_detail": source_credibility_detail,
        "page_word_count": len(text.split()),
        "attribution_confidence": "Moderate",
        "candidate_type": PERSON_BLOCK_TYPE if _looks_like_person_name(clean_text(lead_contact or name)) else page_type,
        "extraction_confidence": 58 if _looks_like_person_name(clean_text(lead_contact or name)) else 34,
        "warnings": [],
        "source_summary": "",
    }
    context["source_summary"] = _summarize_source_types(context)
    context["candidate_id"] = _candidate_uid(context)
    return context


def _enrich_url_candidate(candidate: dict, base_url: str, university_hint: str = "") -> tuple[dict, int, list[str]]:
    enriched = {**candidate}
    checked = 0
    used_urls: list[str] = []
    urls_to_try: list[str] = []
    profile_url = clean_text(candidate.get("official_profile_url", ""))
    if profile_url and profile_url != base_url:
        urls_to_try.append(profile_url)
    department_url = clean_text(candidate.get("department_page_url", ""))
    if department_url and department_url != base_url and department_url not in urls_to_try:
        urls_to_try.append(department_url)

    base_domain = canonical_domain(base_url)
    if (not urls_to_try or not enriched.get("official_email")) and clean_text(candidate.get("name", "")):
        query = clean_text(f'"{candidate.get("name", "")}" "{university_hint or candidate.get("university", "")}" faculty research')
        for result in search_duckduckgo_html(query, max_results=6):
            url = clean_text(result.get("url", ""))
            if not url or not _looks_trustworthy_research_result(url, result.get("title", ""), result.get("snippet", "")):
                continue
            if base_domain and not _same_domain_family(base_domain, canonical_domain(url)):
                continue
            if not _result_matches_candidate(result, candidate):
                continue
            if url not in urls_to_try:
                urls_to_try.append(url)
            if len(urls_to_try) >= 4:
                break

    for url in urls_to_try[:4]:
        checked += 1
        parsed = _parse_research_page(
            {
                "url": url,
                "title": candidate.get("name", ""),
                "snippet": "",
                "source_type": _classify_page_type(url, candidate.get("name", ""), ""),
            },
            allow_non_official=True,
            min_words=20,
        )
        if not parsed:
            continue
        expected_name = clean_text(candidate.get("lead_contact_name") or candidate.get("name", ""))
        parsed_name = clean_text(parsed.get("lead_contact_name") or parsed.get("name", ""))
        if expected_name and parsed_name and not _names_compatible(expected_name, parsed_name):
            continue
        enriched = _merge_target_fields(enriched, parsed)
        used_urls.append(url)
        if enriched.get("official_email") and (enriched.get("publications") or enriched.get("recent_topics")):
            break

    enriched["related_pages_checked"] = checked
    enriched["related_pages_used"] = used_urls
    enriched["source_summary"] = _summarize_source_types(enriched)
    enriched["candidate_id"] = _candidate_uid(enriched)
    return enriched, checked, used_urls


def parse_research_target_url(target_url: str) -> dict | None:
    normalized_url = _normalize_target_url(target_url)
    if not normalized_url:
        return None

    html_text, _error = fetch_page_best_effort(normalized_url)
    if not html_text:
        return None

    soup = try_bs4(html_text)
    page_text = extract_page_text(soup)
    page_context = _build_page_context_from_html(normalized_url, soup)
    parser_report = _new_parser_report(normalized_url, page_context, page_text)
    if parser_report["page_word_count"] < 60:
        _record_parser_category(
            parser_report,
            "source_page_text_too_sparse",
            "The fetched page contains limited readable text, so person and topic extraction may be weak.",
        )
    base_result = _parse_research_page({"url": normalized_url, "title": "", "snippet": "", "source_type": ""}, allow_non_official=True, min_words=20)
    if base_result:
        page_context = _merge_target_fields(page_context, base_result)
        page_context["primary_source_url"] = normalized_url
        page_context["source_summary"] = _summarize_source_types(page_context)

    dom_candidates = _extract_multi_profile_candidates(soup, normalized_url, page_context)
    text_candidates = _extract_text_profile_candidates(page_text, normalized_url, page_context)
    primary_profile_candidate = _extract_primary_profile_candidate(soup, normalized_url, page_context)
    parser_report["raw_person_block_count"] = len(dom_candidates)
    parser_report["visible_text_candidate_count"] = len(text_candidates)
    multi_candidates = _merge_person_candidates(dom_candidates + text_candidates + ([primary_profile_candidate] if primary_profile_candidate else []))
    contact_names = _extract_named_contacts(
        soup,
        page_text,
        page_context.get("name", ""),
        page_context.get("page_type", "other"),
    )
    parser_report["contact_names"] = contact_names[:10]
    parser_report["candidate_objects_built_count"] = len(multi_candidates)
    parser_report["candidate_names"] = [candidate.get("name", "") for candidate in multi_candidates]
    parser_report["candidate_emails"] = [candidate.get("official_email", "") for candidate in multi_candidates if candidate.get("official_email")]
    parser_report["candidate_snapshots"] = [_candidate_debug_snapshot(candidate) for candidate in multi_candidates[:8]]
    parser_report["person_level_extraction_succeeded"] = bool(multi_candidates)
    directory_like_page = page_context.get("page_type") in {"directory_page", "lab_page", "department_page", "center_page"} or any(
        token in clean_text(page_context.get("name", "")).lower()
        for token in ("people", "faculty", "staff", "team", "members", "directory")
    )
    multi_profile_detected = directory_like_page and (len(multi_candidates) >= 2 or len(contact_names) >= 2)
    parser_report["multi_profile_detected"] = multi_profile_detected
    if not dom_candidates and not text_candidates and not primary_profile_candidate:
        _record_parser_category(
            parser_report,
            "no_person_block_found",
            "No person-specific blocks or visible text profiles were confidently extracted from the page.",
        )
    if directory_like_page and len(contact_names) >= 2 and len(multi_candidates) < 2:
        _record_parser_category(
            parser_report,
            "multi_profile_page_not_split",
            "The page looks like a multi-person directory, but the parser did not build enough separate person candidates.",
            severity="failure",
        )
    if parser_report["page_language"] in {"Chinese", "Mixed"} and not any(_contains_cjk(candidate.get("name", "")) for candidate in multi_candidates):
        _record_parser_category(
            parser_report,
            "chinese_name_not_detected",
            "The page appears Chinese or bilingual, but no person candidate with a Chinese name was extracted.",
        )
    if any(_name_has_field_label_pollution(candidate.get("name", "")) for candidate in dom_candidates + text_candidates):
        _record_parser_category(
            parser_report,
            "candidate_name_polluted_by_field_label",
            "At least one raw candidate name contained label or field-text pollution before normalization.",
        )
    page_visible_emails = _extract_all_emails(page_text)
    if page_visible_emails and not parser_report["candidate_emails"] and not page_context.get("official_email"):
        _record_parser_category(
            parser_report,
            "email_found_but_not_attributed",
            "Visible emails were present on the page, but they were not attributed to a person candidate confidently.",
        )
    elif not page_visible_emails and not parser_report["candidate_emails"] and not page_context.get("official_email"):
        _record_parser_category(
            parser_report,
            "email_not_found",
            "No attributable email was found on the source page.",
        )
    if multi_profile_detected:
        return {
            "multi_profile_detected": True,
            "page_context": page_context,
            "source_page_word_count": page_context.get("page_word_count", 0),
            "candidates": multi_candidates,
            "extracted_candidate_count": len(multi_candidates),
            "target_url": normalized_url,
            "parser_report": parser_report,
        }

    base_result = _enforce_candidate_consistency(base_result or page_context)
    if not _is_person_candidate(base_result) and len(contact_names) == 1:
        _record_parser_category(
            parser_report,
            "single_profile_not_identified",
            "Only one visible contact-like name was found, but the page did not initially resolve to a single person candidate.",
        )
    if not _is_person_candidate(base_result) and len(contact_names) == 1 and not _looks_like_container_label(contact_names[0]):
        base_result["name"] = contact_names[0]
        base_result["lead_contact_name"] = contact_names[0]
        if base_result.get("entity_type") in {"Directory", "Research page", "Research Match"}:
            role_title = clean_text(base_result.get("role_title", "")).lower()
            base_result["entity_type"] = "Professor" if "professor" in role_title else "Researcher"
        base_result = _enforce_candidate_consistency(base_result)
        parser_report["fallback_path_used"] = "single_contact_promotion"
    if not _is_person_candidate(base_result) and multi_candidates:
        base_result = _enforce_candidate_consistency(multi_candidates[0])
        parser_report["fallback_path_used"] = "first_person_candidate"
    related_pages_checked = 0
    related_pages_used: list[str] = []
    if base_result.get("source_credibility_label") == "Limited":
        base_result["official_profile_url"] = ""
    base_result["primary_source_url"] = normalized_url
    base_result["related_pages_checked"] = 0
    base_result["related_pages_used"] = []

    if soup is not None:
        for related_page in _collect_related_pages_for_target(soup, normalized_url):
            related_pages_checked += 1
            parsed_related = _parse_research_page(
                {
                    "url": related_page["url"],
                    "title": related_page["label"],
                    "snippet": "",
                    "source_type": _classify_page_type(related_page["url"], related_page["label"], ""),
                },
                allow_non_official=True,
                min_words=20,
            )
            if not parsed_related:
                continue
            base_result = _merge_target_fields(base_result, parsed_related)
            related_pages_used.append(related_page["url"])
            if base_result.get("official_email") and base_result.get("official_profile_url"):
                break

    base_result["related_pages_checked"] = related_pages_checked
    base_result["related_pages_used"] = related_pages_used
    base_result["source_summary"] = _summarize_source_types(base_result)
    parser_report["related_pages_checked"] = related_pages_checked
    parser_report["related_pages_used"] = related_pages_used
    parser_report["official_email_found"] = bool(base_result.get("official_email"))
    parser_report["selected_candidate_id"] = base_result.get("candidate_id", "")
    parser_report["selected_candidate_name"] = base_result.get("name", "")
    parser_report["selected_candidate_email"] = base_result.get("official_email", "")
    parser_report["selected_candidate_title"] = base_result.get("role_title", "")
    parser_report["selected_candidate_profile_url"] = base_result.get("official_profile_url") or base_result.get("primary_source_url", "")
    parser_report["selected_candidate_person_like"] = _is_person_candidate(base_result)
    if parser_report["linked_profile_candidate_count"] and not related_pages_checked:
        _record_parser_category(
            parser_report,
            "linked_profile_not_followed",
            "The page exposed related same-domain profile links, but none were followed during fallback parsing.",
        )
    if not _is_person_candidate(base_result):
        parser_report["page_level_fallback_used"] = True
        parser_report["page_title_fallback_used"] = True
        parser_report["fallback_path_used"] = parser_report["fallback_path_used"] or "page_context_fallback"
        _record_parser_category(
            parser_report,
            "fallback_to_generic_target",
            "The final target still relies on page-level context because no reliable person candidate was extracted.",
            severity="failure",
        )
    elif _looks_like_generic_target_label(base_result.get("name", "")):
        parser_report["page_title_fallback_used"] = True
        _record_parser_category(
            parser_report,
            "page_title_fallback_used",
            "The final target name still looks like a page-level label rather than a person.",
            severity="failure",
        )
    return {
        "multi_profile_detected": False,
        "page_context": page_context,
        "source_page_word_count": base_result.get("page_word_count", 0),
        "candidates": [base_result],
        "extracted_candidate_count": 1 if base_result else 0,
        "target_url": normalized_url,
        "parser_report": parser_report,
    }


def analyze_research_target(
    *,
    target_url: str,
    resume_result: dict,
    interests_text: str,
    target_region: str,
    academic_stage: str,
    opportunity_type: str,
    funding_required: bool,
    preferred_methods: list[str],
    existing_skills: str,
) -> dict:
    candidate_profile = _extract_candidate_profile(
        resume_result=resume_result,
        interests_text=interests_text,
        academic_stage=academic_stage,
        preferred_methods=preferred_methods,
        existing_skills=existing_skills,
        opportunity_type=opportunity_type,
        funding_required=funding_required,
    )
    candidate_profile["resume_result"] = resume_result
    candidate_profile["target_url"] = _normalize_target_url(target_url)
    candidate_profile["target_region"] = target_region

    target_parse = parse_research_target_url(target_url)
    errors: list[str] = []
    if not target_parse:
        errors.append("The provided research URL could not be parsed into a trustworthy target profile.")
        return {
            "candidate_profile": candidate_profile,
            "target_url": _normalize_target_url(target_url),
            "shortlist": [],
            "parsed_candidate_count": 0,
            "official_email_count": 0,
            "recent_topic_profile_count": 0,
            "errors": errors,
            "source_type_counts": {},
            "candidate_type_counts": {},
            "trusted_result_count": 0,
            "official_result_count": 0,
            "source_page_parsed": False,
            "source_page_word_count": 0,
            "source_credibility_label": "Limited",
            "source_credibility_detail": "The provided URL did not yield enough readable source content.",
            "related_pages_checked": 0,
            "related_pages_used": [],
            "multi_profile_detected": False,
            "extracted_candidate_count": 0,
            "parser_report": {
                "input_url": _normalize_target_url(target_url),
                "failure_categories": ["source_page_text_too_sparse"],
                "warning_categories": [],
                "events": [
                    {
                        "category": "source_page_text_too_sparse",
                        "detail": "The target page could not be fetched or did not yield enough readable content.",
                        "severity": "failure",
                    }
                ],
            },
        }

    normalized_target = _normalize_target_url(target_url)
    page_context = target_parse.get("page_context", {})
    parser_report = {**target_parse.get("parser_report", {})}
    raw_candidates = target_parse.get("candidates", [])
    ranked_candidates: list[dict] = []
    related_pages_checked_total = 0
    related_pages_used: list[str] = []
    best_by_identity: dict[tuple[str, str], dict] = {}

    for candidate in raw_candidates:
        enriched_candidate, checked, used = _enrich_url_candidate(_enforce_candidate_consistency(candidate), normalized_target, page_context.get("university", ""))
        related_pages_checked_total += checked
        related_pages_used.extend(used)
        scored = _score_candidate(_enforce_candidate_consistency(enriched_candidate), candidate_profile)
        scored["recommendation"] = _normalize_outreach_recommendation(scored["recommendation"])
        confidence_score, confidence_label, confidence_note = _compute_research_confidence(scored, resume_result)
        scored["confidence_score"] = confidence_score
        scored["confidence_label"] = confidence_label
        scored["confidence_note"] = confidence_note
        scored["primary_source_url"] = candidate.get("primary_source_url") or enriched_candidate.get("primary_source_url") or normalized_target
        scored["target_url"] = normalized_target
        scored["related_pages_checked"] = checked
        scored["related_pages_used"] = used
        scored["candidate_id"] = scored.get("candidate_id") or _candidate_uid(scored)
        identity = (scored["candidate_id"], clean_text(scored.get("official_email", "")).lower())
        existing = best_by_identity.get(identity)
        if not existing or scored.get("priority_score", 0) > existing.get("priority_score", 0):
            best_by_identity[identity] = scored

    ranked_candidates = list(best_by_identity.values())
    person_candidates = [candidate for candidate in ranked_candidates if _is_person_candidate(candidate)]
    if person_candidates:
        ranked_candidates = person_candidates
    ranked_candidates.sort(
        key=lambda candidate: (
            -candidate.get("priority_score", 0),
            -candidate.get("research_fit_score", 0),
            -candidate.get("outreach_feasibility_score", 0),
            candidate.get("name", "").lower(),
        )
    )

    eligible_candidates = [candidate for candidate in ranked_candidates if _eligible_by_alignment(candidate)]
    if not eligible_candidates and ranked_candidates:
        eligible_candidates = [
            candidate
            for candidate in ranked_candidates
            if candidate.get("profile_evidence_count", 0) >= 2 and candidate.get("research_fit_score", 0) >= 36
        ]
    if not eligible_candidates and ranked_candidates:
        eligible_candidates = ranked_candidates[: min(6, len(ranked_candidates))]

    if not eligible_candidates:
        errors.append("The provided page was parsed, but no plausible researcher candidates could be extracted from it.")
        _record_parser_category(
            parser_report,
            "fallback_to_generic_target",
            "The parser could not build a usable person-level target from the provided page.",
            severity="failure",
        )
        return {
            "candidate_profile": candidate_profile,
            "target_url": normalized_target,
            "shortlist": [],
            "parsed_candidate_count": 0,
            "official_email_count": 0,
            "recent_topic_profile_count": 0,
            "errors": errors,
            "source_type_counts": {},
            "candidate_type_counts": {},
            "trusted_result_count": 1,
            "official_result_count": 0,
            "source_page_parsed": True,
            "source_page_word_count": target_parse.get("source_page_word_count", 0),
            "source_credibility_label": page_context.get("source_credibility_label", "Limited"),
            "source_credibility_detail": page_context.get("source_credibility_detail", ""),
            "related_pages_checked": related_pages_checked_total,
            "related_pages_used": related_pages_used,
            "multi_profile_detected": target_parse.get("multi_profile_detected", False),
            "extracted_candidate_count": target_parse.get("extracted_candidate_count", len(raw_candidates)),
            "parser_report": parser_report,
        }

    top_candidate = eligible_candidates[0]
    parser_report["selected_candidate_id"] = top_candidate.get("candidate_id", "")
    parser_report["selected_candidate_name"] = top_candidate.get("name", "")
    parser_report["selected_candidate_email"] = top_candidate.get("official_email", "")
    parser_report["selected_candidate_title"] = top_candidate.get("role_title", "")
    parser_report["selected_candidate_profile_url"] = top_candidate.get("official_profile_url") or top_candidate.get("primary_source_url", "")
    parser_report["selected_candidate_person_like"] = _is_person_candidate(top_candidate)
    parser_report["related_pages_checked"] = related_pages_checked_total
    parser_report["related_pages_used"] = list(dict.fromkeys(related_pages_used))
    parser_report["official_email_found"] = bool(top_candidate.get("official_email"))
    binding_issues = _selected_binding_issues(top_candidate)
    if binding_issues:
        parser_report["candidate_binding_valid"] = False
        for issue in binding_issues:
            _record_parser_category(
                parser_report,
                issue,
                "The selected candidate still shows a name, title, or email consistency issue.",
                severity="failure" if issue == "selected_candidate_binding_mismatch" else "warning",
            )
    else:
        parser_report["candidate_binding_valid"] = True
    if not _is_person_candidate(top_candidate):
        _record_parser_category(
            parser_report,
            "fallback_to_generic_target",
            "The top-ranked result is still not a person-level target.",
            severity="failure",
        )
    if not any(candidate.get("publications") or candidate.get("project_signals") for candidate in eligible_candidates):
        _record_parser_category(
            parser_report,
            "publication_data_missing",
            "Recent publications or project outputs were limited across the extracted candidates.",
        )
    if parser_report.get("linked_profile_candidate_count", 0) and related_pages_checked_total == 0:
        _record_parser_category(
            parser_report,
            "linked_profile_not_followed",
            "The source page exposed related profile links, but no additional pages were checked during enrichment.",
        )
    if not any(candidate.get("official_email") for candidate in eligible_candidates):
        errors.append("Email not found from official or clearly attributable sources for the extracted targets.")
    if not any(candidate.get("publications") or candidate.get("project_signals") for candidate in eligible_candidates):
        errors.append("Recent papers or project outputs were limited across the extracted targets.")
    if top_candidate.get("source_credibility_label") == "Limited":
        errors.append("Source credibility is limited, so the ranking should be treated cautiously.")
    if target_parse.get("multi_profile_detected"):
        errors.append("Multiple targets were found on the provided page. The shortlist below is ranked from best match to weakest match.")

    source_type_counts = Counter(candidate.get("page_type", "other") for candidate in eligible_candidates)
    candidate_type_counts = Counter(candidate.get("entity_type", "Research Match") for candidate in eligible_candidates)

    return {
        "candidate_profile": candidate_profile,
        "target_url": normalized_target,
        "source_page_parsed": True,
        "source_page_word_count": target_parse.get("source_page_word_count", 0),
        "source_credibility_label": page_context.get("source_credibility_label", "Limited"),
        "source_credibility_detail": page_context.get("source_credibility_detail", ""),
        "related_pages_checked": related_pages_checked_total,
        "related_pages_used": list(dict.fromkeys(related_pages_used)),
        "queries": [],
        "search_result_count": max(1, len(raw_candidates)),
        "trusted_result_count": len(raw_candidates) if target_parse.get("multi_profile_detected") else 1,
        "official_result_count": sum(1 for candidate in eligible_candidates if candidate.get("official_profile_url")),
        "faculty_page_count": source_type_counts.get("faculty_profile", 0),
        "lab_page_count": source_type_counts.get("lab_page", 0),
        "center_page_count": source_type_counts.get("center_page", 0),
        "department_page_count": source_type_counts.get("department_page", 0),
        "directory_page_count": source_type_counts.get("directory_page", 0),
        "opportunity_page_count": source_type_counts.get("opportunity_page", 0),
        "project_page_count": source_type_counts.get("project_page", 0),
        "publication_page_count": sum(1 for candidate in eligible_candidates if candidate.get("publications")),
        "source_type_counts": dict(source_type_counts),
        "candidate_type_counts": dict(candidate_type_counts),
        "parsed_candidate_count": len(eligible_candidates),
        "official_email_count": sum(1 for candidate in eligible_candidates if candidate.get("official_email")),
        "recent_topic_profile_count": sum(1 for candidate in eligible_candidates if candidate.get("recent_topics") or candidate.get("publications") or candidate.get("project_signals")),
        "shortlist_count": len(eligible_candidates),
        "errors": errors,
        "shortlist": eligible_candidates[:10],
        "target": top_candidate,
        "selected_candidate_id": top_candidate.get("candidate_id", ""),
        "multi_profile_detected": target_parse.get("multi_profile_detected", False),
        "extracted_candidate_count": target_parse.get("extracted_candidate_count", len(raw_candidates)),
        "parser_report": parser_report,
    }
