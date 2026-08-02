#!/usr/bin/env python3
"""
Reproducible high-risk stock screener for a EUR 4,600 / 3-year / very-high-risk
profile across Semiconductors, Energy & Digital Infrastructure, AI, Defence,
and Consumer Goods.

Run: python main.py
Outputs:
  - data/universe_snapshot_<asof>.csv   (full ~50-name raw pull, for audit)
  - data/selected_10_<asof>.json        (final picks + all computed metrics)
  - docs/index.html                      (the shareable report)

All data is fetched live at run time from Yahoo Finance (yfinance) and, for
FX, a Frankfurter/ECB fallback. Nothing is hardcoded from memory - re-run this
script at any time to refresh every number with a new as-of date.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import pandas as pd

from screener.config import UNIVERSE, CAPITAL_EUR
from screener.fetch import fetch_universe, fetch_all_fx
from screener.metrics import compute_all_metrics
from screener.scoring import apply_screen, compute_composite_scores, compute_risk_ratings, select_top_n, eur_value
from screener.valuation import build_price_targets
from screener.sizing import build_allocation
from screener.backtest import run_backtest
from screener.scenarios import build_scenario_analysis, SCENARIO_KEYS
from screener.report import build_pick_context, render_report
from screener import charts

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
DOCS_DIR = ROOT / "docs"


def main() -> None:
    run_started = dt.datetime.now(dt.timezone.utc)
    as_of_tag = run_started.strftime("%Y%m%d_%H%M")
    print(f"[{run_started.isoformat(timespec='seconds')}] Starting screener run...")

    instruments = {i.ticker: i for i in UNIVERSE}
    currencies = {i.currency for i in UNIVERSE}

    print(f"Fetching FX rates for {sorted(currencies)}...")
    fx_rates = fetch_all_fx(currencies)
    for ccy, info in fx_rates.items():
        print(f"  {ccy} -> EUR: {info['rate']} (source: {info['source']}, as of {info['as_of']})")

    print(f"Fetching data for {len(UNIVERSE)} universe tickers (this can take a few minutes)...")
    raw = fetch_universe(UNIVERSE)

    all_metrics = {t: compute_all_metrics(r) for t, r in raw.items()}

    # --- universe snapshot for audit/reproducibility ---
    DATA_DIR.mkdir(exist_ok=True)
    snapshot_rows = []
    for t, m in all_metrics.items():
        inst = instruments[t]
        snapshot_rows.append({
            "ticker": t, "name": m["long_name"], "sector": inst.sector,
            "exchange": inst.exchange, "currency": inst.currency,
            "price_native": m["price_native"],
            "market_cap_native": m["market_cap_native"],
            "trailing_pe": m["trailing_pe"], "forward_pe": m["forward_pe"],
            "revenue_cagr_5y": m["revenue"]["cagr"],
            "debt_to_equity": m["leverage"]["debt_to_equity"],
            "net_debt_to_ebitda": m["leverage"]["net_debt_to_ebitda"],
            "dividend_yield_pct": m["dividend"]["dividend_yield_pct"],
            "beta": m["beta_vol"]["beta"],
            "as_of": m["as_of"], "data_error": m["data_error"],
        })
    snapshot_path = DATA_DIR / f"universe_snapshot_{as_of_tag}.csv"
    pd.DataFrame(snapshot_rows).to_csv(snapshot_path, index=False)
    print(f"Universe snapshot saved to {snapshot_path}")

    print("Applying screening filters...")
    passed, rejected = apply_screen(all_metrics, instruments, fx_rates)
    print(f"  {len(passed)} passed, {len(rejected)} rejected")

    print("Computing composite scores and risk ratings...")
    scores = compute_composite_scores(passed, instruments)
    risk_ratings = compute_risk_ratings(passed)

    print("Selecting top 10 (sector-diversified)...")
    selected = select_top_n(scores, instruments)
    print(f"  Selected: {selected}")

    print("Computing price targets (multiples + simplified DCF) for selected names...")
    price_targets = {
        t: build_price_targets(raw[t], passed[t], scores[t]["peer_forward_pe_sector"])
        for t in selected
    }

    print("Building EUR 4,600 position sizing...")
    allocation = build_allocation(selected, passed, scores, fx_rates, instruments)

    print("Running historical backtest of the proposed portfolio...")
    backtest = run_backtest(selected, allocation, instruments)

    print("Building 5-scenario forward-looking analysis...")
    scenario_analysis = build_scenario_analysis(
        selected, raw, passed, price_targets, instruments, fx_rates, allocation
    )

    # --- selected picks snapshot for audit/reproducibility ---
    selected_dump = {
        "picks": {
            t: {
                "metrics": {k: v for k, v in passed[t].items() if k != "data_error"},
                "score": scores[t],
                "risk": risk_ratings[t],
                "price_targets": price_targets[t],
            }
            for t in selected
        },
        "allocation": allocation,
        "backtest": backtest,
        "scenario_analysis": scenario_analysis,
    }
    selected_path = DATA_DIR / f"selected_10_{as_of_tag}.json"
    selected_path.write_text(json.dumps(selected_dump, indent=2, default=str), encoding="utf-8")
    print(f"Selected picks snapshot saved to {selected_path}")

    print("Building report context...")
    picks_context = []
    for t in selected:
        picks_context.append(
            build_pick_context(
                t, passed[t], raw[t].history, price_targets[t], scores[t], risk_ratings[t],
                instruments, passed, fx_rates,
            )
        )

    universe_table = []
    for t, m in all_metrics.items():
        inst = instruments[t]
        universe_table.append({
            "ticker": t, "name": m["long_name"], "sector": inst.sector,
            "exchange": inst.exchange, "currency": inst.currency,
            "market_cap_eur": eur_value(m["market_cap_native"], inst.currency, fx_rates),
            "status": "SELECTED" if t in selected else ("SCREENED-IN (not selected)" if t in passed else "REJECTED"),
            "reasons": rejected.get(t, []),
        })
    universe_table.sort(key=lambda r: (r["sector"], r["ticker"]))

    composite_chart = charts.composite_score_chart(
        [p["ticker"] for p in picks_context], [p["composite_score"] for p in picks_context]
    )
    allocation_pie = charts.allocation_pie_chart(allocation["sector_totals_pct"])
    allocation_bar = charts.allocation_bar_chart(allocation["rows"])

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
        "capital_eur": CAPITAL_EUR,
        "fx_rates": fx_rates,
        "universe_table": universe_table,
        "n_universe": len(UNIVERSE),
        "n_passed": len(passed),
        "n_selected": len(selected),
        "picks": picks_context,
        "composite_chart": composite_chart,
        "allocation": allocation,
        "allocation_pie": allocation_pie,
        "allocation_bar": allocation_bar,
        "backtest": backtest,
        "backtest_chart": backtest_chart_html,
        "scenario_analysis": scenario_analysis,
        "scenario_keys": SCENARIO_KEYS,
        "scenario_chart": scenario_chart_html,
    }

    out_path = DOCS_DIR / "index.html"
    render_report(context, out_path)
    print(f"Report written to {out_path}")
    print("Done.")


if __name__ == "__main__":
    main()
