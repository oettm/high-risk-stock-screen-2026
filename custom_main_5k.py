#!/usr/bin/env python3
"""
Custom 9-stock portfolio analysis for a second user-specified basket: MSFT,
NVDA, TSM, VRT, NOW, CRWV, IREN, SAN.PA, JNJ.DE - EUR 5,000 budget,
equal-weight target, WHOLE SHARES ONLY (no fractional shares), same
constraint as the EUR 7,000 basket in custom_main.py.

CRWV (CoreWeave) and IREN (IREN Limited) are not in the curated 50-name
UNIVERSE (config.py) - both are added here as extra Instrument entries,
bucketed into an existing sector (AI / Enterprise Software for CRWV, Energy &
Digital Infrastructure for IREN) so they get a real in-universe peer group
for multiples/PEG valuation and risk-rating percentiles, instead of a
1-name "peer group" of just themselves.

SAN.PA (Sanofi) and JNJ.DE were added after a live low-beta/low-volatility
screen against a healthcare candidate shortlist, explicitly to reduce this
basket's very high average beta/volatility (the original 7 names run
0.9-4.3 beta) and its 100%-USD currency concentration - both are EUR-
denominated. JNJ.DE is the Xetra EUR cross-listing of Johnson & Johnson
(same company as NYSE: JNJ, chosen instead of the primary US listing
specifically so the position is bought/held in EUR); note Yahoo Finance
does not carry forward analyst EPS/PE estimates for this cross-listing (only
the primary US listing has them), so JNJ.DE's Method A/B price targets
correctly show "insufficient data" - a real data-coverage gap of the EUR
listing, not a bug. Both are bucketed into Consumer Goods (SECTOR_CONSUMER)
for peer-percentile purposes - the closest available in-universe peer group
of large, low-beta, dividend-paying blue chips, not a claim that pharma
literally is a consumer-goods sector.

Run: python custom_main_5k.py
Output: docs/custom-portfolio-5k.html
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from screener.config import UNIVERSE, Instrument, SECTOR_AI, SECTOR_ENERGY_INFRA, SECTOR_CONSUMER

from screener.fetch import fetch_universe, fetch_all_fx
from screener.metrics import compute_all_metrics
from screener.scoring import apply_screen, compute_composite_scores, compute_risk_ratings
from screener.valuation import build_price_targets
from screener.custom_sizing import build_integer_allocation
from screener.backtest import run_backtest
from screener.scenarios import build_scenario_analysis, SCENARIO_KEYS
from screener.report import build_pick_context, render_report
from screener import charts

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"

CUSTOM_TICKERS = ["MSFT", "NVDA", "TSM", "VRT", "NOW", "CRWV", "IREN", "SAN.PA", "JNJ.DE"]
CUSTOM_CAPITAL_EUR = 5000.0
CUSTOM_TARGET_WEIGHTS = {t: 1.0 / len(CUSTOM_TICKERS) for t in CUSTOM_TICKERS}

EXTRA_INSTRUMENTS = [
    Instrument("CRWV", "CoreWeave, Inc.", SECTOR_AI, "NASDAQ", "USD"),
    Instrument("IREN", "IREN Limited", SECTOR_ENERGY_INFRA, "NASDAQ", "USD"),
    Instrument("SAN.PA", "Sanofi SA", SECTOR_CONSUMER, "Euronext Paris", "EUR"),
    Instrument("JNJ.DE", "Johnson & Johnson (Xetra, EUR)", SECTOR_CONSUMER, "Xetra", "EUR"),
]


def main() -> None:
    run_started = dt.datetime.now(dt.timezone.utc)
    as_of_tag = run_started.strftime("%Y%m%d_%H%M")
    print(f"[{run_started.isoformat(timespec='seconds')}] Starting custom-portfolio (5k) run...")
    print(f"Tickers: {CUSTOM_TICKERS}, capital EUR {CUSTOM_CAPITAL_EUR:,.0f}, equal-weight target, whole shares only")

    full_universe = list(UNIVERSE) + EXTRA_INSTRUMENTS
    instruments = {i.ticker: i for i in full_universe}
    currencies = {i.currency for i in full_universe}

    missing = [t for t in CUSTOM_TICKERS if t not in instruments]
    if missing:
        raise SystemExit(f"Unknown ticker(s): {missing}")

    print(f"Fetching FX rates for {sorted(currencies)}...")
    fx_rates = fetch_all_fx(currencies)
    for ccy, info in fx_rates.items():
        print(f"  {ccy} -> EUR: {info['rate']} (source: {info['source']})")

    # Fetch the full 50-name universe PLUS CRWV/IREN so sector peer medians /
    # percentile-based risk ratings rest on a real population, not a 1-name
    # "peer group" of just themselves - same pattern as custom_main.py.
    print(f"Fetching data for {len(full_universe)} tickers (peer benchmarking population)...")
    raw = fetch_universe(full_universe)
    all_metrics = {t: compute_all_metrics(r) for t, r in raw.items()}

    passed, rejected = apply_screen(all_metrics, instruments, fx_rates)
    print(f"  {len(passed)} passed screen (used as peer/risk population)")

    for t in CUSTOM_TICKERS:
        if t not in passed:
            print(f"  WARNING: {t} did not pass the standard screen ({rejected.get(t)}) - using raw metrics anyway")
            passed[t] = all_metrics[t]

    scores = compute_composite_scores(passed, instruments)
    risk_ratings = compute_risk_ratings(passed)

    print(f"Computing price targets (multiples + PEG) for the {len(CUSTOM_TICKERS)} custom names...")
    price_targets = {
        t: build_price_targets(passed[t], scores[t]["peer_forward_pe_sector"], scores[t]["peer_peg_sector"])
        for t in CUSTOM_TICKERS
    }

    print("Building integer-share allocation (equal-weight target, whole shares only)...")
    allocation = build_integer_allocation(
        CUSTOM_TICKERS, passed, fx_rates, instruments, CUSTOM_CAPITAL_EUR, CUSTOM_TARGET_WEIGHTS
    )
    for r in allocation["rows"]:
        print(f"  {r['ticker']}: {r['shares']} shares @ {r['price_native']:.2f} {r['currency']} = EUR {r['eur_amount']:.2f} ({r['weight_pct']:.1f}%)")
    print(f"  Leftover cash: EUR {allocation['leftover_cash_eur']:.2f}")

    print("Running historical backtest (3y, FX-adjusted, using realized integer-share weights)...")
    backtest = run_backtest(CUSTOM_TICKERS, allocation, instruments)

    print("Building 5-scenario forward-looking analysis...")
    scenario_analysis = build_scenario_analysis(
        CUSTOM_TICKERS, passed, price_targets, instruments, fx_rates, allocation
    )

    DATA_DIR.mkdir(exist_ok=True)
    dump = {
        "tickers": CUSTOM_TICKERS, "capital_eur": CUSTOM_CAPITAL_EUR,
        "allocation": allocation, "backtest": backtest, "scenario_analysis": scenario_analysis,
    }
    dump_path = DATA_DIR / f"custom_portfolio_5k_{as_of_tag}.json"
    dump_path.write_text(json.dumps(dump, indent=2, default=str), encoding="utf-8")
    print(f"Data snapshot saved to {dump_path}")

    print("Building report context...")
    picks_context = []
    for t in CUSTOM_TICKERS:
        picks_context.append(
            build_pick_context(
                t, passed[t], raw[t].history, price_targets[t], scores[t], risk_ratings[t],
                instruments, passed, fx_rates,
            )
        )

    composite_chart = charts.composite_score_chart(
        [p["ticker"] for p in picks_context], [p["composite_score"] for p in picks_context]
    )
    allocation_pie = charts.allocation_pie_chart(allocation["sector_totals_pct"])
    allocation_bar = charts.custom_allocation_bar_chart(allocation["rows"])

    backtest_chart_html = None
    if "error" not in backtest:
        backtest_chart_html = charts.backtest_chart(backtest["dates"], backtest["portfolio_values"], backtest["benchmarks"])

    scenario_chart_html = charts.scenario_chart(
        SCENARIO_KEYS,
        [scenario_analysis["meta"][k]["label"] for k in SCENARIO_KEYS],
        [scenario_analysis["portfolio"][k]["ending_value_eur"] for k in SCENARIO_KEYS],
        allocation["investable_eur"],
    )

    context = {
        "generated_at": run_started.strftime("%Y-%m-%d %H:%M UTC"),
        "capital_eur": CUSTOM_CAPITAL_EUR,
        "fx_rates": fx_rates,
        "picks": picks_context,
        "n_selected": len(CUSTOM_TICKERS),
        "composite_chart": composite_chart,
        "allocation": allocation,
        "allocation_pie": allocation_pie,
        "allocation_bar": allocation_bar,
        "backtest": backtest,
        "backtest_chart": backtest_chart_html,
        "scenario_analysis": scenario_analysis,
        "scenario_keys": SCENARIO_KEYS,
        "scenario_chart": scenario_chart_html,
        "sibling_report_link": "custom-portfolio.html",
        "sibling_report_label": "Custom portfolio (EUR 7,000)",
    }

    out_path = DOCS_DIR / "custom-portfolio-5k.html"
    render_report(context, out_path, template_name="custom_portfolio_template.html")
    print(f"Report written to {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
