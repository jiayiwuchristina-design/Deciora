from __future__ import annotations

import streamlit as st

from utils.ui import render_entry_card, render_hero


render_hero(
    "AI Opportunity Decision Engine",
    "Choose The Opportunity Path Worth Your Time.",
    "One decision engine, two tracks: evaluate job opportunities or research opportunities with the same product logic of ranking, evidence, recommendation, and next actions.",
    footnote="Career Track answers: should I apply? Research Track answers: should I reach out?",
)

left, right = st.columns(2, gap="large")
with left:
    render_entry_card(
        "Career Track",
        "Job Opportunity",
        "Evaluate company roles with fit scoring, risk checks, layered explanation, and concrete application guidance.",
        [
            "Upload a CV and job URL or description",
            "Get Fit Score, Risk Level, Recommendation, and evidence transparency",
            "See what to improve before you apply",
        ],
    )
    if st.button("Open Career Track", use_container_width=True, type="primary"):
        st.switch_page("pages/job_track.py")

with right:
    render_entry_card(
        "Research Track",
        "Research Opportunity",
        "Find professors worth contacting, judge outreach feasibility, and generate a grounded cold-email package from official sources.",
        [
            "Upload a CV and define research interests",
            "Get a ranked shortlist of professors with fit and feasibility scoring",
            "Generate subject lines, tailored email copy, and pre-email improvements",
        ],
    )
    if st.button("Open Research Track", use_container_width=True, type="primary"):
        st.switch_page("pages/research_track.py")

with st.container(border=True):
    st.markdown("### How the product works")
    st.markdown(
        "\n".join(
            [
                "1. The engine collects opportunity evidence and candidate evidence.",
                "2. It scores whether the opportunity is worth pursuing now.",
                "3. It explains the recommendation and tells you what to do next.",
            ]
        )
    )
