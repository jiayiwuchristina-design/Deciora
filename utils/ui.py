from __future__ import annotations

import html
import re
from typing import Any

import streamlit as st

from utils.helpers import clean_text


def escape(text: str) -> str:
    return html.escape(text or "")


def _brand_mark_html(*, hero: bool = False) -> str:
    modifier = " brand-mark--hero" if hero else ""
    return f'<div class="brand-mark{modifier}" aria-hidden="true"></div>'


def inject_styles() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&family=Space+Grotesk:wght@500;700&display=swap');

        :root {
            --deciora-bg: #f4f7fb;
            --deciora-bg-soft: #eef2f8;
            --deciora-surface: #fcfdff;
            --deciora-surface-strong: #ffffff;
            --deciora-panel: rgba(255, 255, 255, 0.88);
            --deciora-border: rgba(57, 74, 112, 0.16);
            --deciora-border-strong: rgba(35, 49, 81, 0.24);
            --deciora-text: #17253f;
            --deciora-text-soft: #55627b;
            --deciora-text-muted: #7b879c;
            --deciora-brand-900: #17253f;
            --deciora-brand-800: #22304f;
            --deciora-brand-700: #31456f;
            --deciora-brand-500: #7d8ec5;
            --deciora-brand-400: #9aaad7;
            --deciora-brand-300: #d7dff2;
            --deciora-shadow-lg: 0 28px 80px rgba(19, 34, 60, 0.10);
            --deciora-shadow-md: 0 18px 48px rgba(19, 34, 60, 0.08);
            --deciora-shadow-sm: 0 12px 26px rgba(19, 34, 60, 0.06);
            --deciora-radius-xl: 30px;
            --deciora-radius-lg: 24px;
            --deciora-radius-md: 18px;
            --deciora-radius-sm: 14px;
        }

        html, body, [class*="css"] {
            font-family: "Manrope", "Avenir Next", "Segoe UI", sans-serif;
            color: var(--deciora-text);
        }

        h1, h2, h3, h4, h5, h6 {
            font-family: "Manrope", "Avenir Next", "Segoe UI", sans-serif !important;
            letter-spacing: -0.028em;
            font-weight: 700 !important;
        }

        .stApp {
            background:
                radial-gradient(circle at 0% 0%, rgba(154, 170, 215, 0.20), transparent 28%),
                radial-gradient(circle at 100% 6%, rgba(104, 123, 190, 0.14), transparent 24%),
                linear-gradient(180deg, #f7f9fc 0%, #f2f6fb 46%, #f7f9fc 100%);
        }

        [data-testid="stHeader"] {
            background: rgba(244, 247, 251, 0.72);
            backdrop-filter: blur(14px);
        }

        .block-container {
            padding-top: 1.15rem;
            padding-bottom: 2.8rem;
            max-width: 1220px;
        }

        section[data-testid="stSidebar"] {
            background: linear-gradient(180deg, #eef3fa 0%, #f7f9fc 100%);
            border-right: 1px solid rgba(45, 60, 94, 0.08);
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarContent"] {
            padding-top: 0.9rem;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNav"] {
            background: transparent;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"] {
            border-radius: 16px;
            border: 1px solid transparent;
            margin-bottom: 0.3rem;
            background: rgba(255, 255, 255, 0.44);
            transition: all 180ms ease;
        }

        section[data-testid="stSidebar"] [data-testid="stSidebarNavLink"]:hover {
            background: rgba(255, 255, 255, 0.82);
            border-color: rgba(125, 142, 197, 0.30);
        }

        .sidebar-brand {
            background:
                radial-gradient(circle at 86% 18%, rgba(178, 191, 232, 0.46), transparent 30%),
                linear-gradient(145deg, #1a2741 0%, #22304f 52%, #30436d 100%);
            border: 1px solid rgba(152, 170, 223, 0.16);
            border-radius: 26px;
            padding: 0.9rem 0.95rem 0.88rem 0.95rem;
            margin-bottom: 0.85rem;
            box-shadow: 0 20px 46px rgba(17, 27, 48, 0.18);
            position: relative;
            overflow: hidden;
        }

        .sidebar-brand::after {
            content: "";
            position: absolute;
            inset: auto -10% -40% auto;
            width: 160px;
            height: 160px;
            border-radius: 999px;
            background: rgba(163, 177, 223, 0.08);
        }

        .sidebar-brand-row {
            display: flex;
            align-items: center;
            gap: 0.72rem;
            position: relative;
            z-index: 1;
        }

        .brand-mark {
            position: relative;
            width: 48px;
            height: 48px;
            border-radius: 16px;
            background: linear-gradient(145deg, #99aad7 0%, #7d8ec5 48%, #667bb4 100%);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.26), 0 12px 24px rgba(9, 16, 31, 0.16);
            flex: 0 0 auto;
        }

        .brand-mark::before {
            content: "";
            position: absolute;
            inset: 10px 11px 10px 12px;
            border-radius: 11px;
            border: 2.25px solid rgba(248, 250, 255, 0.92);
            border-right-width: 0;
        }

        .brand-mark::after {
            content: "";
            position: absolute;
            top: 9px;
            right: 9px;
            width: 14px;
            height: 14px;
            border-radius: 999px;
            background: rgba(248, 250, 255, 0.96);
        }

        .brand-mark--hero {
            width: 52px;
            height: 52px;
            border-radius: 17px;
        }

        .brand-mark--hero::before {
            inset: 10px 11px 10px 12px;
            border-radius: 12px;
        }

        .brand-mark--hero::after {
            top: 10px;
            right: 10px;
            width: 15px;
            height: 15px;
        }

        .sidebar-brand-name,
        .hero-brand-name {
            color: #f6f8fd;
            font-family: "Space Grotesk", "Manrope", sans-serif;
            font-size: 1.2rem;
            font-weight: 600;
            line-height: 1.02;
            letter-spacing: -0.025em;
        }

        .sidebar-brand-tag,
        .hero-brand-tag {
            color: rgba(235, 240, 251, 0.78);
            font-size: 0.77rem;
            line-height: 1.38;
            margin-top: 0.18rem;
        }

        .sidebar-brand-note {
            margin-top: 0.72rem;
            color: rgba(235, 240, 251, 0.82);
            font-size: 0.8rem;
            line-height: 1.48;
            position: relative;
            z-index: 1;
        }

        .sidebar-track-card {
            background: rgba(255, 255, 255, 0.76);
            border: 1px solid rgba(49, 69, 111, 0.12);
            border-radius: 22px;
            padding: 0.88rem 0.92rem 0.8rem 0.92rem;
            box-shadow: var(--deciora-shadow-sm);
            margin-bottom: 0.88rem;
        }

        .sidebar-track-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            color: var(--deciora-brand-700);
            background: rgba(154, 170, 215, 0.16);
            border: 1px solid rgba(125, 142, 197, 0.24);
            border-radius: 999px;
            padding: 0.24rem 0.58rem;
            font-size: 0.7rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.09em;
            margin-bottom: 0.6rem;
        }

        .sidebar-track-title {
            color: var(--deciora-text);
            font-family: "Manrope", "Avenir Next", "Segoe UI", sans-serif;
            font-size: 0.98rem;
            font-weight: 700;
            margin-bottom: 0.28rem;
            letter-spacing: -0.02em;
        }

        .sidebar-track-body {
            color: var(--deciora-text-soft);
            font-size: 0.85rem;
            line-height: 1.5;
            margin-bottom: 0.62rem;
        }

        .sidebar-track-steps {
            margin: 0;
            padding-left: 1.1rem;
            color: var(--deciora-text);
        }

        .sidebar-track-steps li {
            font-size: 0.83rem;
            line-height: 1.48;
            margin-bottom: 0.34rem;
        }

        .hero {
            position: relative;
            overflow: hidden;
            background:
                radial-gradient(circle at 88% 18%, rgba(169, 184, 228, 0.25), transparent 22%),
                radial-gradient(circle at 22% 110%, rgba(121, 141, 198, 0.20), transparent 28%),
                linear-gradient(135deg, #17253f 0%, #22304f 48%, #30436d 100%);
            color: #f6f8fd;
            border: 1px solid rgba(161, 176, 220, 0.12);
            border-radius: var(--deciora-radius-xl);
            padding: 1.02rem 1.14rem 1.08rem 1.14rem;
            margin-bottom: 1.02rem;
            box-shadow: var(--deciora-shadow-lg);
        }

        .hero::before {
            content: "";
            position: absolute;
            inset: 0;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.06) 0%, transparent 34%, transparent 100%);
            pointer-events: none;
        }

        .hero-top {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            align-items: flex-start;
            margin-bottom: 0.78rem;
            position: relative;
            z-index: 1;
            flex-wrap: wrap;
        }

        .hero-brand {
            display: flex;
            align-items: center;
            gap: 0.72rem;
        }

        .hero-kicker {
            display: inline-flex;
            align-items: center;
            align-self: flex-start;
            background: rgba(255, 255, 255, 0.10);
            border: 1px solid rgba(215, 223, 242, 0.16);
            color: rgba(245, 248, 255, 0.90);
            border-radius: 999px;
            padding: 0.32rem 0.64rem;
            font-size: 0.68rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
        }

        .hero h1 {
            position: relative;
            z-index: 1;
            margin: 0 0 0.42rem 0;
            font-size: clamp(1.72rem, 3.15vw, 2.34rem);
            line-height: 1.04;
            font-weight: 700;
            max-width: 700px;
            letter-spacing: -0.034em;
        }

        .hero p {
            position: relative;
            z-index: 1;
            margin: 0;
            color: rgba(244, 247, 252, 0.88);
            max-width: 700px;
            font-size: 0.94rem;
            line-height: 1.58;
            font-weight: 500;
        }

        .hero-footnote {
            position: relative;
            z-index: 1;
            margin-top: 0.72rem;
            color: rgba(232, 238, 249, 0.78);
            font-size: 0.82rem;
            line-height: 1.44;
            max-width: 700px;
        }

        .entry-card,
        .metric-card,
        .section-shell,
        .decision-banner,
        .shortlist-card,
        .package-card,
        .explain-panel,
        div[data-testid="stVerticalBlockBorderWrapper"],
        div[data-testid="stForm"] {
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.96) 0%, rgba(250, 252, 255, 0.92) 100%);
            border: 1px solid var(--deciora-border);
            box-shadow: var(--deciora-shadow-sm);
        }

        .entry-card {
            border-radius: 24px;
            padding: 1.22rem 1.14rem;
            min-height: 310px;
        }

        .entry-kicker {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            color: var(--deciora-brand-700);
            background: rgba(154, 170, 215, 0.18);
            border: 1px solid rgba(125, 142, 197, 0.28);
            border-radius: 999px;
            padding: 0.24rem 0.62rem;
            font-size: 0.7rem;
            font-weight: 700;
            letter-spacing: 0.09em;
            text-transform: uppercase;
            margin-bottom: 0.72rem;
        }

        .entry-card h3 {
            color: var(--deciora-text);
            margin: 0 0 0.42rem 0;
            font-size: 1.22rem;
            line-height: 1.18;
            font-weight: 700;
        }

        .entry-card p {
            color: var(--deciora-text-soft);
            margin: 0 0 0.88rem 0;
            font-size: 0.92rem;
            line-height: 1.6;
        }

        .entry-list {
            margin: 0.1rem 0 0 0;
            padding-left: 1.1rem;
            color: var(--deciora-text);
            line-height: 1.58;
            font-size: 0.9rem;
        }

        .entry-list li::marker {
            color: var(--deciora-brand-500);
        }

        .metric-card {
            border-radius: 22px;
            padding: 1.02rem 1rem;
            min-height: 164px;
            position: relative;
            overflow: hidden;
        }

        .metric-card::before {
            content: "";
            position: absolute;
            inset: 0 auto auto 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, #7d8ec5 0%, #b7c4e6 100%);
            opacity: 0.72;
        }

        .metric-label {
            color: var(--deciora-text-muted);
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.56rem;
            line-height: 1.38;
        }

        .metric-value {
            color: var(--deciora-text);
            font-family: "Manrope", "Avenir Next", "Segoe UI", sans-serif;
            font-size: clamp(1.52rem, 2.08vw, 1.92rem);
            line-height: 1.08;
            font-weight: 700;
            margin-bottom: 0.42rem;
            overflow-wrap: anywhere;
            letter-spacing: -0.028em;
        }

        .metric-subtext {
            color: var(--deciora-text-soft);
            font-size: 0.87rem;
            line-height: 1.52;
            margin-top: 0.18rem;
        }

        .risk-badge, .rec-badge, .mode-pill, .score-pill, .track-pill, .source-pill, .coverage-status {
            display: inline-flex;
            align-items: center;
            border-radius: 999px;
            padding: 0.24rem 0.62rem;
            font-size: 0.73rem;
            font-weight: 700;
            letter-spacing: 0.02em;
        }

        .mode-pill {
            background: rgba(154, 170, 215, 0.16);
            color: var(--deciora-brand-700);
            border: 1px solid rgba(125, 142, 197, 0.26);
            margin-bottom: 0.66rem;
        }

        .track-pill {
            background: rgba(255, 255, 255, 0.88);
            color: var(--deciora-brand-800);
            border: 1px solid rgba(125, 142, 197, 0.22);
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.72);
        }

        .source-pill,
        .score-pill {
            background: rgba(237, 241, 249, 0.86);
            color: var(--deciora-brand-800);
            border: 1px solid rgba(125, 142, 197, 0.18);
            white-space: normal;
            line-height: 1.28;
        }

        .pill-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.42rem;
            margin: 0.08rem 0 0.34rem 0;
        }

        .section-index {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 1.48rem;
            height: 1.48rem;
            border-radius: 999px;
            background: rgba(154, 170, 215, 0.18);
            color: var(--deciora-brand-700);
            font-size: 0.72rem;
            font-weight: 700;
            margin-right: 0.42rem;
            border: 1px solid rgba(125, 142, 197, 0.18);
        }

        .section-title {
            color: var(--deciora-text);
            font-size: 1rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
        }

        .section-shell,
        .decision-banner,
        .package-card,
        .explain-panel {
            border-radius: 22px;
            padding: 0.96rem 1rem;
            margin-bottom: 0.88rem;
        }

        .section-shell p,
        .package-card p,
        .package-card li,
        .explain-panel li,
        .decision-banner p {
            color: var(--deciora-text-soft);
            margin: 0;
            line-height: 1.58;
            font-size: 0.91rem;
        }

        .section-intro {
            color: var(--deciora-text-muted) !important;
            margin-bottom: 0.62rem !important;
        }

        .section-shell ul,
        .package-card ul,
        .explain-panel ul {
            margin-top: 0.14rem;
            padding-left: 1.12rem;
        }

        .coverage-list {
            display: flex;
            flex-direction: column;
            gap: 0.62rem;
            margin-top: 0.72rem;
        }

        .coverage-summary {
            border-radius: 20px;
            padding: 0.9rem 0.95rem 0.88rem 0.95rem;
            margin-top: 0.1rem;
            margin-bottom: 0.82rem;
            border: 1px solid var(--deciora-border);
            background: linear-gradient(145deg, rgba(255, 255, 255, 0.96) 0%, rgba(243, 247, 253, 0.92) 100%);
        }

        .coverage-summary-level {
            font-size: 0.72rem;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.32rem;
        }

        .coverage-summary-copy {
            color: var(--deciora-text-soft);
            font-size: 0.89rem;
            line-height: 1.52;
        }

        .coverage-summary--strong {
            background: linear-gradient(145deg, #ecf9f0 0%, #ffffff 100%);
            border-color: #b8e1c1;
        }

        .coverage-summary--strong .coverage-summary-level {
            color: #1f6a39;
        }

        .coverage-summary--moderate {
            background: linear-gradient(145deg, #fff7e8 0%, #ffffff 100%);
            border-color: #f2d39d;
        }

        .coverage-summary--moderate .coverage-summary-level {
            color: #9b6420;
        }

        .coverage-summary--limited {
            background: linear-gradient(145deg, #fff1f1 0%, #ffffff 100%);
            border-color: #efc0c0;
        }

        .coverage-summary--limited .coverage-summary-level {
            color: #a53a3a;
        }

        .coverage-row {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 0.9rem;
            padding: 0.74rem 0.84rem;
            border-radius: 18px;
            border: 1px solid rgba(57, 74, 112, 0.12);
            background: rgba(244, 247, 252, 0.88);
        }

        .coverage-meta {
            flex: 1 1 auto;
        }

        .coverage-label {
            color: var(--deciora-text);
            font-size: 0.88rem;
            font-weight: 700;
            margin-bottom: 0.14rem;
        }

        .coverage-detail {
            color: var(--deciora-text-soft);
            font-size: 0.84rem;
            line-height: 1.48;
        }

        .coverage-status--success {
            background: #edf8f0;
            color: #25613d;
            border: 1px solid #b7dec2;
        }

        .coverage-status--partial {
            background: #fff7ea;
            color: #8c6123;
            border: 1px solid #edd5a7;
        }

        .coverage-status--missing {
            background: #fff2f1;
            color: #9d3f3f;
            border: 1px solid #ecc4c4;
        }

        .coverage-status--info {
            background: #edf2fb;
            color: var(--deciora-brand-700);
            border: 1px solid rgba(125, 142, 197, 0.22);
        }

        .decision-banner h3,
        .package-card h4,
        .explain-panel h3 {
            margin: 0 0 0.3rem 0;
            color: var(--deciora-text);
            font-size: 0.95rem;
            font-weight: 700;
        }

        .shortlist-card {
            border-radius: 24px;
            padding: 0.96rem 1rem;
            margin-bottom: 0.86rem;
        }

        .shortlist-head {
            display: flex;
            justify-content: space-between;
            gap: 0.8rem;
            align-items: flex-start;
            margin-bottom: 0.66rem;
            flex-wrap: wrap;
        }

        .shortlist-title {
            color: var(--deciora-text);
            font-size: 1.03rem;
            font-weight: 700;
            margin: 0 0 0.14rem 0;
            line-height: 1.24;
        }

        .shortlist-meta,
        .shortlist-copy,
        .shortlist-source-summary,
        .shortlist-grid-item span,
        .shortlist-mini-card span {
            color: var(--deciora-text-soft);
            font-size: 0.88rem;
            line-height: 1.52;
        }

        .shortlist-tags {
            margin: 0.44rem 0 0.54rem 0;
        }

        .shortlist-grid,
        .shortlist-mini-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
            gap: 0.68rem;
            margin-top: 0.66rem;
        }

        .shortlist-grid-item,
        .shortlist-mini-card {
            background: rgba(244, 247, 252, 0.88);
            border: 1px solid rgba(57, 74, 112, 0.10);
            border-radius: 18px;
            padding: 0.7rem 0.8rem;
        }

        .shortlist-grid-item strong,
        .shortlist-mini-card strong {
            color: var(--deciora-text);
            display: block;
            font-size: 0.72rem;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-bottom: 0.22rem;
        }

        [data-testid="stMarkdownContainer"] h2,
        [data-testid="stMarkdownContainer"] h3,
        [data-testid="stMarkdownContainer"] h4 {
            color: var(--deciora-text) !important;
        }

        [data-testid="stCaptionContainer"],
        section[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
            color: var(--deciora-text-muted) !important;
        }

        [data-testid="stWidgetLabel"] p,
        [data-testid="stWidgetLabel"] span {
            color: var(--deciora-text) !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
            letter-spacing: -0.01em;
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-radius: 24px !important;
            padding: 0.1rem;
            background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(249, 251, 255, 0.93) 100%);
        }

        div[data-testid="stForm"] {
            border-radius: 24px !important;
            padding: 0.15rem;
        }

        [data-testid="stFileUploaderDropzone"] {
            background: rgba(247, 249, 253, 0.92);
            border: 1px dashed rgba(125, 142, 197, 0.48);
            border-radius: 18px;
        }

        [data-testid="stFileUploaderDropzoneInstructions"] div,
        [data-testid="stFileUploaderDropzoneInstructions"] span,
        [data-testid="stFileUploaderDropzoneInstructions"] small {
            color: var(--deciora-text-soft) !important;
            font-size: 0.86rem !important;
        }

        .stTextArea textarea,
        .stTextInput input,
        [data-baseweb="textarea"] textarea {
            background: rgba(252, 253, 255, 0.96) !important;
            color: var(--deciora-text) !important;
            border: 1px solid rgba(57, 74, 112, 0.16) !important;
            border-radius: 16px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
        }

        .stTextArea textarea:focus,
        .stTextInput input:focus,
        [data-baseweb="textarea"] textarea:focus {
            border-color: rgba(125, 142, 197, 0.50) !important;
            box-shadow: 0 0 0 1px rgba(125, 142, 197, 0.18), 0 0 0 4px rgba(125, 142, 197, 0.10) !important;
        }

        [data-baseweb="select"] > div,
        [data-testid="stSelectbox"] [data-baseweb="select"] > div {
            background: rgba(252, 253, 255, 0.96) !important;
            color: var(--deciora-text) !important;
            border: 1px solid rgba(57, 74, 112, 0.16) !important;
            border-radius: 16px !important;
            box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.9);
        }

        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button,
        div[data-testid="stDownloadButton"] > button {
            width: 100%;
            border-radius: 16px;
            border: 1px solid rgba(57, 74, 112, 0.16);
            background: rgba(255, 255, 255, 0.88);
            color: var(--deciora-text);
            font-weight: 700;
            font-size: 0.92rem;
            letter-spacing: -0.01em;
            min-height: 2.62rem;
            box-shadow: var(--deciora-shadow-sm);
            transition: all 180ms ease;
        }

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover,
        div[data-testid="stDownloadButton"] > button:hover {
            border-color: rgba(125, 142, 197, 0.34);
            transform: translateY(-1px);
            box-shadow: 0 18px 32px rgba(19, 34, 60, 0.09);
        }

        div[data-testid="stButton"] > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #22304f 0%, #31456f 100%);
            color: #f7f9fd;
            border-color: rgba(35, 49, 81, 0.42);
        }

        div[data-testid="stButton"] > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            background: linear-gradient(135deg, #263657 0%, #38507c 100%);
        }

        div[data-testid="stLinkButton"] a {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            width: 100%;
            min-height: 2.62rem;
            border-radius: 16px;
            border: 1px solid rgba(57, 74, 112, 0.16);
            background: rgba(255, 255, 255, 0.92);
            color: var(--deciora-text);
            font-weight: 700;
            font-size: 0.92rem;
            text-decoration: none;
            box-shadow: var(--deciora-shadow-sm);
            transition: all 180ms ease;
        }

        div[data-testid="stLinkButton"] a:hover {
            border-color: rgba(125, 142, 197, 0.34);
            transform: translateY(-1px);
        }

        .stProgress > div > div > div > div {
            background: linear-gradient(90deg, #31456f 0%, #7d8ec5 100%);
        }

        hr {
            border-color: rgba(57, 74, 112, 0.12) !important;
        }

        [data-testid="stExpander"] {
            border: 1px solid rgba(57, 74, 112, 0.12);
            border-radius: 18px;
            background: rgba(255, 255, 255, 0.84);
            box-shadow: var(--deciora-shadow-sm);
        }

        [data-testid="stExpander"] summary,
        [data-testid="stExpander"] summary p,
        [data-testid="stExpander"] summary span {
            color: var(--deciora-text) !important;
            font-weight: 700 !important;
            font-size: 0.92rem !important;
        }

        div[data-testid="stAlert"] {
            background: rgba(255, 255, 255, 0.84);
            border: 1px solid rgba(57, 74, 112, 0.14);
            color: var(--deciora-text);
            border-radius: 18px;
            box-shadow: var(--deciora-shadow-sm);
        }

        div[data-testid="stAlert"] p,
        div[data-testid="stAlert"] li,
        div[data-testid="stAlert"] span {
            color: var(--deciora-text) !important;
        }

        .divider-gap {
            height: 0.45rem;
        }

        @media (max-width: 900px) {
            .hero {
                padding: 0.94rem 0.92rem 0.98rem 0.92rem;
            }

            .hero-top {
                gap: 0.7rem;
                margin-bottom: 0.72rem;
            }

            .shortlist-grid,
            .shortlist-mini-list {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar_brand() -> None:
    st.sidebar.markdown(
        "".join(
            [
                '<div class="sidebar-brand">',
                '<div class="sidebar-brand-row">',
                _brand_mark_html(),
                '<div>',
                '<div class="sidebar-brand-name">Deciora</div>',
                '<div class="sidebar-brand-tag">Decision engine for opportunity choices</div>',
                "</div>",
                "</div>",
                '<div class="sidebar-brand-note">Calm, evidence-led guidance for deciding what deserves your time.</div>',
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_sidebar_track_panel(title: str, body: str, steps: list[str]) -> None:
    step_html = "".join(f"<li>{escape(step)}</li>" for step in steps)
    st.sidebar.markdown(
        "".join(
            [
                '<div class="sidebar-track-card">',
                '<div class="sidebar-track-kicker">Track</div>',
                f'<div class="sidebar-track-title">{escape(title)}</div>',
                f'<div class="sidebar-track-body">{escape(body)}</div>',
                f'<ol class="sidebar-track-steps">{step_html}</ol>',
                "</div>",
            ]
        ),
        unsafe_allow_html=True,
    )


def render_hero(kicker: str, title: str, body: str, footnote: str = "") -> None:
    footnote_html = f'<div class="hero-footnote">{escape(footnote)}</div>' if footnote else ""
    st.markdown(
        "".join(
            [
                '<div class="hero">',
                '<div class="hero-top">',
                '<div class="hero-brand">',
                _brand_mark_html(hero=True),
                '<div>',
                '<div class="hero-brand-name">Deciora</div>',
                '<div class="hero-brand-tag">Refined decision support for career and research choices</div>',
                "</div>",
                "</div>",
                f'<div class="hero-kicker">{escape(kicker)}</div>',
                "</div>",
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


def render_process_steps(title: str, steps: list[str]) -> None:
    step_cards = "".join(
        "".join(
            [
                '<div class="shortlist-mini-card">',
                f'<strong>Step {index}</strong>',
                f"<span>{escape(step)}</span>",
                "</div>",
            ]
        )
        for index, step in enumerate(steps, start=1)
    )
    st.markdown(
        "".join(
            [
                '<div class="section-shell">',
                f'<div class="section-title">{escape(title)}</div>',
                f'<div class="shortlist-mini-list">{step_cards}</div>',
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


def _semantic_pill_html(label: str, *, base_class: str = "track-pill") -> str:
    lowered = clean_text(label).lower()
    if any(token in lowered for token in ("apply", "reach out now", "found", "success", "low risk")):
        bg, fg, border = "#edf8f0", "#25613d", "#b7dec2"
    elif any(token in lowered for token in ("consider", "later", "after tailoring", "medium", "moderate", "priority")):
        bg, fg, border = "#fff7ea", "#8c6123", "#edd5a7"
    elif any(token in lowered for token in ("skip", "missing", "insufficient", "warning", "issue", "high")):
        bg, fg, border = "#fff2f1", "#9d3f3f", "#ecc4c4"
    else:
        bg, fg, border = "#edf2fb", "#31456f", "rgba(125, 142, 197, 0.24)"
    return (
        f'<span class="{escape(base_class)}" '
        f'style="background:{bg};color:{fg};border:1px solid {border};">{escape(label)}</span>'
    )


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
    recommendation_badge = _semantic_pill_html(recommendation)
    st.markdown(
        "".join(
            [
                '<div class="shortlist-card">',
                '<div class="shortlist-head">',
                "<div>",
                f'<div class="shortlist-title">#{rank} · {escape(name)}</div>',
                f'<div class="shortlist-meta">{escape(meta_text)}</div>',
                "</div>",
                recommendation_badge,
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
