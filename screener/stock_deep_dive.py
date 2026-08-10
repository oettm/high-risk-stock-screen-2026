"""
Builds the Jinja2 context for a single-stock deep-dive report (light theme,
same Fact/Estimate/Opinion convention as the other 3 reports).

Unlike the portfolio reports, valuation here is benchmarked against a
DEDICATED peer group supplied by the driver script, not the 50-name curated
universe or an ad-hoc sector bucket. That matters: in the portfolio reports,
Sanofi was bucketed into "Consumer Goods" purely so it had *some* peer group
for percentile valuation, which visibly inflated its bull-case target (P&G/
Coca-Cola-style multiples applied to a pharma stock). A dedicated deep dive
should use real sector peers - see sanofi_deep_dive.py's PEER_TICKERS.
"""

from __future__ import annotations

import datetime as dt

import yfinance as yf

from screener.config import Instrument
from screener.fetch import fetch_stock, fetch_all_fx
from screener.metrics import compute_all_metrics, forward_eps_growth
from screener.valuation import build_price_targets
from screener import charts


def fetch_peer_valuation_sample(peer_tickers: list[str]) -> dict:
    """Live forward P/E and PEG (forward P/E / forward EPS growth%) for a
    hand-picked peer group. PEG only included when growth is positive - a
    negative-growth peer would produce a nonsensical negative PEG."""
    rows = []
    forward_pes = []
    pegs = []
    for p in peer_tickers:
        try:
            info = yf.Ticker(p).info
        except Exception:  # noqa: BLE001
            continue
        fpe = info.get("forwardPE")
        fwd_eps = info.get("forwardEps")
        trail_eps = info.get("trailingEps")
        growth = (fwd_eps / trail_eps - 1) if (fwd_eps and trail_eps and trail_eps > 0) else None
        peg = None
        if fpe and fpe > 0:
            forward_pes.append(fpe)
        if fpe and growth and growth > 0:
            peg = fpe / (growth * 100)
            pegs.append(peg)
        rows.append({
            "ticker": p, "name": info.get("longName") or p, "forward_pe": fpe,
            "growth": growth, "peg": peg, "currency": info.get("currency"),
        })
    return {"rows": rows, "forward_pes": forward_pes, "pegs": pegs}


def build_financial_solidity(info: dict) -> dict:
    return {
        "total_revenue": info.get("totalRevenue"),
        "revenue_growth_pct": info.get("revenueGrowth"),
        "gross_margin_pct": info.get("grossMargins"),
        "operating_margin_pct": info.get("operatingMargins"),
        "profit_margin_pct": info.get("profitMargins"),
        "ebitda_margin_pct": info.get("ebitdaMargins"),
        "return_on_equity_pct": info.get("returnOnEquity"),
        "total_debt": info.get("totalDebt"),
        "total_cash": info.get("totalCash"),
        "debt_to_equity": (info.get("debtToEquity") / 100.0) if info.get("debtToEquity") else None,
        "current_ratio": info.get("currentRatio"),
        "quick_ratio": info.get("quickRatio"),
        "free_cashflow": info.get("freeCashflow"),
        "operating_cashflow": info.get("operatingCashflow"),
        "enterprise_to_ebitda": info.get("enterpriseToEbitda"),
        "price_to_book": info.get("priceToBook"),
        "dividend_yield_pct": info.get("dividendYield"),
        "payout_ratio_pct": info.get("payoutRatio"),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
    }


def build_analyst_consensus(info: dict) -> dict:
    return {
        "target_mean": info.get("targetMeanPrice"),
        "target_median": info.get("targetMedianPrice"),
        "target_high": info.get("targetHighPrice"),
        "target_low": info.get("targetLowPrice"),
        "n_analysts": info.get("numberOfAnalystOpinions"),
        "recommendation": info.get("recommendationKey"),
        "recommendation_mean": info.get("recommendationMean"),
    }


def build_deep_dive_context(
    instrument: Instrument,
    peer_tickers: list[str],
    decline_events: list[dict],
    pipeline_projects: list[dict],
    business_profile: dict,
    moat: dict,
    generated_at: dt.datetime,
) -> dict:
    raw = fetch_stock(instrument)
    metrics = compute_all_metrics(raw)
    fx_rates = fetch_all_fx({instrument.currency})

    peer_sample = fetch_peer_valuation_sample(peer_tickers)
    price_targets = build_price_targets(metrics, peer_sample["forward_pes"], peer_sample["pegs"])
    fwd_growth = forward_eps_growth(metrics)

    financials = build_financial_solidity(raw.info)
    analyst = build_analyst_consensus(raw.info)

    scale = 100.0 if instrument.pence_quoted else 1.0
    h5y = yf.Ticker(instrument.ticker).history(period="5y", auto_adjust=False)
    dates_5y, closes_5y = [], []
    if h5y is not None and not h5y.empty:
        dates_5y = [d.strftime("%Y-%m-%d") for d in h5y.index]
        closes_5y = (h5y["Close"] / scale).tolist()

    price_by_date = dict(zip(dates_5y, closes_5y)) if dates_5y else {}
    for ev in decline_events:
        ev["y"] = price_by_date.get(ev["date"], metrics["price_native"])

    decline_chart = charts.decline_annotated_chart(instrument.ticker, dates_5y, closes_5y, instrument.currency, decline_events)
    peer_chart = charts.peer_valuation_bar_chart(
        [r["ticker"] for r in peer_sample["rows"] if r["forward_pe"]],
        [r["forward_pe"] for r in peer_sample["rows"] if r["forward_pe"]],
        metrics["price_native"], price_targets["multiples"].get("bull_price"),
        price_targets["multiples"].get("bear_price"), instrument.currency,
    )

    return {
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "ticker": instrument.ticker, "name": metrics["long_name"], "sector": instrument.sector,
        "exchange": instrument.exchange, "currency": instrument.currency,
        "as_of": metrics["as_of"],
        "price_native": metrics["price_native"], "day_change_pct": metrics.get("day_change_pct"),
        "beta": metrics["beta_vol"].get("beta"), "vol_1y": metrics["beta_vol"].get("annualized_volatility_1y"),
        "trailing_pe": metrics["trailing_pe"], "forward_pe": metrics["forward_pe"],
        "forward_eps": metrics["forward_eps"], "trailing_eps": metrics["trailing_eps"],
        "forward_growth": fwd_growth,
        "financials": financials,
        "revenue_history": metrics["revenue"],
        "revenue_chart": charts.revenue_growth_chart(instrument.ticker, metrics["revenue"]["years"], metrics["revenue"]["revenues"], instrument.currency),
        "analyst": analyst,
        "price_targets": price_targets,
        "peer_sample": peer_sample,
        "peer_chart": peer_chart,
        "decline_chart": decline_chart,
        "decline_events": decline_events,
        "pipeline_projects": pipeline_projects,
        "business": business_profile,
        "moat": moat,
        "data_error": raw.error,
    }
