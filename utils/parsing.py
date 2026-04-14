from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup

from utils.helpers import clean_text, contains_any, extract_keywords, split_sentences

FALLBACK_PAGE_PATTERNS = ["/about", "/about-us", "/company", "/careers", "/jobs", "/contact", "/legal", "/terms", "/privacy"]
JOB_HEADINGS = {
    "role_summary": ["about the role", "role summary", "about the job", "position summary", "overview"],
    "responsibilities": ["responsibilities", "what you will do", "you will", "role duties", "day-to-day"],
    "requirements": ["requirements", "what we're looking for", "what you need", "qualifications", "must have", "who you are"],
    "preferred_qualifications": ["nice to have", "preferred", "desirable", "would be great", "additional skills"],
    "benefits": ["benefits", "what we offer", "what you'll get", "perks", "compensation", "salary"],
    "location": ["location", "based in", "remote", "hybrid", "work arrangement"],
}


def _try_bs4(html_text: str) -> BeautifulSoup:
    for parser in ("lxml", "html.parser"):
        try:
            return BeautifulSoup(html_text, parser)
        except Exception:
            continue
    return BeautifulSoup(html_text, "html.parser")


def _fetch_page(url: str, timeout: int = 10) -> tuple[str, str]:
    try:
        response = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
                )
            },
        )
        response.raise_for_status()
        return response.text, ""
    except Exception as exc:
        return "", str(exc)


def _fetch_page_with_browser(url: str) -> tuple[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return "", f"Playwright is not installed: {exc}"

    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=20000)
            content = page.content()
            page.close()
            browser.close()
            return content, ""
    except Exception as exc:
        return "", str(exc)


def _extract_page_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()

    main_block = soup.find("main") or soup.find("article") or soup.body or soup
    return clean_text(main_block.get_text("\n", strip=True))


def _extract_headings(soup: BeautifulSoup) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    for heading_tag in soup.find_all(re.compile(r"^h[1-4]$")):
        heading = clean_text(heading_tag.get_text())
        if not heading:
            continue
        content_lines: list[str] = []
        for sibling in heading_tag.find_next_siblings():
            if sibling.name and re.fullmatch(r"h[1-4]", sibling.name.lower()):
                break
            if sibling.name in {"script", "style", "nav", "footer", "header", "noscript", "svg", "form"}:
                continue
            text = clean_text(sibling.get_text(separator=" ", strip=True))
            if text:
                content_lines.append(text)
        sections.append((heading, clean_text("\n".join(content_lines))))
    return sections


def _find_section_by_keywords(sections: list[tuple[str, str]], keywords: list[str]) -> str:
    for heading, content in sections:
        normalized = heading.lower()
        if any(keyword in normalized for keyword in keywords):
            return content
    return ""


def _extract_block_from_text(text: str, markers: list[str], limit: int = 1400) -> str:
    lower = text.lower()
    for marker in markers:
        index = lower.find(marker)
        if index != -1:
            return clean_text(text[index : index + limit])
    return ""


def _extract_company_and_title(page_title: str, headings: list[tuple[str, str]], domain: str, soup: BeautifulSoup) -> tuple[str, str]:
    title = clean_text(page_title or "")
    heading_title = headings[0][0] if headings else ""
    job_title = heading_title or title
    company_name = ""

    if title:
        if "|" in title or "-" in title or "–" in title or ":" in title:
            parts = [part.strip() for part in re.split(r"[\|\-–:]+", title) if part.strip()]
            if len(parts) >= 2:
                if len(parts[0].split()) <= len(parts[-1].split()):
                    job_title = parts[0]
                    company_name = parts[-1]
                else:
                    job_title = parts[-1]
                    company_name = parts[0]

    if not company_name:
        for meta_key in ("og:site_name", "application-name", "twitter:title", "og:title"):
            meta = soup.find("meta", property=meta_key) or soup.find("meta", attrs={"name": meta_key})
            if meta and meta.get("content"):
                company_name = clean_text(meta["content"])
                break

    if not company_name:
        company_name = domain
    return clean_text(company_name), clean_text(job_title)


def _extract_location_and_mode(text: str) -> tuple[str, str]:
    lowered = text.lower()
    if "remote" in lowered and "hybrid" in lowered:
        return "Remote or hybrid", "Remote/Hybrid"
    if "remote" in lowered:
        return "Remote", "Remote"
    if "hybrid" in lowered:
        return "Hybrid", "Hybrid"
    if "on-site" in lowered or "onsite" in lowered:
        return "On-site", "On-site"
    location_match = re.search(r"(?:based in|location[:]?|office in|working from|located in)\s+([A-Za-z0-9 ,\-]+)", text, re.I)
    if location_match:
        return clean_text(location_match.group(1)), "On-site"
    return "Not specified", "Not specified"


def _extract_skills(text: str) -> list[str]:
    keywords = extract_keywords(text, limit=30)
    return sorted({keyword for keyword in keywords if len(keyword) > 1})


def _build_structured_job_data(text: str, title: str, domain: str, sections: list[tuple[str, str]], same_domain_pages: list[dict]) -> dict:
    role_summary = _find_section_by_keywords(sections, JOB_HEADINGS["role_summary"]) or _extract_block_from_text(text, ["about the role", "role summary", "overview", "what you will do"], limit=500)
    responsibilities = _find_section_by_keywords(sections, JOB_HEADINGS["responsibilities"]) or _extract_block_from_text(text, ["responsibilities", "what you will do", "you will"], limit=700)
    requirements = _find_section_by_keywords(sections, JOB_HEADINGS["requirements"]) or _extract_block_from_text(text, ["requirements", "qualifications", "must have", "what we're looking for"], limit=700)
    preferred = _find_section_by_keywords(sections, JOB_HEADINGS["preferred_qualifications"]) or _extract_block_from_text(text, ["nice to have", "preferred", "desirable", "would be great"], limit=400)
    benefits = _find_section_by_keywords(sections, JOB_HEADINGS["benefits"]) or _extract_block_from_text(text, ["benefits", "what we offer", "perks", "salary", "compensation"], limit=400)
    location, work_mode = _extract_location_and_mode(text)
    required_skills = _extract_skills(f"{responsibilities}\n{requirements}\n{text}")
    preferred_skills = _extract_skills(f"{preferred}\n{text}")

    clarity = "Vague"
    if responsibilities and requirements:
        clarity = "Clear"
    elif responsibilities or requirements:
        clarity = "Partial"

    evidence_quality = "Minimal"
    if same_domain_pages and len(same_domain_pages) >= 2:
        evidence_quality = "Good"
    elif same_domain_pages:
        evidence_quality = "Limited"

    if not role_summary:
        first_sentences = split_sentences(text)
        role_summary = " ".join(first_sentences[:2]) if first_sentences else "No clear role summary was found."

    return {
        "company_name": "",
        "job_title": title,
        "role_summary": clean_text(role_summary),
        "responsibilities": clean_text(responsibilities),
        "requirements": clean_text(requirements),
        "required_skills": required_skills,
        "preferred_skills": preferred_skills,
        "benefits": clean_text(benefits),
        "location": location,
        "work_mode": work_mode,
        "posting_clarity": clarity,
        "evidence_quality": evidence_quality,
        "external_sentiment": "Not fetched",
    }


def _find_same_domain_pages(base_url: str, soup: BeautifulSoup, domain: str) -> list[dict]:
    seen: set[str] = set()
    pages: list[dict] = []
    for link in soup.find_all("a", href=True):
        href = link["href"].strip()
        if not href:
            continue
        if href.startswith("//"):
            href = f"https:{href}"
        if href.startswith("http"):
            parsed = urlparse(href)
            if parsed.netloc != domain:
                continue
            link_url = href
        elif href.startswith("/"):
            link_url = urljoin(base_url, href)
        else:
            continue

        if link_url in seen or len(pages) >= 3:
            continue

        path = urlparse(link_url).path.lower()
        if any(pattern in path for pattern in FALLBACK_PAGE_PATTERNS):
            pages.append({"url": link_url, "path": path, "title": clean_text(link.get_text())})
            seen.add(link_url)

    return pages


def _fetch_same_domain_pages(base_url: str, soup: BeautifulSoup, domain: str) -> list[dict]:
    candidates = _find_same_domain_pages(base_url, soup, domain)
    results: list[dict] = []
    for item in candidates[:3]:
        page_text, error = _fetch_page(item["url"])
        if not page_text and "Playwright" in error:
            page_text, error = _fetch_page_with_browser(item["url"])
        clean_page = clean_text(page_text) if page_text else ""
        results.append(
            {
                "url": item["url"],
                "title": item.get("title") or "",
                "success": bool(clean_page),
                "text": clean_page,
                "error": error,
            }
        )
    return results


def _parse_structured_text(text: str, page_title: str, soup: BeautifulSoup, domain: str) -> dict:
    headings = _extract_headings(soup)
    company_name, job_title = _extract_company_and_title(page_title, headings, domain, soup)
    same_domain_pages = _fetch_same_domain_pages(domain and f"https://{domain}" or "", soup, domain)
    structured = _build_structured_job_data(text, job_title, domain, headings, same_domain_pages)
    structured["company_name"] = company_name
    structured["job_title"] = job_title
    structured["same_domain_pages"] = same_domain_pages
    return structured


def looks_like_job_text(text: str) -> bool:
    lower = text.lower()
    return bool(
        len(text.split()) >= 100
        and any(keyword in lower for keyword in ["responsibilities", "requirements", "qualifications", "what you will do", "about the role"])
    )


def _extract_resume_sections(text: str) -> dict[str, str]:
    sections = {
        "education": "",
        "experience": "",
        "skills": "",
        "certifications": "",
        "projects": "",
        "other": "",
    }
    current_section = "other"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = line.lower()
        if re.match(r"^(education|academic background|qualifications?)[:\-]?$", normalized):
            current_section = "education"
            continue
        if re.match(r"^(experience|work experience|professional experience|employment history|career history)[:\-]?$", normalized):
            current_section = "experience"
            continue
        if re.match(r"^(skills|technical skills|key skills|competencies)[:\-]?$", normalized):
            current_section = "skills"
            continue
        if re.match(r"^(certifications|certificates|licenses)[:\-]?$", normalized):
            current_section = "certifications"
            continue
        if re.match(r"^(projects|project work|selected projects)[:\-]?$", normalized):
            current_section = "projects"
            continue

        sections[current_section] += f"{line}\n"

    return {key: clean_text(value) for key, value in sections.items()}


def parse_resume_text(text: str) -> dict[str, Any]:
    cleaned = clean_text(text)
    sections = _extract_resume_sections(cleaned)
    return {
        "success": bool(cleaned),
        "text": cleaned,
        "page_count": 0,
        "sections": sections,
        "error": "" if cleaned else "No resume text was provided.",
        "fallback_used": False,
    }


def parse_resume_pdf(pdf_bytes: bytes) -> dict[str, Any]:
    try:
        import fitz
    except ImportError as exc:
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "sections": {"education": "", "experience": "", "skills": "", "certifications": "", "projects": "", "other": ""},
            "error": f"PyMuPDF is not installed: {exc}",
            "fallback_used": False,
        }

    try:
        document = fitz.open(stream=pdf_bytes, filetype="pdf")
        raw_pages = [page.get_text("text") for page in document]
        text = clean_text("\n\n".join(raw_pages))
        sections = _extract_resume_sections(text)
        success = bool(text and len(text.split()) >= 5)
        return {
            "success": success,
            "text": text,
            "page_count": len(document),
            "sections": sections,
            "error": "" if success else "PDF did not yield usable text.",
            "fallback_used": False,
        }
    except Exception as exc:
        return {
            "success": False,
            "text": "",
            "page_count": 0,
            "sections": {"education": "", "experience": "", "skills": "", "certifications": "", "projects": "", "other": ""},
            "error": str(exc),
            "fallback_used": False,
        }


@lru_cache(maxsize=24)
def scrape_job_url(url: str) -> dict:
    result = {
        "attempted": True,
        "success": False,
        "text": "",
        "title": "",
        "company_name": "",
        "job_title": "",
        "error": "",
        "domain": urlparse(url).netloc,
        "same_domain_pages": [],
        "sources": {
            "job_page": False,
            "same_domain_pages": False,
            "benefits": False,
            "contact_signals": False,
            "external_sentiment": False,
        },
        "structured": {},
    }

    html_text, fetch_error = _fetch_page(url)
    if fetch_error:
        result["error"] = f"Could not fetch the URL: {fetch_error}"
        return result

    soup = _try_bs4(html_text)
    page_text = _extract_page_text(soup)
    page_title = clean_text(soup.title.get_text()) if soup.title else ""
    result["title"] = page_title

    if not looks_like_job_text(page_text):
        browser_html, browser_error = _fetch_page_with_browser(url)
        if browser_html:
            soup = _try_bs4(browser_html)
            page_text = _extract_page_text(soup)
            page_title = clean_text(soup.title.get_text()) if soup.title else page_title
        else:
            if browser_error:
                result["error"] = f"Initial parse was thin and browser fallback failed: {browser_error}"
            else:
                result["error"] = "Initial parse was thin and browser fallback did not return more text."

    structured = _parse_structured_text(page_text, page_title, soup, result["domain"])
    same_domain_pages = structured.get("same_domain_pages", [])
    result["same_domain_pages"] = same_domain_pages
    result["text"] = page_text
    result["company_name"] = structured.get("company_name", "")
    result["job_title"] = structured.get("job_title", "")
    result["structured"] = structured
    result["success"] = bool(page_text and (looks_like_job_text(page_text) or result["company_name"]))
    if result["success"]:
        result["sources"]["job_page"] = True
        result["sources"]["same_domain_pages"] = bool(same_domain_pages)
        result["sources"]["benefits"] = bool(structured.get("benefits"))
        result["sources"]["contact_signals"] = any("contact" in page["path"] for page in same_domain_pages)
        result["sources"]["external_sentiment"] = False
    return result
