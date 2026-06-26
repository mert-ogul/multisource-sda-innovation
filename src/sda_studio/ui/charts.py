"""Plotly chart builders for evidence summaries."""

from __future__ import annotations

from collections import Counter

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from sda_studio.domain.models import EvidenceItem, EvidenceSource


def evidence_count_by_source(items: list[EvidenceItem]) -> go.Figure:
    counts = Counter(i.source.value for i in items)
    df = pd.DataFrame({"source": list(counts.keys()), "count": list(counts.values())})
    fig = px.bar(df, x="source", y="count", title="Evidence count by source", color="source")
    fig.update_layout(showlegend=False, height=350)
    return fig


def trend_over_time(items: list[EvidenceItem], source: EvidenceSource | None = None) -> go.Figure:
    dated = [i for i in items if i.date is not None]
    if source:
        dated = [i for i in dated if i.source == source]
    if not dated:
        fig = go.Figure()
        fig.update_layout(title="Timeline by source (no dated evidence)", height=350)
        return fig
    df = pd.DataFrame({"date": [i.date for i in dated], "source": [i.source.value for i in dated]})
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)
    monthly = df.groupby(["month", "source"]).size().reset_index(name="count")
    fig = px.line(
        monthly,
        x="month",
        y="count",
        color="source",
        title="Timeline by source",
        markers=True,
    )
    fig.update_layout(height=380, xaxis_title="Month")
    return fig


def sentiment_distribution(items: list[EvidenceItem]) -> go.Figure:
    rows = []
    for i in items:
        if i.source not in (EvidenceSource.REVIEW, EvidenceSource.SOCIAL):
            continue
        sent = i.metadata.get("sentiment")
        if sent is not None:
            rows.append({"source": i.source.value, "sentiment": sent})
    if not rows:
        fig = go.Figure()
        fig.update_layout(title="Sentiment distribution (no data)", height=350)
        return fig
    df = pd.DataFrame(rows)
    fig = px.histogram(df, x="sentiment", color="source", barmode="overlay", nbins=20, title="Sentiment distribution")
    fig.update_layout(height=350)
    return fig


def top_keywords_chart(items: list[EvidenceItem], top_n: int = 12) -> go.Figure:
    from sda_studio.processing.keywords import extract_top_keywords

    texts = [f"{i.title} {i.text}" for i in items]
    keywords = extract_top_keywords(texts, top_n=top_n)
    if not keywords:
        fig = go.Figure()
        fig.update_layout(title="Top keywords (no data)", height=350)
        return fig
    df = pd.DataFrame({"keyword": keywords, "rank": range(len(keywords), 0, -1)})
    fig = px.bar(df, x="rank", y="keyword", orientation="h", title="Top keywords / topics")
    fig.update_layout(height=400, yaxis={"categoryorder": "total ascending"})
    return fig


def catalog_by_brand(items: list[EvidenceItem]) -> go.Figure:
    catalog = [i for i in items if i.source == EvidenceSource.CATALOG]
    brands = Counter(i.metadata.get("brand", "Unknown") for i in catalog)
    if not brands:
        fig = go.Figure()
        fig.update_layout(title="Catalog coverage by brand (no data)", height=350)
        return fig
    df = pd.DataFrame({"brand": list(brands.keys()), "count": list(brands.values())})
    df = df.sort_values("count", ascending=True)
    fig = px.bar(df, x="count", y="brand", orientation="h", title="Product catalog coverage by brand")
    fig.update_layout(height=380)
    return fig
