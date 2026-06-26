"""Reusable Streamlit UI fragments."""

from __future__ import annotations

from dataclasses import dataclass

import streamlit as st

from sda_studio.config.categories import PREDEFINED_THEMES, SDACategory, TimeWindow
from sda_studio.domain.models import EvidenceItem, EvidenceSource, OpportunityCard
from sda_studio.storage.datasets import LoadedEvidence, available_regions, load_all_evidence


@dataclass
class SidebarInput:
    theme_text: str
    category: str
    time_window: str
    region: str | None
    analyze_clicked: bool


def render_project_intro() -> None:
    st.title("Multi-Source SDA Innovation Studio")
    st.markdown(
        """
        Scout **Small Domestic Appliance (SDA)** innovation opportunities by combining evidence from
        **patents**, **news**, **user reviews**, **social discussions**, and **product catalog** data.

        Enter an opportunity theme (e.g. *silent compact air purifier for small bedrooms*), then generate an
        **Opportunity Card** with demand/supply signals, Desirability–Viability–Feasibility scores, and
        supporting evidence snippets.
        """
    )


@st.cache_data(show_spinner=False)
def _cached_regions() -> list[str]:
    items, _, _ = load_all_evidence()
    return available_regions(items)


def render_sidebar() -> SidebarInput:
    regions = _cached_regions()

    with st.sidebar:
        st.header("Opportunity setup")

        category = st.selectbox("SDA category", options=[c.value for c in SDACategory], key="sda_category")
        examples = PREDEFINED_THEMES[SDACategory(category)]
        if "theme_text" not in st.session_state:
            st.session_state.theme_text = examples[0]

        example_pick = st.selectbox(
            "Example themes",
            options=["(custom)"] + examples,
            key="example_theme",
        )

        if example_pick != "(custom)":
            st.session_state["theme_text"] = example_pick

        theme_text = st.text_area("Opportunity theme", height=90, key="theme_text")
        time_window = st.selectbox("Time window", options=[w.value for w in TimeWindow], key="time_window")

        st.divider()
        st.subheader("Region / market")
        if regions:
            region_pick = st.selectbox("Filter by region", options=["All regions"] + regions, key="region_pick")
            region = None if region_pick == "All regions" else region_pick
        else:
            st.caption("Not available — no region values in loaded data.")
            region = None

        analyze_clicked = st.button("Analyze opportunity", type="primary", use_container_width=True)

    return SidebarInput(
        theme_text=theme_text.strip(),
        category=category,
        time_window=time_window,
        region=region,
        analyze_clicked=analyze_clicked,
    )


def render_data_banner(loaded: LoadedEvidence) -> None:
    if loaded.is_sample_data:
        st.info("Using **demo/sample** data for all sources.")

    with st.expander("Data sources", expanded=False):
        for summary in loaded.sources:
            st.markdown(f"- **{summary.source.value}**: {summary.item_count} — {summary.label}")


def render_opportunity_card(card: OpportunityCard) -> None:
    st.subheader("Opportunity Card")
    st.markdown(f"**Theme:** {card.theme_title}")
    st.caption(f"Category: {card.category}" + (f" | Region: {card.region}" if card.region else ""))

    cols = st.columns(4)
    cols[0].metric("Desirability", f"{card.scores.desirability:.0f}", help="User pain, desires, sentiment")
    cols[1].metric("Viability", f"{card.scores.viability:.0f}", help="News and catalog market activity")
    cols[2].metric("Feasibility", f"{card.scores.feasibility:.0f}", help="Technical maturity minus crowding")
    cols[3].metric("Recommendation", card.recommendation.value)

    col_d, col_s = st.columns(2)
    with col_d:
        st.markdown("**Demand signals**")
        for bullet in card.demand_signals:
            st.markdown(f"- {bullet}")
    with col_s:
        st.markdown("**Supply signals**")
        for bullet in card.supply_signals:
            st.markdown(f"- {bullet}")

    st.markdown(f"**Patent crowdedness:** {card.scores.crowdedness:.0f}/100 *(competitive signal, not automatically negative)*")

    st.markdown("**Scoring explanation**")
    st.write(card.scores.plain_english)
    with st.expander("Score component breakdown"):
        for comp in card.scores.components:
            sign = "+" if comp.value >= 0 else ""
            st.write(f"**{comp.name}** ({sign}{comp.value:.1f}, weight {comp.weight:.0%}): {comp.explanation}")


def render_evidence_snippets(snippets: list[EvidenceItem]) -> None:
    st.subheader("Evidence snippets")
    if not snippets:
        st.caption("No supporting snippets matched this theme.")
        return
    for item in snippets:
        origin = item.metadata.get("data_origin", "unknown")
        with st.expander(
            f"[{item.source.value}] {item.title[:70]} — relevance {item.relevance_score:.0%} ({origin})"
        ):
            st.write(item.text[:600] or "—")
            st.caption(item.match_explanation)
            meta_parts = []
            if item.date:
                meta_parts.append(f"Date: {item.date}")
            if item.region:
                meta_parts.append(f"Region: {item.region}")
            if meta_parts:
                st.caption(" | ".join(meta_parts))


def _filter(items: list[EvidenceItem], source: EvidenceSource) -> list[EvidenceItem]:
    return [i for i in items if i.source == source]


def render_patents_tab(items: list[EvidenceItem]) -> None:
    subset = _filter(items, EvidenceSource.PATENT)
    st.markdown(f"**{len(subset)}** matched patent records")
    if not subset:
        st.caption("No patent evidence matched this theme and filters.")
        return
    for item in subset[:12]:
        applicant = item.metadata.get("applicant", "—")
        kws = item.metadata.get("keywords", [])
        kw_str = ", ".join(kws[:6]) if kws else "—"
        st.markdown(f"**{item.title}**")
        st.caption(f"Applicant: {applicant} | Relevance: {item.relevance_score:.0%}")
        st.write(item.text[:300])
        st.caption(f"Keywords: {kw_str}")
        st.divider()


def render_news_tab(items: list[EvidenceItem]) -> None:
    subset = _filter(items, EvidenceSource.NEWS)
    st.markdown(f"**{len(subset)}** matched articles")
    if not subset:
        st.caption("No news evidence matched this theme and filters.")
        return
    for item in subset[:12]:
        outlet = item.metadata.get("source_name", "—")
        entities = item.metadata.get("entities", [])
        st.markdown(f"**{item.title}**")
        st.caption(f"Source: {outlet} | Relevance: {item.relevance_score:.0%}")
        st.write(item.text[:300])
        if entities:
            st.caption(f"Mentions: {', '.join(entities[:5])}")
        st.divider()


def render_reviews_tab(items: list[EvidenceItem]) -> None:
    subset = _filter(items, EvidenceSource.REVIEW)
    st.markdown(f"**{len(subset)}** matched reviews")
    if not subset:
        st.caption("No review evidence matched this theme and filters.")
        return
    for item in subset[:12]:
        rating = item.metadata.get("rating")
        sentiment = item.metadata.get("sentiment")
        rating_str = f"{rating:.1f}/5" if rating is not None else "—"
        sent_str = f"{sentiment:.2f}" if sentiment is not None else "—"
        st.markdown(f"**{item.title}**")
        st.caption(f"Rating: {rating_str} | Sentiment: {sent_str} | Relevance: {item.relevance_score:.0%}")
        st.write(item.text[:300])
        st.divider()


def render_social_tab(items: list[EvidenceItem]) -> None:
    subset = _filter(items, EvidenceSource.SOCIAL)
    st.markdown(f"**{len(subset)}** matched social posts")
    if not subset:
        st.caption("No social evidence matched this theme and filters.")
        return
    for item in subset[:12]:
        platform = item.metadata.get("platform", "reddit")
        upvotes = item.metadata.get("upvotes", 0)
        comments = item.metadata.get("comment_count", 0)
        sentiment = item.metadata.get("sentiment")
        sent_str = f"{sentiment:.2f}" if sentiment is not None else "—"
        st.markdown(f"**{item.title}**")
        st.caption(
            f"{platform} | {upvotes} upvotes | {comments} comments | "
            f"Sentiment: {sent_str} | Relevance: {item.relevance_score:.0%}"
        )
        st.write(item.text[:300])
        st.divider()


def render_catalog_tab(items: list[EvidenceItem]) -> None:
    subset = _filter(items, EvidenceSource.CATALOG)
    st.markdown(f"**{len(subset)}** matched catalog products")
    if not subset:
        st.caption("No catalog products matched this theme and filters.")
        return
    for item in subset[:12]:
        brand = item.metadata.get("brand", "—")
        price = item.metadata.get("price_usd")
        price_str = f"${price:.0f}" if price is not None else "—"
        attrs = item.metadata.get("attributes", {})
        if attrs:
            attr_str = ", ".join(f"{k}={v}" for k, v in list(attrs.items())[:4])
        else:
            attr_str = item.text
        appliance = item.metadata.get("appliance_type")
        energy = item.metadata.get("energy_watts")
        energy_str = f"{energy:.0f}W" if energy is not None else "energy n/a"
        niche = item.metadata.get("category_niche_density")
        extra = f" | {appliance} | {energy_str}" if appliance else ""
        niche_str = f" | niche: {niche}" if niche else ""
        st.markdown(f"**{item.title}** — {brand}")
        st.caption(
            f"Price: {price_str}{extra}{niche_str} | Relevance: {item.relevance_score:.0%}"
        )
        st.write(attr_str)
        st.divider()


def render_evidence_tabs(matched: list[EvidenceItem]) -> None:
    tabs = st.tabs(["Patents", "News", "Reviews", "Social", "Product catalog"])
    with tabs[0]:
        render_patents_tab(matched)
    with tabs[1]:
        render_news_tab(matched)
    with tabs[2]:
        render_reviews_tab(matched)
    with tabs[3]:
        render_social_tab(matched)
    with tabs[4]:
        render_catalog_tab(matched)


def render_charts_tab(matched: list[EvidenceItem]) -> None:
    from sda_studio.ui.charts import (
        catalog_by_brand,
        evidence_count_by_source,
        sentiment_distribution,
        top_keywords_chart,
        trend_over_time,
    )

    st.plotly_chart(evidence_count_by_source(matched), use_container_width=True)
    st.plotly_chart(trend_over_time(matched), use_container_width=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.plotly_chart(sentiment_distribution(matched), use_container_width=True)
    with col_b:
        st.plotly_chart(top_keywords_chart(matched), use_container_width=True)
    st.plotly_chart(catalog_by_brand(matched), use_container_width=True)
