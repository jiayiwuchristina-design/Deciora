from __future__ import annotations

import streamlit as st

from utils.ui import render_entry_card, render_hero, render_process_steps


render_hero(
    "Decision Engine",
    "Decide What Deserves Your Time.",
    "Deciora helps you judge whether a role or research opportunity is worth pursuing with calm scoring, grounded evidence, and next actions you can trust.",
    footnote="Career Track answers: should you apply? Research Track answers: should you reach out?",
)

left, right = st.columns(2, gap="large")
with left:
    render_entry_card(
        "Career Track",
        "Evaluate Career Opportunities",
        "Assess whether a role is worth the application effort with fit scoring, risk checks, layered explanation, and focused next steps.",
        [
            "Bring a CV and a job URL or pasted description",
            "See Fit Score, Risk Level, Recommendation, and evidence coverage",
            "Know what to tighten before you apply",
        ],
    )
    if st.button("Open Career Track", use_container_width=True, type="primary"):
        st.switch_page("pages/job_track.py")

with right:
    render_entry_card(
        "Research Track",
        "Evaluate Research Outreach",
        "Judge whether a professor, lab, or research target is worth contacting and generate a grounded outreach package from official sources.",
        [
            "Bring a CV and define your research direction",
            "Review ranked targets with fit and outreach-feasibility scoring",
            "Generate subject lines, outreach copy, and pre-email improvements",
        ],
    )
    if st.button("Open Research Track", use_container_width=True, type="primary"):
        st.switch_page("pages/research_track.py")

render_process_steps(
    "How Deciora Works",
    [
        "Collect opportunity evidence and candidate-side signals from the inputs you provide.",
        "Score whether the opportunity is worth pursuing now with transparent decision logic.",
        "Explain the recommendation and show what to improve before you spend more time.",
    ],
)
