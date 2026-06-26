"""Streamlit entry point — UI only; logic lives in sda_studio package."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from sda_studio.domain.models import Theme
from sda_studio.domain.scoring import build_opportunity_card
from sda_studio.processing.matching import explain_matching
from sda_studio.storage.datasets import analyze_theme
from sda_studio.ui.components import (
    render_charts_tab,
    render_data_banner,
    render_evidence_snippets,
    render_evidence_tabs,
    render_opportunity_card,
    render_project_intro,
    render_sidebar,
)

st.set_page_config(
    page_title="Multi-Source SDA Innovation Studio",
    page_icon="🔌",
    layout="wide",
)


def main() -> None:
    render_project_intro()
    sidebar = render_sidebar()

    if sidebar.analyze_clicked:
        if not sidebar.theme_text:
            st.error("Please enter an opportunity theme.")
            return

        theme = Theme(
            text=sidebar.theme_text,
            category=sidebar.category,
            time_window=sidebar.time_window,
            region=sidebar.region,
        )
        with st.spinner("Loading evidence and matching to theme..."):
            loaded = analyze_theme(theme)
            card = build_opportunity_card(theme, loaded.matched_items, is_sample_data=loaded.is_sample_data)

        st.session_state.loaded = loaded
        st.session_state.card = card
        st.session_state.match_explanation = explain_matching(theme, len(loaded.matched_items))

    if "card" not in st.session_state:
        st.markdown("---")
        st.markdown(
            "Use the **sidebar** to pick a category, choose or edit a theme, set the time window "
            "(and region if available), then click **Analyze opportunity**."
        )
        return

    loaded = st.session_state.loaded
    card = st.session_state.card
    matched = loaded.matched_items

    st.markdown("---")
    render_data_banner(loaded)
    st.caption(st.session_state.match_explanation)

    tab_card, tab_evidence, tab_charts = st.tabs(
        ["Opportunity Card", "Evidence by source", "Charts"]
    )

    with tab_card:
        render_opportunity_card(card)
        render_evidence_snippets(card.evidence_snippets)

    with tab_evidence:
        render_evidence_tabs(matched)

    with tab_charts:
        render_charts_tab(matched)


if __name__ == "__main__":
    main()
