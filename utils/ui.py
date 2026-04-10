from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

from utils.helpers import clean_text


def escape(text: str) -> str:
    return html.escape(text or "")


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');

        html, body, [class*="css"]  {
            font-family: "Manrope", "Avenir Next", "Segoe UI", sans-serif;
        }

        .stApp {
            background:
                radial-gradient(circle at top left, rgba(14, 165, 233, 0.08), transparent 26%),
                radial-gradient(circle at top right, rgba(15, 118, 110, 0.08), transparent 24%),
                linear-gradient(180deg, #f7fbfc 0%, #ffffff 100%);
        }

        .block-container {
            padding-top: 2rem;
            padding-bottom: 3rem;
            max-width: 1200px;
        }

        .hero {
            background: linear-gradient(135deg, #082f49 0%, #0f766e 100%);
            color: #f8fafc;
            border-radius: 24px;
            padding: 2rem 2rem 1.6rem 2rem;
            margin-bottom: 1.25rem;
            box-shadow: 0 24px 80px rgba(8, 47, 73, 0.18);
        }

        .hero-kicker {
            display: inline-block;
            background: rgba(255, 255, 255, 0.12);
            border: 1px solid rgba(255, 255, 255, 0.18);
            color: #dff7f4;
            border-radius: 999px;
            padding: 0.35rem 0.7rem;
            font-size: 0.78rem;
            font-weight: 700;
            letter-spacing: 0.02em;
            margin-bottom: 1rem;
        }

        .hero h1 {
            margin: 0 0 0.55rem 0;
            font-size: 2.35rem;
            line-height: 1.05;
            font-weight: 800;
        }

        .hero p {
            margin: 0;
            color: rgba(248, 250, 252, 0.9);
            max-width: 760px;
            font-size: 1.02rem;
            line-height: 1.6;
        }

        .hero-footnote {
            margin-top: 1rem;
            color: rgba(248, 250, 252, 0.82);
            font-size: 0.92rem;
        }

        .entry-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 24px;
            padding: 1.35rem 1.25rem;
            box-shadow: 0 22px 60px rgba(15, 23, 42, 0.07);
            min-height: 300px;
        }

        .entry-kicker {
            display: inline-block;
            color: #0f766e;
            background: #ecfeff;
            border: 1px solid #a5f3fc;
            border-radius: 999px;
            padding: 0.26rem 0.62rem;
            font-size: 0.74rem;
            font-weight: 800;
            letter-spacing: 0.05em;
            text-transform: uppercase;
            margin-bottom: 0.95rem;
        }

        .entry-card h3 {
            color: #0f172a;
            margin: 0 0 0.45rem 0;
            font-size: 1.35rem;
            line-height: 1.2;
            font-weight: 800;
        }

        .entry-card p {
            color: #475569;
            margin: 0 0 0.95rem 0;
            font-size: 0.96rem;
            line-height: 1.65;
        }

        .entry-list {
            margin: 0.2rem 0 1rem 1rem;
            color: #334155;
            line-height: 1.65;
        }

        .metric-card {
            background: #ffffff;
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 20px;
            padding: 1.15rem 1.1rem;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.06);
            min-height: 172px;
            display: flex;
            flex-direction: column;
            justify-content: flex-start;
        }

        .metric-label {
            color: #475569;
            font-size: 0.8rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.6rem;
            line-height: 1.35;
        }

        .metric-value {
            color: #0f172a;
            font-size: clamp(1.6rem, 2.25vw, 2rem);
            line-height: 1.1;
            font-weight: 800;
            margin-bottom: 0.45rem;
            word-break: normal;
            overflow-wrap: anywhere;
        }

        .metric-subtext {
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.6;
            margin-top: 0.15rem;
        }

        .risk-badge, .rec-badge, .mode-pill, .score-pill, .track-pill {
            display: inline-block;
            border-radius: 999px;
            padding: 0.28rem 0.65rem;
            font-size: 0.8rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }

        .mode-pill {
            background: #ecfeff;
            color: #155e75;
            border: 1px solid #a5f3fc;
            margin-bottom: 0.8rem;
        }

        .track-pill {
            background: #f0fdf4;
            color: #166534;
            border: 1px solid #86efac;
            margin-bottom: 0.8rem;
        }

        .source-pill {
            display: inline-block;
            padding: 0.34rem 0.72rem;
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            border-radius: 999px;
            color: #334155;
            font-size: 0.82rem;
            font-weight: 600;
            white-space: normal;
            line-height: 1.35;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.45rem;
            margin: 0.1rem 0 0.4rem 0;
        }

        .section-index {
            display: inline-block;
            min-width: 1.5rem;
            height: 1.5rem;
            line-height: 1.5rem;
            text-align: center;
            border-radius: 999px;
            background: #e0f2fe;
            color: #075985;
            font-size: 0.78rem;
            font-weight: 800;
            margin-right: 0.45rem;
        }

        .section-title {
            color: #0f172a;
            font-size: 1.08rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
        }

        .section-shell {
            background: #ffffff;
            border: 1px solid rgba(148, 163, 184, 0.18);
            border-radius: 18px;
            padding: 1.05rem 1.1rem;
            margin-bottom: 0.95rem;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.05);
        }

        .section-shell p {
            color: #334155;
            margin: 0;
            line-height: 1.65;
            font-size: 0.96rem;
        }

        .section-intro {
            color: #475569 !important;
            margin-bottom: 0.75rem !important;
        }

        .section-shell ul, .entry-list {
            margin-top: 0.2rem;
            color: #334155;
            line-height: 1.7;
            padding-left: 1.15rem;
        }

        .coverage-list {
            display: flex;
            flex-direction: column;
            gap: 0.7rem;
            margin-top: 0.85rem;
        }

        .coverage-summary {
            border-radius: 18px;
            padding: 0.95rem 1rem;
            margin-top: 0.15rem;
            margin-bottom: 0.95rem;
            border: 1px solid #cbd5e1;
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        }

        .coverage-summary-level {
            font-size: 0.82rem;
            font-weight: 800;
            text-transform: uppercase;
            letter-spacing: 0.06em;
            margin-bottom: 0.4rem;
        }

        .coverage-summary-copy {
            color: #334155;
            font-size: 0.94rem;
            line-height: 1.6;
        }

        .coverage-summary--strong {
            background: linear-gradient(135deg, #ecfdf5 0%, #ffffff 100%);
            border-color: #86efac;
        }

        .coverage-summary--strong .coverage-summary-level {
            color: #166534;
        }

        .coverage-summary--moderate {
            background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
            border-color: #fde68a;
        }

        .coverage-summary--moderate .coverage-summary-level {
            color: #92400e;
        }

        .coverage-summary--limited {
            background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%);
            border-color: #fecaca;
        }

        .coverage-summary--limited .coverage-summary-level {
            color: #991b1b;
        }

        .coverage-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            padding: 0.8rem 0.9rem;
            border-radius: 16px;
            border: 1px solid #e2e8f0;
            background: #f8fafc;
        }

        .coverage-meta {
            flex: 1 1 auto;
        }

        .coverage-label {
            color: #0f172a;
            font-size: 0.93rem;
            font-weight: 800;
            margin-bottom: 0.18rem;
        }

        .coverage-detail {
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.55;
        }

        .coverage-status {
            display: inline-block;
            white-space: nowrap;
            border-radius: 999px;
            padding: 0.24rem 0.62rem;
            font-size: 0.78rem;
            font-weight: 800;
            letter-spacing: 0.02em;
        }

        .coverage-status--success {
            background: #ecfdf5;
            color: #166534;
            border: 1px solid #86efac;
        }

        .coverage-status--partial {
            background: #fffbeb;
            color: #92400e;
            border: 1px solid #fde68a;
        }

        .coverage-status--missing {
            background: #fef2f2;
            color: #991b1b;
            border: 1px solid #fecaca;
        }

        .coverage-status--info {
            background: #eff6ff;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
        }

        .decision-banner {
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(148, 163, 184, 0.24);
            border-radius: 20px;
            padding: 1rem 1.05rem;
            margin-bottom: 1rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
        }

        .decision-banner h3 {
            margin: 0 0 0.35rem 0;
            color: #0f172a;
            font-size: 1rem;
            font-weight: 800;
        }

        .decision-banner p {
            margin: 0;
            color: #475569;
            line-height: 1.6;
            font-size: 0.94rem;
        }

        .shortlist-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 22px;
            padding: 1.05rem 1.1rem;
            box-shadow: 0 18px 50px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.95rem;
        }

        .shortlist-head {
            display: flex;
            justify-content: space-between;
            gap: 1rem;
            align-items: flex-start;
            margin-bottom: 0.75rem;
            flex-wrap: wrap;
        }

        .shortlist-title {
            color: #0f172a;
            font-size: 1.14rem;
            font-weight: 800;
            margin: 0 0 0.18rem 0;
            line-height: 1.3;
        }

        .shortlist-meta {
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.65;
        }

        .shortlist-tags {
            margin: 0.55rem 0 0.65rem 0;
        }

        .score-pill {
            background: #eff6ff;
            color: #1d4ed8;
            border: 1px solid #bfdbfe;
            white-space: normal;
            line-height: 1.35;
        }

        .shortlist-copy {
            color: #334155;
            font-size: 0.95rem;
            line-height: 1.68;
            margin: 0;
        }

        .shortlist-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.8rem;
            margin-top: 0.75rem;
        }

        .shortlist-grid-item {
            background: #f8fafc;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 0.75rem 0.85rem;
        }

        .shortlist-grid-item strong {
            color: #0f172a;
            display: block;
            font-size: 0.82rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.22rem;
        }

        .shortlist-grid-item span {
            color: #475569;
            font-size: 0.93rem;
            line-height: 1.58;
        }

        .shortlist-source-summary {
            margin-top: 0.8rem;
            color: #475569;
            font-size: 0.9rem;
            line-height: 1.6;
        }

        .shortlist-mini-list {
            margin-top: 0.85rem;
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
            gap: 0.7rem;
        }

        .shortlist-mini-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 16px;
            padding: 0.72rem 0.82rem;
        }

        .shortlist-mini-card strong {
            color: #0f172a;
            display: block;
            font-size: 0.8rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.24rem;
        }

        .shortlist-mini-card span {
            color: #475569;
            font-size: 0.92rem;
            line-height: 1.56;
        }

        .package-card {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
            margin-bottom: 0.95rem;
        }

        .package-card h4 {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 800;
            margin: 0 0 0.55rem 0;
        }

        .package-card p, .package-card li {
            color: #334155;
            font-size: 0.95rem;
            line-height: 1.6;
        }

        .package-card ul {
            margin: 0.15rem 0 0 1rem;
            padding-left: 0.25rem;
        }

        .explain-panel {
            background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
            border: 1px solid rgba(148, 163, 184, 0.2);
            border-radius: 18px;
            padding: 1rem 1.05rem;
            margin-bottom: 0.95rem;
            box-shadow: 0 18px 40px rgba(15, 23, 42, 0.05);
        }

        .explain-panel h3 {
            color: #0f172a;
            font-size: 1rem;
            font-weight: 800;
            margin: 0 0 0.65rem 0;
        }

        .explain-panel ul {
            margin: 0.1rem 0 0 1rem;
            padding-left: 0.25rem;
        }

        .explain-panel li {
            color: #334155;
            font-size: 0.95rem;
            line-height: 1.65;
            margin-bottom: 0.38rem;
        }

        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] h4 {
            color: #0f172a !important;
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] span {
            color: #0f172a !important;
            font-weight: 700 !important;
        }

        [data-testid="stCaptionContainer"] {
            color: #475569 !important;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: #ffffff;
            border: 1px dashed #94a3b8;
        }

        [data-testid="stFileUploaderDropzoneInstructions"] div,
        [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stFileUploaderDropzoneInstructions"] small {
            color: #334155 !important;
        }

        .stTextArea textarea,
        .stTextInput input {
            color: #0f172a !important;
        }

        [data-baseweb="select"] > div {
            color: #0f172a !important;
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span {
            color: #0f172a !important;
            font-weight: 700 !important;
        }

        div[data-testid="stAlert"] {
            background: #f8fafc;
            border: 1px solid #cbd5e1;
            color: #0f172a;
            border-radius: 16px;
        }

        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] li,
        div[data-testid="stAlert"] span {
            color: #0f172a !important;
        }

        .divider-gap {
            height: 0.4rem;
        }

        @media (max-width: 900px) {
            .shortlist-grid {
                grid-template-columns: 1fr;
            }

            .shortlist-mini-list {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_hero(kicker: str, title: str, body: str, footnote: str = "") -> None:
    footnote_html = f'<div class="hero-footnote">{escape(footnote)}</div>' if footnote else ""
    st.markdown(
        "".join(
            [
                '<div class="hero">',
                f'<div class="hero-kicker">{escape(kicker)}</div>',
                f"<h1>{escape(title)}</h1>",
                f"<p>{escape(body)}</p>",
                footnote_html,
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_entry_card(kicker: str, title: str, body: str, bullets: list[str]) -> None:
    bullet_html = "".join(f"<li>{escape(item)}</li>" for item in bullets)
    st.markdown(
        "".join(
            [
                '<div class="entry-card">',
                f'<div class="entry-kicker">{escape(kicker)}</div>',
                f"<h3>{escape(title)}</h3>",
                f"<p>{escape(body)}</p>",
                f'<ul class="entry-list">{bullet_html}</ul>',
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def dedupe_section_items(items: list[str]) -> list[str]:
    cleaned_items: list[str] = []
    seen: set[str] = set()
    for raw_item in items:
        item = clean_text(str(raw_item or "")).strip().lstrip("- ").strip()
        if not item:
            continue
        lowered = item.lower()
        if lowered in seen:
            continue
        cleaned_items.append(item)
        seen.add(lowered)
    return cleaned_items


def clean_section_markup_text(text: str) -> str:
    cleaned = html.unescape(str(text or ""))
    replacements = (
        (r"<br\s*/?>", "\n"),
        (r"</p\s*>", "\n\n"),
        (r"</div\s*>", "\n"),
        (r"</li\s*>", "\n"),
        (r"</ul\s*>", "\n"),
        (r"</ol\s*>", "\n"),
        (r"<li\b[^>]*>", "- "),
    )
    for pattern, replacement in replacements:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"<[^>]+>", "", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return clean_text(cleaned).strip()


def extract_html_list_items(text: str) -> list[str]:
    matches = re.findall(r"<li\b[^>]*>(.*?)</li>", html.unescape(str(text or "")), flags=re.IGNORECASE | re.DOTALL)
    items = [clean_section_markup_text(match) for match in matches]
    return dedupe_section_items(items)


def normalize_section_content(content: Any) -> tuple[list[str], str]:
    if content is None:
        return [], ""

    if isinstance(content, (list, tuple)):
        normalized_items: list[str] = []
        for item in content:
            nested_items, paragraph = normalize_section_content(item)
            if nested_items:
                normalized_items.extend(nested_items)
            elif paragraph:
                normalized_items.append(paragraph)
        return dedupe_section_items(normalized_items), ""

    text = str(content).strip()
    if not text:
        return [], ""

    html_items = extract_html_list_items(text)
    if html_items:
        return html_items, ""

    cleaned = clean_section_markup_text(text)
    if not cleaned:
        return [], ""

    lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
    bullet_pattern = re.compile(r"^\s*(?:[-*•]+|\d+[.)])\s+")
    bullet_items = [bullet_pattern.sub("", line).strip() for line in lines if bullet_pattern.match(line)]
    if bullet_items and len(bullet_items) == len(lines):
        return dedupe_section_items(bullet_items), ""

    return [], cleaned


def render_metric_card(title: str, value: str, subtitle: str, badge_html: str = "") -> None:
    subtext_html = f'<div class="metric-subtext">{escape(subtitle)}</div>' if subtitle.strip() else ""
    card_html = "".join(
        [
            '<div class="metric-card">',
            f'<div class="metric-label">{escape(title)}</div>',
            f'<div class="metric-value">{escape(value)}</div>',
            badge_html,
            subtext_html,
            "</div>",
        ]
    )
    st.markdown(card_html, unsafe_allow_html=True)


def render_text_section(index: int, title: str, body: str) -> None:
    formatted_body = escape(body).replace("\n", "<br>")
    st.markdown(
        "".join(
            [
                '<div class="section-shell">',
                f'<div class="section-title"><span class="section-index">{index}</span>{escape(title)}</div>',
                f"<p>{formatted_body}</p>",
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_list_section(
    index: int,
    title: str,
    content: Any,
    empty_message: str,
    intro: str = "",
) -> None:
    items, paragraph = normalize_section_content(content)
    if items:
        list_html = "".join(f"<li>{escape(item)}</li>" for item in items)
        body_html = f"<ul>{list_html}</ul>"
    elif paragraph:
        body_html = f"<p>{escape(paragraph)}</p>"
    else:
        body_html = f"<p>{escape(empty_message)}</p>"
    intro_html = f'<p class="section-intro">{escape(intro)}</p>' if intro else ""
    section_html = "".join(
        [
            '<div class="section-shell">',
            f'<div class="section-title"><span class="section-index">{index}</span>{escape(title)}</div>',
            intro_html,
            body_html,
            "</div>",
        ]
    )
    st.markdown(section_html, unsafe_allow_html=True)


def render_coverage_section(
    index: int,
    title: str,
    summary_label: str,
    summary_detail: str,
    summary_tone: str,
    rows: list[dict[str, str]],
) -> None:
    rows_html = "".join(
        "".join(
            [
                '<div class="coverage-row">',
                '<div class="coverage-meta">',
                f'<div class="coverage-label">{escape(row["label"])}</div>',
                f'<div class="coverage-detail">{escape(row["detail"])}</div>',
                "</div>",
                f'<span class="coverage-status coverage-status--{escape(row["tone"])}">{escape(row["status"])}</span>',
                "</div>",
            ]
        )
        for row in rows
    )
    st.markdown(
        "".join(
            [
                '<div class="section-shell">',
                f'<div class="section-title"><span class="section-index">{index}</span>{escape(title)}</div>',
                f'<div class="coverage-summary coverage-summary--{escape(summary_tone)}">',
                f'<div class="coverage-summary-level">{escape(summary_label)}</div>',
                f'<div class="coverage-summary-copy">{escape(summary_detail)}</div>',
                "</div>",
                f'<div class="coverage-list">{rows_html}</div>',
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_pills(items: list[str]) -> None:
    pills_html = "".join(f'<span class="source-pill">{escape(item)}</span>' for item in items)
    pills_html = f'<div class="pill-row">{pills_html}</div>'
    st.markdown(pills_html, unsafe_allow_html=True)


def render_decision_banner(title: str, body: str) -> None:
    st.markdown(
        "".join(
            [
                '<div class="decision-banner">',
                f"<h3>{escape(title)}</h3>",
                f"<p>{escape(body)}</p>",
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def _first_nonempty(values: Any) -> str:
    if not isinstance(values, (list, tuple)):
        return clean_text(str(values or ""))
    for value in values:
        cleaned = clean_text(str(value or ""))
        if cleaned:
            return cleaned
    return ""


def render_shortlist_card(candidate: dict[str, Any], rank: int) -> None:
    recommendation = candidate.get("recommendation", "Insufficient evidence")
    name = candidate.get("name", "Unnamed research target")
    university = candidate.get("university", "Institution not clearly identified")
    department_or_lab = candidate.get("department_or_lab", "Research context not clearly identified")
    role_title = candidate.get("role_title", "")
    meta_parts = [university, department_or_lab]
    if role_title and role_title not in {"Role not clearly labeled on the source page", department_or_lab}:
        meta_parts.insert(1, role_title)
    meta_text = " · ".join(part for part in meta_parts if clean_text(part))
    score_pills = "".join(
        f'<span class="score-pill">{escape(label)}</span>'
        for label in (
            f"Priority {candidate.get('priority_score', 0)}/100",
            f"Fit {candidate.get('research_fit_score', 0)}/100",
            f"Feasibility {candidate.get('outreach_feasibility_score', 0)}/100",
            recommendation,
        )
    )
    tag_pills = "".join(
        f'<span class="source-pill">{escape(tag)}</span>'
        for tag in candidate.get("research_tags", [])[:4] + candidate.get("discipline_tags", [])[:2]
    )
    score_pills = f'<div class="pill-row">{score_pills}</div>'
    tag_pills = f'<div class="pill-row">{tag_pills}</div>' if tag_pills else ""
    contact_label = candidate.get("official_email") or candidate.get("lead_contact_name") or "No official contact route surfaced"
    recent_output = (
        _first_nonempty(candidate.get("publications", []))
        or _first_nonempty(candidate.get("project_signals", []))
        or _first_nonempty(candidate.get("recent_topics", []))
        or "Recent outputs were limited on the fetched sources."
    )
    strong_fit = candidate.get("why_match_topline", "Limited explanation available.")
    uncertainty = candidate.get("main_watchout", "No major watch-out recorded.")
    source_summary = candidate.get("quick_source_summary", "Source mix not summarized.")
    why_summary = candidate.get("why_matched_summary", strong_fit)
    st.markdown(
        "".join(
            [
                '<div class="shortlist-card">',
                '<div class="shortlist-head">',
                "<div>",
                f'<div class="shortlist-title">#{rank} · {escape(name)}</div>',
                f'<div class="shortlist-meta">{escape(meta_text)}</div>',
                "</div>",
                f'<span class="track-pill">{escape(recommendation)}</span>',
                "</div>",
                f'<div class="shortlist-tags">{score_pills}</div>',
                f'<div class="shortlist-tags">{tag_pills}</div>',
                f'<p class="shortlist-copy">{escape(why_summary)}</p>',
                '<div class="shortlist-grid">',
                f'<div class="shortlist-grid-item"><strong>Match Type</strong><span>{escape(candidate.get("entity_type", "Research match"))}</span></div>',
                f'<div class="shortlist-grid-item"><strong>Opportunity Type</strong><span>{escape(candidate.get("opportunity_type", "Research opportunity"))}</span></div>',
                f'<div class="shortlist-grid-item"><strong>Contact Route</strong><span>{escape(contact_label)}</span></div>',
                f'<div class="shortlist-grid-item"><strong>Source Mix</strong><span>{escape(source_summary)}</span></div>',
                "</div>",
                '<div class="shortlist-mini-list">',
                f'<div class="shortlist-mini-card"><strong>Why It Deserves Attention</strong><span>{escape(strong_fit)}</span></div>',
                f'<div class="shortlist-mini-card"><strong>Main Uncertainty</strong><span>{escape(uncertainty)}</span></div>',
                f'<div class="shortlist-mini-card"><strong>Recent Output Or Topic</strong><span>{escape(recent_output)}</span></div>',
                f'<div class="shortlist-mini-card"><strong>Worth Contacting Now?</strong><span>{escape(recommendation)}</span></div>',
                "</div>",
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_outreach_package(package: dict[str, Any]) -> None:
    with st.container(border=True):
        st.markdown("### Outreach Package")
        render_list_section(14, "Subject Line Options", package.get("subject_lines", []), "No subject lines were generated.")
        render_list_section(
            15,
            "Personalization Lines",
            package.get("personalization_lines", []),
            "No personalization lines were generated.",
        )
        render_list_section(
            16,
            "CV Tailoring Suggestions",
            package.get("cv_tailoring", []),
            "No tailoring suggestions were generated.",
        )
        render_text_section(17, "Cold Email Draft", package.get("email_draft", "No email draft was generated."))
        render_text_section(18, "Follow-Up Suggestion", package.get("follow_up", "No follow-up suggestion was generated."))
