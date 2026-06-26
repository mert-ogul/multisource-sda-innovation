"""Application settings loaded from environment."""

from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
SAMPLE_DIR = DATA_DIR / "sample"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_ROOT / "reports"


@dataclass(frozen=True)
class APISettings:
    epo_consumer_key: str | None
    epo_consumer_secret: str | None
    news_api_key: str | None
    reddit_client_id: str | None
    reddit_client_secret: str | None
    reddit_user_agent: str
    use_patent_client: bool
    patent_client_max_results: int
    use_live_news: bool
    news_api_max_results: int

    @property
    def has_epo(self) -> bool:
        return bool(self.epo_consumer_key and self.epo_consumer_secret)

    @property
    def has_news_api(self) -> bool:
        return bool(self.news_api_key)

    @property
    def live_news_enabled(self) -> bool:
        return self.has_news_api and self.use_live_news

    @property
    def has_reddit(self) -> bool:
        return bool(self.reddit_client_id and self.reddit_client_secret)


def _env_bool(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> APISettings:
    max_results_raw = os.getenv("PATENT_CLIENT_MAX_RESULTS", "25")
    try:
        patent_client_max_results = max(1, min(100, int(max_results_raw)))
    except ValueError:
        patent_client_max_results = 25

    news_max_raw = os.getenv("NEWS_API_MAX_RESULTS", "25")
    try:
        news_api_max_results = max(1, min(100, int(news_max_raw)))
    except ValueError:
        news_api_max_results = 25

    news_api_key = os.getenv("NEWS_API_KEY") or None
    use_live_news_default = bool(news_api_key)
    use_live_news = _env_bool("USE_LIVE_NEWS", default=use_live_news_default)

    return APISettings(
        epo_consumer_key=os.getenv("EPO_OPS_CONSUMER_KEY") or None,
        epo_consumer_secret=os.getenv("EPO_OPS_CONSUMER_SECRET") or None,
        news_api_key=news_api_key,
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID") or None,
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET") or None,
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "sda-innovation-studio/1.0"),
        use_patent_client=_env_bool("USE_PATENT_CLIENT", default=False),
        patent_client_max_results=patent_client_max_results,
        use_live_news=use_live_news,
        news_api_max_results=news_api_max_results,
    )
