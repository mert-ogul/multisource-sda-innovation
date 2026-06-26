# Multi-Source SDA Innovation Studio — Project Report

**Author:** Innovation Studio case study  
**Date:** June 2026  
**Status:** Functional prototype with live APIs and user datasets

---

## 1. Scope

### Problem

Small Domestic Appliance (SDA) innovation scouting requires combining fragmented signals — patents (supply/R&D), news (market momentum), reviews (user pain), social discourse, and product catalogs (competitive density). Teams lack a single, explainable view that ties a product theme to evidence and a go/no-go recommendation.

### Solution

A Python Streamlit application that:

1. Ingests multi-source evidence into a unified schema
2. Matches evidence to a free-text opportunity theme
3. Scores opportunities using transparent Desirability–Viability–Feasibility (D–V–F) logic
4. Presents an Opportunity Card with demand/supply signals, score breakdowns, and evidence snippets

### In scope

| Area | Implementation |
|------|----------------|
| UI | Streamlit with sidebar theme setup, opportunity card, evidence tabs, charts |
| Live patents | USPTO Public Search via `patent_client` (category-aware queries) |
| Live news | newsapi.ai / Event Registry REST API |
| User reviews | Amazon coffee-maker CSV, Yelp Austin reviews, filtered Amazon reviews |
| User catalog | 10k synthetic appliance SKU dataset with cleaning and SDA mapping |
| Demo mode | Generated sample CSVs (~185 items) for offline use |
| Real data mode | No mixing of demo data when live/user sources are active |
| Analytics | Keyword + TF-IDF matching, TextBlob sentiment, review insight extraction |
| Testing | 71 pytest cases |

### Out of scope

- Production deployment, authentication, scheduling
- LLM-based summarization or scoring
- Live Reddit/social API (extension point only)
- Empirical calibration of D–V–F weights against business outcomes
- Patent claim parsing, citation networks, or legal FTO analysis

---

## 2. Architecture

### High-level flow

```
User theme (sidebar)
        │
        ▼
┌───────────────────┐
│  storage/         │
│  datasets.py      │  load_all_evidence(theme)
│                   │  → real-data mode check
│                   │  → suppress sample back-fill
└─────────┬─────────┘
          │
    ┌─────┴─────┬─────────┬─────────┬─────────┐
    ▼           ▼         ▼         ▼         ▼
 patents     news     reviews   social    catalog
 (live/      (live/   (user     (CSV/     (synthetic
  CSV)        CSV)     datasets)  empty)   10k SKUs)
    │           │         │         │         │
    └─────┬─────┴─────────┴─────────┴─────────┘
          ▼
   processing/matching.py  →  filter + rank by relevance
          ▼
   domain/scoring.py       →  D–V–F + OpportunityCard
          ▼
   ui/components.py        →  Streamlit presentation
```

### Layering

| Layer | Modules | Rule |
|-------|---------|------|
| UI | `app.py`, `ui/*` | Thin shell; no business logic |
| Storage | `storage/datasets.py` | Orchestrates ingestion, real-data mode |
| Ingestion | `ingestion/*` | Per-source loaders → `EvidenceItem` |
| Processing | `processing/*` | Cleaning, matching, sentiment, insights |
| Domain | `domain/*` | Models and scoring; no Streamlit imports |

### Data model

All sources normalize to **`EvidenceItem`**:

- `source` — patent | news | review | social | catalog
- `title`, `text`, `date`, `category`, `region`
- `metadata` — source-specific fields + `data_origin` (`sample` | `user_provided` | `live`)
- `relevance_score`, `match_explanation` — set during theme matching

### Real data mode

When any source returns live or user-provided data, `datasets.py` suppresses sample CSVs for all other sources. This prevents misleading mixes (e.g. live news alongside fabricated Reddit posts). Sources without real data return empty with a clear label in the UI expander.

---

## 3. Data sources (current deployment)

| Source | Origin | Dataset / API | Approx. volume |
|--------|--------|---------------|----------------|
| Patents | Live API | `patent_client` → USPTO Public Search | Up to 25 per theme |
| News | Live API | newsapi.ai Event Registry | Up to 25 per theme |
| Reviews | User data | `coffee_maker.csv`, `ratings_and_sentiments.csv`, `amazon_reviews.txt` | ~7,200 (capped at 2,500/file by default) |
| Catalog | User data | `appliance-skus-10k-synthetic.csv` | 10,000 SKUs (8,741 Kitchen, 1,259 Coffee) |
| Social | — | Not connected in real mode | 0 (intentionally empty) |

### Review processing pipeline

1. **Ingest** — load CSV/TXT from `data/raw/`
2. **Filter** — map Amazon products to SDA categories via keyword rules
3. **Clean** — lowercase, tokenize, stopword handling
4. **Sentiment** — TextBlob polarity per review
5. **Insights** — extract pain points (noise, leak, cleaning…), desired features (quiet, compact…), delighters (love, recommend…), and TF-IDF topics

### Catalog processing pipeline

1. **Clean** — normalize Company, Brand, SKU, Energy (watts)
2. **Map** — appliance type → SDA category (Kettle→Coffee; Toaster/Dishwasher/etc.→Kitchen)
3. **Enrich** — attach `category_sku_total` and niche density label (crowded / moderate / sparse)

### Patent search strategy

Category-specific anchor queries are tried first (e.g. `air purifier`, `coffee maker`, `robot vacuum`), then the full theme phrase, then shorter token combinations. Searches run against USPTO **title** and **abstract** fields until results are found.

---

## 4. Insights from the build

### What works well

1. **Unified schema** — adding a new source requires only a loader returning `EvidenceItem` list; matching and scoring are source-agnostic.
2. **Explainability** — keyword overlap, TF-IDF cosine, and lexicon-based pain/desire counts are inspectable in code and UI.
3. **Provenance** — `data_origin` on every item and per-source summaries prevent demo data from being mistaken for live research.
4. **Real user voice at scale** — 7k+ reviews surface strong Coffee-category pain themes (cleaning difficulty, noise, leakage) that align with predefined opportunity themes.
5. **Catalog crowding signal** — 8,741 Kitchen SKUs vs 1,259 Coffee SKUs gives a credible “crowded niche” indicator for kitchen appliances.

### Example interpretation (Coffee theme)

For *“quiet single-serve coffee maker for early mornings”*:

- **Desirability** tends high — review text frequently mentions noise, cleaning, and compact size
- **Viability** supported by live news hits and large review corpus
- **Feasibility** moderated by patent volume in coffee/brewing space
- **Catalog** shows Coffee niche as less crowded than Kitchen (kettle SKUs only)

### Matching behavior

- Category filter is strict — only items in the selected SDA category pass
- Minimum relevance threshold (default 0.08) drops weak matches
- Time window filters by item date when available (live patents and news include dates; some review rows may not)

---

## 5. D–V–F scoring (summary)

| Dimension | Primary inputs | Intuition |
|-----------|----------------|-----------|
| **Desirability** | Reviews, social | User pain + desired features + negative sentiment → opportunity |
| **Viability** | News, catalog | Market activity and product landscape |
| **Feasibility** | Patents, catalog | Technical maturity minus patent crowding penalty |

**Recommendation:** Explore (avg ≥ 60, D ≥ 55) | Watch (avg ≥ 45) | Deprioritize

Crowdedness is surfaced as its own index — high patent concentration is a competitive signal, not an automatic veto.

---

## 6. Limitations

| Limitation | Impact |
|------------|--------|
| **Python 3.11–3.12 for patents** | `patent_client` does not install on 3.13+ |
| **USPTO API reliability** | Occasional timeouts or empty responses; no retry queue |
| **News API tokens** | Trial accounts limited; each search consumes tokens |
| **English-only** | Keyword lists and TextBlob are English-centric |
| **Heuristic scoring** | D–V–F weights are illustrative, not validated on revenue/NPS |
| **Catalog coverage** | Synthetic 10k set maps only to Kitchen + Coffee; no Air/Floor/Robotics SKUs |
| **Amazon review filter** | Only ~224 SDA-relevant rows from general Amazon dump |
| **No social in real mode** | Reddit connector is a stub; social tab empty unless user adds CSV |
| **Performance** | First analysis with 7k reviews + 10k catalog can take 15–30 seconds |
| **No persistence** | No database; evidence reloaded each analysis |

---

## 7. Next steps

### Near term (high value)

1. **Reddit / social connector** — implement live search when credentials are set, matching patents/news pattern
2. **Patent abstract fetch** — enrich live patent `text` field beyond title-only for better matching
3. **Caching** — `@st.cache_data` on `load_all_evidence(theme)` to speed repeat analyses
4. **Expand catalog mapping** — add Air purifier, vacuum, and robot vacuum types to synthetic or real PIM data

### Medium term

5. **Embedding-based matching** — optional sentence-transformer mode alongside TF-IDF
6. **Category-specific lexicons** — tune pain/desire terms per SDA category in config
7. **Batch theme comparison** — portfolio view across multiple themes
8. **Export** — PDF/PPTX opportunity cards with charts

### Long term

9. **Score calibration** — backtest D–V–F weights against launch outcomes or sales proxies
10. **Production hardening** — auth, job queue for API calls, observability, rate-limit handling
11. **EPO integration** — full European patent coverage when OPS credentials are configured

---

## 8. How to run

See [`README.md`](../README.md) for full setup. Minimal commands:

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
cp .env.example .env   # set USE_PATENT_CLIENT=true and NEWS_API_KEY
streamlit run app.py
pytest tests/ -v
```

Place user datasets in `data/raw/` as documented in the README.

---

## Appendix: Key files

| File | Role |
|------|------|
| `storage/datasets.py` | Evidence aggregation, real-data mode |
| `ingestion/patent_client_source.py` | USPTO/EPO live patent search |
| `ingestion/newsapi_source.py` | Event Registry news search |
| `ingestion/review_sources.py` | Amazon + Yelp review loaders |
| `ingestion/catalog_sources.py` | Synthetic SKU catalog cleaning |
| `processing/matching.py` | Theme relevance scoring |
| `domain/scoring.py` | D–V–F and opportunity card assembly |
