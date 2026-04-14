from __future__ import annotations

from pathlib import Path

import streamlit as st

try:
    from dotenv import load_dotenv
except ModuleNotFoundError:  # pragma: no cover - optional dependency fallback
    load_dotenv = None

from utils.ui import inject_styles, render_sidebar_brand


DOTENV_AVAILABLE = load_dotenv is not None
DOTENV_FILE_PRESENT = Path(".env").exists()

if DOTENV_AVAILABLE:
    load_dotenv()

st.set_page_config(
    page_title="Deciora",
    layout="wide",
    initial_sidebar_state="expanded",
)
inject_styles()
render_sidebar_brand()

navigation = st.navigation(
    {
        "Deciora": [
            st.Page("pages/home.py", title="Home", icon=":material/home:", default=True),
            st.Page("pages/job_track.py", title="Career Track", icon=":material/work:"),
            st.Page("pages/research_track.py", title="Research Track", icon=":material/school:"),
        ]
    }
)

if DOTENV_FILE_PRESENT and not DOTENV_AVAILABLE:
    st.sidebar.caption("`.env` detected, but `python-dotenv` is not installed. Environment variables were not loaded automatically.")

navigation.run()
