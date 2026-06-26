"""Keyword extraction from text collections."""

from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer

from sda_studio.processing.cleaning import normalize_text


STOPWORDS = {
    "the", "and", "for", "with", "this", "that", "from", "have", "been",
    "are", "was", "were", "but", "not", "you", "all", "can", "had", "her",
    "his", "one", "our", "out", "they", "what", "when", "will", "your",
    "about", "into", "than", "them", "then", "there", "these", "would",
    "also", "just", "like", "very", "much", "more", "some", "only", "over",
}


def extract_top_keywords(texts: list[str], top_n: int = 10) -> list[str]:
    if not texts:
        return []
    cleaned = [normalize_text(t) for t in texts if t and normalize_text(t)]
    if not cleaned:
        return []
    if len(cleaned) == 1:
        words = [w for w in cleaned[0].split() if w not in STOPWORDS and len(w) > 3]
        return [w for w, _ in Counter(words).most_common(top_n)]

    vectorizer = TfidfVectorizer(
        max_features=50,
        stop_words="english",
        ngram_range=(1, 2),
    )
    try:
        matrix = vectorizer.fit_transform(cleaned)
        scores = matrix.sum(axis=0).A1
        terms = vectorizer.get_feature_names_out()
        ranked = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)
        return [t for t, _ in ranked[:top_n]]
    except ValueError:
        return []
