"""
Per-ticker news headlines (Yahoo Finance via yfinance, no API key) with a
lightweight sentiment classification.

VADER's out-of-the-box lexicon is tuned for social-media text and returns
"neutral" (compound ~0.0) on almost every financial headline - "NVIDIA beats
earnings estimates" or "Sanofi stock plunges" both score 0.0 unmodified,
because "beats"/"plunges" aren't in its base word list. FINANCE_LEXICON
below is a small, hand-curated set of ~70 finance-specific terms layered on
top of VADER's rule engine (so its negation/intensifier handling - "not
bad", "sharply higher" - still applies) so headlines actually get classified
instead of defaulting to neutral. This is a disclosed heuristic on
headline+summary text, not a trained model or an editorial judgment -
labeled Estimate throughout the dashboard, never Fact.
"""

from __future__ import annotations

import datetime as dt

import yfinance as yf
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

FINANCE_LEXICON: dict[str, float] = {
    "beats": 2.0, "beat": 2.0, "beating": 2.0, "misses": -2.0, "miss": -2.0, "missed": -2.0,
    "upgrade": 2.2, "upgraded": 2.2, "upgrades": 2.2, "downgrade": -2.2, "downgraded": -2.2, "downgrades": -2.2,
    "surge": 2.3, "surges": 2.3, "surged": 2.3, "soar": 2.3, "soars": 2.3, "soared": 2.3,
    "rally": 1.8, "rallies": 1.8, "rallied": 1.8,
    "plunge": -2.5, "plunges": -2.5, "plunged": -2.5, "tumble": -2.2, "tumbles": -2.2, "tumbled": -2.2,
    "slump": -2.0, "slumps": -2.0, "slides": -1.8, "slid": -1.8, "sinks": -2.0, "sank": -2.0,
    "raises": 1.5, "raised": 1.5, "cuts": -1.8, "cut": -1.5, "slashes": -2.2, "slashed": -2.2,
    "record": 1.6, "blockbuster": 2.3, "breakthrough": 2.2, "outperform": 1.8, "underperform": -1.8,
    "bullish": 2.0, "bearish": -2.0, "optimistic": 1.6, "pessimistic": -1.6,
    "layoffs": -2.2, "layoff": -2.2, "bankruptcy": -3.0, "default": -2.3, "recall": -1.9,
    "lawsuit": -1.9, "fraud": -3.0, "investigation": -1.8, "probe": -1.7, "scandal": -2.6,
    "impairment": -1.8, "write-off": -1.8, "writedown": -1.8, "warning": -1.6, "profit warning": -2.3,
    "approval": 1.8, "approved": 1.8, "rejection": -1.9, "rejected": -1.9, "delay": -1.4, "delayed": -1.4,
    "discontinue": -1.7, "discontinued": -1.7, "halt": -1.6, "halted": -1.6, "suspends": -1.7, "suspended": -1.7,
    "acquisition": 1.0, "acquires": 1.0, "merger": 0.8, "partnership": 1.2, "deal": 0.8,
    "expands": 1.2, "expansion": 1.2, "growth": 1.4, "declines": -1.5, "decline": -1.5, "shrinks": -1.6,
    "guidance cut": -2.3, "guidance raise": 2.0, "raises guidance": 2.0, "cuts guidance": -2.2,
    "in line": 0.3, "as expected": 0.2, "unexpected": -0.5,
}

POSITIVE_THRESHOLD = 0.05  # VADER's own documented default thresholds
NEGATIVE_THRESHOLD = -0.05

_analyzer = SentimentIntensityAnalyzer()
_analyzer.lexicon.update(FINANCE_LEXICON)

SENTIMENT_LABELS_IT = {"positive": "Positivo", "negative": "Negativo", "neutral": "Neutro"}


def classify_sentiment(text: str) -> dict:
    score = _analyzer.polarity_scores(text or "")["compound"]
    if score >= POSITIVE_THRESHOLD:
        label = "positive"
    elif score <= NEGATIVE_THRESHOLD:
        label = "negative"
    else:
        label = "neutral"
    return {"score": score, "label": label}


def _days_ago_display(pub_date_iso: str | None, now: dt.datetime) -> str:
    if not pub_date_iso:
        return "data n/d"
    try:
        pub = dt.datetime.fromisoformat(pub_date_iso.replace("Z", "+00:00"))
    except ValueError:
        return "data n/d"
    delta_hours = (now - pub).total_seconds() / 3600
    if delta_hours < 1:
        return "meno di un'ora fa"
    if delta_hours < 24:
        return f"{int(delta_hours)}h fa"
    days = int(delta_hours // 24)
    return f"{days}g fa" if days < 30 else pub.strftime("%Y-%m-%d")


def fetch_ticker_news(ticker: str, now: dt.datetime, max_items: int = 6) -> list[dict]:
    try:
        raw_news = yf.Ticker(ticker).news or []
    except Exception:  # noqa: BLE001
        return []

    items = []
    for n in raw_news[:max_items]:
        c = n.get("content", {})
        title = c.get("title")
        if not title:
            continue
        summary = c.get("summary") or ""
        sentiment = classify_sentiment(f"{title}. {summary}")
        pub_date = c.get("pubDate")
        url = (c.get("canonicalUrl") or {}).get("url") or (c.get("clickThroughUrl") or {}).get("url")
        publisher = (c.get("provider") or {}).get("displayName") or "N/A"
        items.append({
            "ticker": ticker, "title": title, "summary": summary,
            "publisher": publisher, "url": url, "pub_date": pub_date,
            "pub_date_display": _days_ago_display(pub_date, now),
            "sentiment_label": sentiment["label"], "sentiment_score": sentiment["score"],
            "sentiment_label_it": SENTIMENT_LABELS_IT[sentiment["label"]],
        })
    return items


def fetch_all_news(tickers: list[str], now: dt.datetime, max_items_per_ticker: int = 6) -> list[dict]:
    all_items = []
    for t in tickers:
        all_items.extend(fetch_ticker_news(t, now, max_items_per_ticker))
    all_items.sort(key=lambda x: x["pub_date"] or "", reverse=True)
    return all_items
