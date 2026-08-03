"""Builds the Jinja2 context and renders docs/index.html."""

from __future__ import annotations

import datetime as dt
import statistics as stats
from pathlib import Path

import jinja2

from screener.config import Instrument, CAPITAL_EUR
from screener.qualitative import MOAT
from screener.business_profile import BUSINESS_PROFILE
from screener import charts

TEMPLATE_DIR = Path(__file__).parent / "templates"


def _sector_peer_pe_median(passed_metrics: dict, sector: str) -> float | None:
    vals = [
        m.get("forward_pe") or m.get("trailing_pe")
        for t, m in passed_metrics.items()
        if m["sector"] == sector and (m.get("forward_pe") or m.get("trailing_pe"))
    ]
    return round(stats.median(vals), 1) if vals else None


def build_pick_context(
    ticker: str,
    metrics: dict,
    raw_history,
    price_targets: dict,
    score: dict,
    risk: dict,
    instruments: dict[str, Instrument],
    passed_metrics: dict,
    fx_rates: dict,
) -> dict:
    inst = instruments[ticker]
    rev = metrics["revenue"]
    tech = metrics["technicals"]
    moat = MOAT.get(ticker, {"source": "N/A", "durability": "N/A", "threats": "N/A"})
    business = BUSINESS_PROFILE.get(ticker, {
        "summary": "N/A - no business profile on file for this ticker.",
        "business_units": [], "customers": "N/A", "key_risks": [],
    })

    rate = fx_rates.get(inst.currency, {}).get("rate")
    price_eur = (metrics["price_native"] * rate) if (metrics["price_native"] and rate) else None

    revenue_chart = charts.revenue_growth_chart(ticker, rev["years"], rev["revenues"], inst.currency)

    price_chart = "<p><em>No price history available.</em></p>"
    if raw_history is not None and not raw_history.empty:
        scale = 100.0 if inst.pence_quoted else 1.0
        closes = (raw_history["Close"] / scale).tolist()
        dates = [d.strftime("%Y-%m-%d") for d in raw_history.index]
        price_chart = charts.price_history_chart(
            ticker, dates, closes, tech.get("ma50"),
            tech.get("entry_zone_low"), tech.get("entry_zone_high"),
            tech.get("stop_loss"), inst.currency,
        )

    peer_median_pe = _sector_peer_pe_median(passed_metrics, inst.sector)

    return {
        "ticker": ticker,
        "name": metrics["long_name"],
        "sector": inst.sector,
        "exchange": inst.exchange,
        "currency": inst.currency,
        "as_of": metrics["as_of"],
        "price_native": metrics["price_native"],
        "price_eur": price_eur,
        "trailing_pe": metrics["trailing_pe"],
        "forward_pe": metrics["forward_pe"],
        "sector_peer_median_pe": peer_median_pe,
        "revenue": rev,
        "revenue_chart": revenue_chart,
        "leverage": metrics["leverage"],
        "dividend": metrics["dividend"],
        "moat": moat,
        "business": business,
        "price_targets": price_targets,
        "risk": risk,
        "technicals": tech,
        "price_chart": price_chart,
        "composite_score": score["composite"],
        "score_components": score["components"],
        "beta_vol": metrics["beta_vol"],
        "data_error": metrics.get("data_error"),
    }


def render_report(context: dict, out_path: Path) -> None:
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(str(TEMPLATE_DIR)),
        autoescape=jinja2.select_autoescape(["html"]),
    )
    template = env.get_template("report_template.html")
    html = template.render(**context)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html, encoding="utf-8")
