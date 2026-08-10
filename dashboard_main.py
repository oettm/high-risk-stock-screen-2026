#!/usr/bin/env python3
"""
Weekly Bloomberg-style dashboard for the user's ACTUAL holdings (real share
counts, not a target-weight construction): SAN.PA 14, NVDA 4, VRT 4,
ASML.AS 1, CRWV 10, NOW 6.

Unlike the other three reports, this one is meant to be re-run regularly -
see .github/workflows/weekly-dashboard.yml, which runs it every Monday and
commits the refreshed docs/dashboard.html plus data/dashboard_history.json
(week-over-week deltas need that history file to persist between runs).

Run: python dashboard_main.py
Output: docs/dashboard.html (+ updates data/dashboard_history.json)

--- EDIT THESE when your actual holdings change ---
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from screener.config import UNIVERSE, Instrument, SECTOR_AI, SECTOR_CONSUMER
from screener.fetch import fetch_universe, fetch_all_fx
from screener.metrics import compute_all_metrics
from screener.scoring import apply_screen, compute_composite_scores, compute_risk_ratings
from screener.valuation import build_price_targets
from screener.backtest import run_backtest
from screener.scenarios import build_scenario_analysis, SCENARIO_KEYS
from screener.news_sentiment import fetch_all_news
from screener.dashboard import build_dashboard_context
from screener.report import render_report

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"
HISTORY_PATH = DATA_DIR / "dashboard_history.json"

# Real share counts actually held - edit this when you buy/sell.
HOLDINGS = {"SAN.PA": 14, "NVDA": 4, "VRT": 4, "ASML.AS": 1, "CRWV": 10, "NOW": 6}

# Disclosed commission assumptions (user-stated: ~20-22 EUR/US trade, ~1 EUR/EU trade).
COMMISSIONS = {"us_trade_eur": 21.0, "eu_trade_eur": 1.0}

# Real EUR cost basis per position - what was actually paid, EXCLUDING commissions
# (commissions are tracked separately above). Set to None until known: the dashboard
# will render "N/A" for that position's P&L rather than guess. Fill these in with your
# real purchase amounts (e.g. from your broker's transaction history) to get real P&L.
COST_BASIS_EUR = {"SAN.PA": None, "NVDA": None, "VRT": None, "ASML.AS": None, "CRWV": None, "NOW": None}

# CRWV isn't in the curated 50-name UNIVERSE (config.py) - added here as an extra
# Instrument bucketed into AI/Enterprise Software purely for peer-percentile
# benchmarking, same pattern as custom_main_5k.py. ASML.AS/NVDA/VRT/NOW are
# already in UNIVERSE; SAN.PA needs the same extra-Instrument treatment.
EXTRA_INSTRUMENTS = [
    Instrument("CRWV", "CoreWeave, Inc.", SECTOR_AI, "NASDAQ", "USD"),
    Instrument("SAN.PA", "Sanofi SA", SECTOR_CONSUMER, "Euronext Paris", "EUR"),
]


def main() -> None:
    run_started = dt.datetime.now(dt.timezone.utc)
    print(f"[{run_started.isoformat(timespec='seconds')}] Starting dashboard run...")
    print(f"Holdings: {HOLDINGS}")

    full_universe = list(UNIVERSE) + EXTRA_INSTRUMENTS
    instruments = {i.ticker: i for i in full_universe}
    currencies = {i.currency for i in full_universe}

    missing = [t for t in HOLDINGS if t not in instruments]
    if missing:
        raise SystemExit(f"Unknown ticker(s): {missing}")

    print(f"Fetching FX rates for {sorted(currencies)}...")
    fx_rates = fetch_all_fx(currencies)
    for ccy, info in fx_rates.items():
        print(f"  {ccy} -> EUR: {info['rate']} (source: {info['source']})")

    print(f"Fetching data for {len(full_universe)} tickers (peer benchmarking population)...")
    raw = fetch_universe(full_universe)
    all_metrics = {t: compute_all_metrics(r) for t, r in raw.items()}

    passed, rejected = apply_screen(all_metrics, instruments, fx_rates)
    for t in HOLDINGS:
        if t not in passed:
            print(f"  WARNING: {t} did not pass the standard screen ({rejected.get(t)}) - using raw metrics anyway")
            passed[t] = all_metrics[t]

    scores = compute_composite_scores(passed, instruments)
    risk_ratings = compute_risk_ratings(passed)

    print("Computing price targets for the 6 held names...")
    price_targets = {
        t: build_price_targets(passed[t], scores[t]["peer_forward_pe_sector"], scores[t]["peer_peg_sector"])
        for t in HOLDINGS
    }

    # Backtest/scenarios reuse the shared pipeline, which expects an
    # "allocation" dict shaped like {"rows": [...], "investable_eur": x} -
    # build it directly from real holdings x current price instead of
    # running the target-weight allocator.
    rows_for_alloc = []
    total_eur = 0.0
    for t, shares in HOLDINGS.items():
        inst = instruments[t]
        rate = fx_rates[inst.currency]["rate"]
        price_native = passed[t]["price_native"]
        eur_amount = shares * price_native * rate
        total_eur += eur_amount
        rows_for_alloc.append({"ticker": t, "shares": shares, "price_native": price_native,
                                "currency": inst.currency, "eur_amount": eur_amount})
    for r in rows_for_alloc:
        r["weight_pct"] = r["eur_amount"] / total_eur * 100
    allocation = {"rows": rows_for_alloc, "investable_eur": total_eur, "leftover_cash_eur": 0.0}

    print("Running historical backtest (3y, FX-adjusted, current real weights)...")
    backtest = run_backtest(list(HOLDINGS.keys()), allocation, instruments)

    print("Building 5-scenario forward-looking analysis...")
    scenario_analysis = build_scenario_analysis(
        list(HOLDINGS.keys()), passed, price_targets, instruments, fx_rates, allocation
    )

    print("Fetching news + sentiment for the 6 held names (Yahoo Finance, finance-tuned VADER)...")
    news = fetch_all_news(list(HOLDINGS.keys()), run_started, max_items_per_ticker=6)
    print(f"  {len(news)} news items fetched")

    print("Building dashboard context (incl. week-over-week vs data/dashboard_history.json)...")
    context = build_dashboard_context(
        HOLDINGS, instruments, raw, passed, price_targets, risk_ratings, fx_rates,
        COMMISSIONS, COST_BASIS_EUR, news, backtest, scenario_analysis, SCENARIO_KEYS,
        HISTORY_PATH, run_started,
    )

    out_path = DOCS_DIR / "dashboard.html"
    render_report(context, out_path, template_name="dashboard_template.html")
    print(f"Dashboard written to {out_path}")
    print(f"Total value: EUR {context['total_value_eur']:.2f}  |  P&L coverage: {context['pnl_coverage']}")
    print("Done.")


if __name__ == "__main__":
    main()
