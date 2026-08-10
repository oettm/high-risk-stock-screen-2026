"""
Builds the Jinja2 context for the Bloomberg-style holdings dashboard
(docs/dashboard.html), unlike the other three reports, this one is built
from the user's ACTUAL share counts (real holdings), not a target-weight
construction, and is meant to be regenerated weekly (see
.github/workflows/weekly-dashboard.yml) so the numbers stay current.

Two things live here that don't exist in the other reports:
  - a small local history file (data/dashboard_history.json) so week-over-
    week price/weight deltas AND a real (not hindsight-backtest) portfolio-
    value-over-time chart can be shown, growing one point per weekly run;
  - real P&L: the user's actual EUR cost basis per position (what they
    stated they paid, excluding commissions), so gain/loss is computed
    against real money in, not just today's mark-to-market. Any position
    without a supplied cost basis renders "N/A" rather than a guessed number.
"""

from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

from screener.config import Instrument

HISTORY_MAX_ENTRIES = 26  # ~6 months of weekly snapshots


def load_history(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []


def append_history(path: Path, snapshot: dict, max_entries: int = HISTORY_MAX_ENTRIES) -> list[dict]:
    history = load_history(path)
    history.append(snapshot)
    history = history[-max_entries:]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(history, indent=2), encoding="utf-8")
    return history


def week_over_week(current_rows: list[dict], current_total_eur: float, previous: dict | None) -> dict:
    if previous is None:
        return {"available": False, "as_of": None, "total_change_pct": None, "per_ticker": {}}
    prev_positions = previous.get("positions", {})
    prev_total = previous.get("total_value_eur")
    per_ticker = {}
    for r in current_rows:
        t = r["ticker"]
        prev = prev_positions.get(t)
        price_change_pct = None
        weight_change_pp = None
        if prev and prev.get("price_eur") and r.get("price_eur"):
            price_change_pct = r["price_eur"] / prev["price_eur"] - 1
        if prev and prev.get("weight_pct") is not None:
            weight_change_pp = r["weight_pct"] - prev["weight_pct"]
        per_ticker[t] = {"price_change_pct": price_change_pct, "weight_change_pp": weight_change_pp}
    total_change_pct = (current_total_eur / prev_total - 1) if prev_total else None
    return {"available": True, "as_of": previous.get("date"), "total_change_pct": total_change_pct, "per_ticker": per_ticker}


def build_dashboard_context(
    holdings: dict[str, int],
    instruments: dict[str, Instrument],
    raw_by_ticker: dict,
    passed_metrics: dict,
    price_targets: dict,
    risk_ratings: dict,
    fx_rates: dict,
    commissions: dict,
    cost_basis_eur: dict[str, float | None],
    news: list[dict],
    backtest: dict,
    scenario_analysis: dict,
    scenario_keys: list[str],
    history_path: Path,
    generated_at: dt.datetime,
) -> dict:
    from screener import dashboard_charts as dc

    rows = []
    total_eur = 0.0
    for t, shares in holdings.items():
        m = passed_metrics[t]
        inst = instruments[t]
        rate = fx_rates.get(inst.currency, {}).get("rate")
        price_native = m["price_native"]
        price_eur = (price_native * rate) if (price_native and rate) else None
        eur_amount = (shares * price_eur) if price_eur else 0.0
        total_eur += eur_amount
        tech = m["technicals"]

        raw = raw_by_ticker.get(t)
        sparkline_html = "<span style='color:#6b6a63;'>n/d</span>"
        price_chart_html = "<p class='muted'>Nessuno storico prezzi disponibile.</p>"
        if raw is not None and raw.history is not None and not raw.history.empty:
            scale = 100.0 if inst.pence_quoted else 1.0
            closes_full = (raw.history["Close"] / scale)
            sparkline_html = dc.sparkline_chart(closes_full.tail(90).tolist())
            dates_full = [d.strftime("%Y-%m-%d") for d in raw.history.index]
            price_chart_html = dc.stock_price_chart_dark(
                t, dates_full, closes_full.tolist(), tech.get("ma50"),
                tech.get("entry_zone_low"), tech.get("entry_zone_high"),
                tech.get("stop_loss"), inst.currency,
            )

        cost_eur = cost_basis_eur.get(t)
        pnl_eur = (eur_amount - cost_eur) if cost_eur is not None else None
        pnl_pct = (eur_amount / cost_eur - 1) if cost_eur else None

        rows.append({
            "ticker": t, "name": m["long_name"], "shares": shares,
            "price_native": price_native, "price_eur": price_eur,
            "currency": inst.currency, "eur_amount": eur_amount,
            "day_change_pct": m.get("day_change_pct"),
            "stop_loss": tech.get("stop_loss"),
            "entry_zone_low": tech.get("entry_zone_low"), "entry_zone_high": tech.get("entry_zone_high"),
            "beta": m["beta_vol"].get("beta"), "vol_1y": m["beta_vol"].get("annualized_volatility_1y"),
            "risk_rating": risk_ratings.get(t, {}).get("rating"),
            "sparkline": sparkline_html,
            "price_chart": price_chart_html,
            "cost_basis_eur": cost_eur, "pnl_eur": pnl_eur, "pnl_pct": pnl_pct,
            "as_of": m.get("as_of"),
        })

    for r in rows:
        r["weight_pct"] = (r["eur_amount"] / total_eur * 100) if total_eur else 0.0

    n_us = sum(1 for t in holdings if instruments[t].currency != "EUR")
    n_eu = sum(1 for t in holdings if instruments[t].currency == "EUR")
    total_commissions = n_us * commissions["us_trade_eur"] + n_eu * commissions["eu_trade_eur"]

    known_cost_rows = [r for r in rows if r["cost_basis_eur"] is not None]
    total_cost_basis_eur = sum(r["cost_basis_eur"] for r in known_cost_rows) if known_cost_rows else None
    total_pnl_eur = (sum(r["eur_amount"] for r in known_cost_rows) - total_cost_basis_eur) if total_cost_basis_eur else None
    total_pnl_pct = (
        sum(r["eur_amount"] for r in known_cost_rows) / total_cost_basis_eur - 1
    ) if total_cost_basis_eur else None
    pnl_coverage = f"{len(known_cost_rows)}/{len(rows)}"

    history = load_history(history_path)
    previous = history[-1] if history else None
    wow = week_over_week(rows, total_eur, previous)

    today_snapshot = {
        "date": generated_at.strftime("%Y-%m-%d"),
        "total_value_eur": total_eur,
        "positions": {r["ticker"]: {"price_eur": r["price_eur"], "weight_pct": r["weight_pct"]} for r in rows},
    }
    full_history = append_history(history_path, today_snapshot)

    def _wavg(key):
        vals = [(r[key], r["weight_pct"]) for r in rows if r.get(key) is not None]
        wsum = sum(w for _, w in vals)
        return (sum(v * w for v, w in vals) / wsum) if wsum else None

    portfolio_beta = _wavg("beta")
    portfolio_vol = _wavg("vol_1y")
    portfolio_risk_rating = _wavg("risk_rating")

    eur_weight = sum(r["weight_pct"] for r in rows if r["currency"] == "EUR")
    usd_weight = 100.0 - eur_weight

    weight_donut = dc.weight_donut_dark(rows)
    risk_bar = dc.risk_bar_dark(rows)
    backtest_chart_html = None
    if "error" not in backtest:
        backtest_chart_html = dc.backtest_chart_dark(backtest["dates"], backtest["portfolio_values"], backtest["benchmarks"])
    scenario_chart_html = dc.scenario_chart_dark(
        scenario_keys,
        [scenario_analysis["meta"][k]["label"] for k in scenario_keys],
        [scenario_analysis["portfolio"][k]["ending_value_eur"] for k in scenario_keys],
        total_eur,
    )
    evolution_chart_html = dc.portfolio_evolution_chart_dark(
        [h["date"] for h in full_history], [h["total_value_eur"] for h in full_history], total_cost_basis_eur,
    )

    return {
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "rows": rows,
        "total_value_eur": total_eur,
        "total_commissions_eur": total_commissions,
        "commission_drag_pct": (total_commissions / total_eur * 100) if total_eur else None,
        "total_cost_basis_eur": total_cost_basis_eur,
        "total_pnl_eur": total_pnl_eur,
        "total_pnl_pct": total_pnl_pct,
        "pnl_coverage": pnl_coverage,
        "pnl_complete": len(known_cost_rows) == len(rows),
        "wow": wow,
        "portfolio_beta": portfolio_beta,
        "portfolio_vol": portfolio_vol,
        "portfolio_risk_rating": portfolio_risk_rating,
        "eur_weight": eur_weight,
        "usd_weight": usd_weight,
        "news": news,
        "backtest": backtest,
        "backtest_chart": backtest_chart_html,
        "scenario_analysis": scenario_analysis,
        "scenario_keys": scenario_keys,
        "scenario_chart": scenario_chart_html,
        "weight_donut": weight_donut,
        "risk_bar": risk_bar,
        "evolution_chart": evolution_chart_html,
        "history_points": len(full_history),
        "price_targets": price_targets,
    }
