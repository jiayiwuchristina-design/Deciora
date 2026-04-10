from __future__ import annotations

import re
from functools import lru_cache
from urllib.parse import quote_plus, urlparse

import requests
from bs4 import BeautifulSoup

from utils.helpers import clean_text


DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36"
    )
}

SEARCH_BLOCKLIST = {
    "google.com",
    "scholar.google.com",
    "www.google.com",
    "bing.com",
    "www.bing.com",
    "duckduckgo.com",
    "html.duckduckgo.com",
    "linkedin.com",
    "www.linkedin.com",
    "researchgate.net",
    "www.researchgate.net",
    "semanticscholar.org",
    "www.semanticscholar.org",
    "orcid.org",
    "www.orcid.org",
}

OFFICIAL_DOMAIN_SUFFIXES = (
    ".edu",
    ".ac.uk",
    ".edu.au",
    ".ac.nz",
    ".edu.sg",
    ".edu.cn",
    ".edu.hk",
    ".edu.tw",
    ".ac.jp",
    ".ac.kr",
    ".edu.my",
    ".edu.br",
    ".edu.mx",
)


def try_bs4(html_text: str) -> BeautifulSoup:
    for parser in ("lxml", "html.parser"):
        try:
            return BeautifulSoup(html_text, parser)
        except Exception:
            continue
    return BeautifulSoup(html_text, "html.parser")


def fetch_page(url: str, timeout: int = 12) -> tuple[str, str]:
    try:
        response = requests.get(url, timeout=timeout, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        return response.text, ""
    except Exception as exc:
        return "", str(exc)


def fetch_json(url: str, params: dict | None = None, timeout: int = 12) -> tuple[dict, str]:
    try:
        response = requests.get(url, params=params or {}, timeout=timeout, headers=DEFAULT_HEADERS)
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}, ""
    except Exception as exc:
        return {}, str(exc)


def fetch_page_with_browser(url: str) -> tuple[str, str]:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        return "", f"Playwright is not installed: {exc}"

    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto(url, wait_until="networkidle", timeout=20000)
            content = page.content()
            page.close()
            browser.close()
            return content, ""
    except Exception as exc:
        return "", str(exc)


def fetch_page_best_effort(url: str) -> tuple[str, str]:
    html_text, error = fetch_page(url)
    if html_text:
        return html_text, ""
    browser_html, browser_error = fetch_page_with_browser(url)
    if browser_html:
        return browser_html, ""
    return "", error or browser_error


def extract_page_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "footer", "header", "noscript", "svg", "form"]):
        tag.decompose()
    main_block = soup.find("main") or soup.find("article") or soup.body or soup
    return clean_text(main_block.get_text("\n", strip=True))


def canonical_domain(url: str) -> str:
    domain = urlparse(url).netloc.lower().strip()
    return domain[4:] if domain.startswith("www.") else domain


def is_official_academic_domain(url: str) -> bool:
    domain = canonical_domain(url)
    if not domain or domain in SEARCH_BLOCKLIST:
        return False
    if domain.endswith(OFFICIAL_DOMAIN_SUFFIXES):
        return True
    return any(token in domain for token in ("university", "college", "institute", "school", "campus", "uni-"))


@lru_cache(maxsize=64)
def search_duckduckgo_html(query: str, max_results: int = 8) -> list[dict[str, str]]:
    url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
    html_text, error = fetch_page(url, timeout=15)
    if not html_text:
        return []

    soup = try_bs4(html_text)
    results: list[dict[str, str]] = []
    seen: set[str] = set()

    for result in soup.select(".result"):
        link = result.select_one(".result__a")
        if not link or not link.get("href"):
            continue
        href = link.get("href", "").strip()
        if not href or href in seen:
            continue
        domain = canonical_domain(href)
        if not domain or domain in SEARCH_BLOCKLIST:
            continue
        snippet_tag = result.select_one(".result__snippet")
        snippet = clean_text(snippet_tag.get_text(" ", strip=True)) if snippet_tag else ""
        results.append(
            {
                "title": clean_text(link.get_text(" ", strip=True)),
                "url": href,
                "snippet": snippet,
                "domain": domain,
            }
        )
        seen.add(href)
        if len(results) >= max_results:
            break

    return results


def extract_email_from_text(text: str) -> str:
    match = re.search(r"([A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,})", text, flags=re.IGNORECASE)
    return match.group(1) if match else ""


@lru_cache(maxsize=96)
def search_openalex_works(query: str, per_page: int = 12) -> list[dict]:
    payload, _error = fetch_json(
        "https://api.openalex.org/works",
        params={
            "search": query,
            "per-page": per_page,
        },
        timeout=18,
    )
    results = payload.get("results", [])
    return results if isinstance(results, list) else []
