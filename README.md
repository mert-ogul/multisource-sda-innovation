# Multi-Source SDA Innovation Studio

A Python **Streamlit** app for scouting **Small Domestic Appliance (SDA)** innovation opportunities. Given a product theme (e.g. *“silent compact air purifier for small bedrooms”*), it combines evidence from **patents**, **news**, **reviews**, **social**, and **product catalog** data — then produces an **Opportunity Card** with demand/supply signals, Desirability–Viability–Feasibility (D–V–F) scores, transparent explanations, and evidence snippets.

The app supports three operating modes:

| Mode | When | What loads |
|------|------|------------|
| **Demo** | No API keys, no `data/raw/` datasets | Sample CSVs in `data/sample/` |
| **Real data** | Live APIs and/or your datasets in `data/raw/` | Only real sources — **no mock Reddit or demo patents mixed in** |
| **Mixed user** | Some files in `data/raw/`, rest from sample | Per-source: raw overrides sample |

---

## Quick start (full stack — your current setup)

Use **Python 3.11 or 3.12** (required for live patents via `patent_client`).

```bash
cd "Multi-Source SDA Innovation Studio"

# Create and activate environment
python3.11 -m venv .venv311
source .venv311/bin/activate        # Windows: .venv311\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API keys and flags
cp .env.example .env
# Edit .env — at minimum:
#   USE_PATENT_CLIENT=true
#   NEWS_API_KEY=your-newsapi-ai-key
#   USE_LIVE_NEWS=true

# Optional: generate demo CSVs (fallback when no real data configured)
python scripts/generate_sample_data.py

# Run the app
streamlit run app.py
```

Open **http://localhost:8501**, pick a category and theme, then click **Analyze opportunity**.

Expand **Data sources** in the UI to confirm what loaded (e.g. live patents, live news, user reviews, synthetic catalog).

---

## Quick start (demo only — no APIs, no raw data)

```bash
python3.11 -m venv .venv311
source .venv311/bin/activate
pip install -r requirements.txt
python scripts/generate_sample_data.py
streamlit run app.py
```

The UI shows *Using demo/sample data for all sources.*

---

## Sidebar workflow

1. **SDA category** — Air, Kitchen, Coffee, Floor Care, Robotics
2. **Example themes** or custom theme text
3. **Time window** — filters matched evidence; also sets news API `dateStart`
4. **Region** — optional filter when regions exist in loaded data
5. **Analyze opportunity** — triggers live API calls (patents, news) and theme matching

Patents and news are fetched **per theme** when you analyze — not on initial page load.

---

## Data sources

### Live APIs (`.env`)

| Source | Enable | Provider | Notes |
|--------|--------|----------|-------|
| Patents | `USE_PATENT_CLIENT=true` | [patent_client](https://github.com/parkerhancock/patent_client) → USPTO Public Search | No API key for US; Python 3.11–3.12 only |
| News | `NEWS_API_KEY` + `USE_LIVE_NEWS=true` | [newsapi.ai](https://newsapi.ai/documentation) (Event Registry) | ~1 token per search (recent data) |
| EPO patents | `EPO_OPS_CONSUMER_KEY` / `SECRET` | EPO Inpadoc via patent_client | Optional |

### User datasets (`data/raw/`)

| File | Source | SDA categories |
|------|--------|----------------|
| `coffee_maker.csv` | Amazon coffee-maker reviews | Coffee |
| `ratings_and_sentiments.csv` | Yelp Austin coffee shops + attribute sentiments | Coffee |
| `raw_yelp_review_data.csv` | Yelp reviews (fallback) | Coffee |
| `amazon_reviews.txt` | Amazon product reviews (tab-separated) | Air, Kitchen, Coffee, Floor Care, Robotics |
| `appliance-skus-10k-synthetic.csv` | Synthetic appliance catalog (10k SKUs) | Kitchen, Coffee |

Reviews are cleaned, tokenized, and enriched with **sentiment**, **pain points**, **desired features**, **delighters**, and **topics**.

The synthetic catalog cleans malformed **Company**, **Brand**, **SKU**, and **Energy Consumption** fields and reports **niche density** (crowded / moderate / sparse) in opportunity scoring.

### Standard CSV fallback (`data/raw/` or `data/sample/`)

| Source | Filename |
|--------|----------|
| Patents | `patents.csv` |
| News | `news.csv` |
| Reviews | `reviews.csv` |
| Social | `social.csv` |
| Catalog | `product_catalog.csv` |

**Priority per file:** `data/raw/` → `data/sample/`

### Real data mode (no mixing demo data)

When **any** live API or user dataset is active, sample CSVs are **not** used for other sources. For example:

- Live news + user reviews → social shows **0 items** (not mock Reddit)
- Live patents enabled → demo `patents.csv` is **not** loaded

Sources without real data appear as empty in the **Data sources** expander.

---

## Environment variables

Copy `.env.example` to `.env`:

```bash
# Patents (USPTO — no key required)
USE_PATENT_CLIENT=true
PATENT_CLIENT_MAX_RESULTS=25

# News (newsapi.ai / Event Registry)
NEWS_API_KEY=your-api-key-here
USE_LIVE_NEWS=true
NEWS_API_MAX_RESULTS=25

# Reviews (optional cap per dataset file; 0 = unlimited)
REVIEWS_MAX_PER_SOURCE=2500

# Optional EPO patents
EPO_OPS_CONSUMER_KEY=
EPO_OPS_CONSUMER_SECRET=

# Reddit (extension point — not implemented)
REDDIT_CLIENT_ID=
REDDIT_CLIENT_SECRET=
REDDIT_USER_AGENT=sda-innovation-studio/1.0
```

**Security:** Never commit `.env` to git. Rotate API keys if exposed.

---

## Tests

```bash
source .venv311/bin/activate
PYTHONPATH=src pytest tests/ -v
```

71 tests cover ingestion, live API connectors (mocked), review/catalog datasets, real-data mode, matching, scoring, and sample themes.

---

## Project structure

```
app.py                              # Streamlit entry (thin UI shell)
src/sda_studio/
  config/
    categories.py                   # SDA categories, themes, time windows
    settings.py                     # .env loading
    patent_search.py                # Per-category USPTO query terms
    catalog_mapping.py              # Appliance type → SDA category
    review_keywords.py              # Amazon review → SDA category
  domain/
    models.py                       # EvidenceItem, Theme, OpportunityCard
    scoring.py                      # D–V–F scoring
  ingestion/
    csv_loader.py                   # CSV validation, provenance
    patents.py                      # CSV or patent_client
    patent_client_source.py         # USPTO / EPO live search
    news.py                         # CSV or newsapi.ai
    newsapi_source.py               # Event Registry API client
    reviews.py                        # CSV or user review datasets
    review_sources.py               # Amazon + Yelp loaders
    catalog.py                      # CSV or synthetic SKU catalog
    catalog_sources.py              # Catalog cleaning + mapping
    social.py                       # Social CSV (demo)
  processing/
    cleaning.py                     # Normalize, tokenize
    matching.py                     # Theme relevance (TF-IDF + keywords)
    sentiment.py                    # TextBlob polarity
    keywords.py                     # TF-IDF keyword extraction
    review_insights.py              # Pain / desire / delight extraction
  storage/
    datasets.py                     # load_all_evidence(), real-data mode
  ui/
    components.py                   # Streamlit fragments
    charts.py                       # Plotly charts
data/
  raw/                              # Your datasets + API-backed mode
  sample/                           # Generated demo CSVs
  processed/                        # Optional copies from prepare_data.py
scripts/
  generate_sample_data.py
  prepare_data.py
tests/
reports/
  report.md                         # Case-study report
```

---

## Optional scripts

```bash
# Copy sample data to data/processed/ and validate
python scripts/prepare_data.py

```

---

## Troubleshooting

| Issue | Fix |
|-------|-----|
| Patents always 0 | Use Python 3.11/3.12, set `USE_PATENT_CLIENT=true`, restart Streamlit, click **Analyze** |
| `patent_client` install fails | Use Python 3.11 or 3.12 (not 3.13+) |
| News empty | Check `NEWS_API_KEY`, token quota, and theme keywords |
| Slow first analysis | Live patents + 7k reviews + 10k catalog — expect 15–30s |
| Social empty in real mode | Expected — add `data/raw/social.csv` or Reddit API (future) |

---

## Further reading

- **Case-study report:** [`reports/report.md`](reports/report.md)



