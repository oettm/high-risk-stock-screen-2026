"""
Builds the Jinja2 context for the Bloomberg-style holdings dashboard
(docs/dashboard.html), unlike the other three reports, this one is built
from the user's ACTUAL share counts (real holdings), not a target-weight
construction, and is meant to be regenerated weekly (see
.github/workflows/weekly-dashboard.yml) so the numbers stay current.

Two things live here that don't exist in the other reports:
  - a small local history file (data/dashboard_history.json) so week-over-
    week price/weight deltas can be shown instead of only a point-in-time
    snapshot;
  - a rule-based "curation suggestions" engine: every suggestion is derived
    from a disclosed, fixed threshold on live data (concentration, risk
    rating, stop-loss breach, entry-zone proximity, price vs bull/bear
    target, currency split, minimum-efficient-trade-size given the user's
    real commission costs) - not a model opinion generated fresh each run.
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


def curation_suggestions(
    rows: list[dict],
    price_targets: dict,
    instruments: dict[str, Instrument],
    us_trade_fee_eur: float,
    eu_trade_fee_eur: float,
) -> list[dict]:
    suggestions: list[dict] = []

    def add(severity: str, title: str, detail: str) -> None:
        suggestions.append({"severity": severity, "title": title, "detail": detail})

    eur_weight = sum(r["weight_pct"] for r in rows if r["currency"] == "EUR")
    usd_weight = 100.0 - eur_weight

    for r in rows:
        t = r["ticker"]
        pt = price_targets.get(t, {})
        mult, peg = pt.get("multiples", {}), pt.get("peg", {})
        price = r["price_native"]

        if r["weight_pct"] >= 25:
            add(
                "warning", f"{t}: concentrazione elevata",
                f"Pesa il {r['weight_pct']:.1f}% del portafoglio - spesso l'effetto di un prezzo per azione alto "
                "e non frazionabile piuttosto che una scelta deliberata. Una singola posizione di questa taglia "
                "domina il rischio complessivo indipendentemente dal suo beta.",
            )

        rating = r.get("risk_rating")
        if rating is not None and rating >= 8:
            add(
                "warning", f"{t}: risk rating elevato ({rating:.1f}/10)",
                "Tra le posizioni più rischiose del paniere su beta/volatilità/leva combinati - dimensiona la "
                "posizione, e la tua tolleranza a un eventuale drawdown, di conseguenza.",
            )

        stop = r.get("stop_loss")
        if stop is not None and price is not None and price <= stop:
            add(
                "critical", f"{t}: sotto il livello di stop-loss tecnico",
                f"Prezzo {price:.2f} {r['currency']} <= stop {stop:.2f} (50gg MA − 2×ATR14) - rivedi la posizione, "
                "questo è un segnale tecnico, non un ordine automatico.",
            )

        elow, ehigh = r.get("entry_zone_low"), r.get("entry_zone_high")
        if elow is not None and ehigh is not None and price is not None and elow <= price <= ehigh:
            add(
                "info", f"{t}: nella propria zona di ingresso tecnica",
                f"Prezzo {price:.2f} {r['currency']} entro la banda {elow:.2f}-{ehigh:.2f} - punto tecnicamente "
                "ragionevole per aumentare l'esposizione, se è quello che vuoi fare.",
            )

        bull = mult.get("bull_price") or peg.get("bull_price")
        if bull is not None and price is not None and price > bull:
            add(
                "info", f"{t}: tratta sopra il proprio bull case ({bull:.2f})",
                "Il modello non vede più upside nemmeno nello scenario ottimistico a questo prezzo - valuta una "
                "presa di profitto parziale o verifica se il bull case va aggiornato con nuovi dati.",
            )

        bear = mult.get("bear_price") or peg.get("bear_price")
        if bear is not None and price is not None and price < bear:
            add(
                "warning", f"{t}: tratta sotto il proprio bear case ({bear:.2f})",
                "Il mercato sta scontando uno scenario peggiore del nostro bear case - verifica se ci sono notizie "
                "fondamentali specifiche prima di considerarlo automaticamente un'opportunità.",
            )

        if mult.get("bull_price") is None and peg.get("bull_price") is None:
            add(
                "info", f"{t}: nessun target di prezzo calcolabile",
                "EPS forward negativo o dati insufficienti - monitora questa posizione qualitativamente "
                "(notizie, trimestrali), non con un target numerico.",
            )

    if eur_weight < 30:
        add(
            "info", "Split valutario sbilanciato verso USD",
            f"EUR {eur_weight:.0f}% / USD {usd_weight:.0f}% del portafoglio - esposizione cambio EUR/USD "
            "concentrata; valuta se coprire (posizione corta EUR/USD) o far crescere le posizioni EUR con "
            "i prossimi versamenti.",
        )
    elif eur_weight > 70:
        add(
            "info", "Split valutario sbilanciato verso EUR",
            f"EUR {eur_weight:.0f}% / USD {usd_weight:.0f}% del portafoglio.",
        )

    min_us_trade = us_trade_fee_eur / 0.02 if us_trade_fee_eur else None
    min_eu_trade = eu_trade_fee_eur / 0.02 if eu_trade_fee_eur else None
    if min_us_trade or min_eu_trade:
        add(
            "info", "Taglio minimo efficiente per il prossimo trade",
            f"Con una commissione stimata di EUR {us_trade_fee_eur:.0f} sui titoli USA, un ordine sotto ~EUR "
            f"{min_us_trade:,.0f} costa oltre il 2% in commissioni; sui titoli EU (fee EUR {eu_trade_fee_eur:.0f}) "
            f"la soglia scende a ~EUR {min_eu_trade:,.0f}. Accumulare prima di comprare piccoli tagli USA riduce "
            "il drag.",
        )

    severity_order = {"critical": 0, "warning": 1, "info": 2}
    suggestions.sort(key=lambda s: severity_order.get(s["severity"], 3))
    return suggestions


def build_dashboard_context(
    holdings: dict[str, int],
    instruments: dict[str, Instrument],
    raw_by_ticker: dict,
    passed_metrics: dict,
    price_targets: dict,
    risk_ratings: dict,
    fx_rates: dict,
    commissions: dict,
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
        if raw is not None and raw.history is not None and not raw.history.empty:
            scale = 100.0 if inst.pence_quoted else 1.0
            closes = (raw.history["Close"] / scale).tail(90).tolist()
            sparkline_html = dc.sparkline_chart(closes)

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
            "as_of": m.get("as_of"),
        })

    for r in rows:
        r["weight_pct"] = (r["eur_amount"] / total_eur * 100) if total_eur else 0.0

    n_us = sum(1 for t in holdings if instruments[t].currency != "EUR")
    n_eu = sum(1 for t in holdings if instruments[t].currency == "EUR")
    total_commissions = n_us * commissions["us_trade_eur"] + n_eu * commissions["eu_trade_eur"]

    history = load_history(history_path)
    previous = history[-1] if history else None
    wow = week_over_week(rows, total_eur, previous)

    today_snapshot = {
        "date": generated_at.strftime("%Y-%m-%d"),
        "total_value_eur": total_eur,
        "positions": {r["ticker"]: {"price_eur": r["price_eur"], "weight_pct": r["weight_pct"]} for r in rows},
    }
    append_history(history_path, today_snapshot)

    def _wavg(key):
        vals = [(r[key], r["weight_pct"]) for r in rows if r.get(key) is not None]
        wsum = sum(w for _, w in vals)
        return (sum(v * w for v, w in vals) / wsum) if wsum else None

    portfolio_beta = _wavg("beta")
    portfolio_vol = _wavg("vol_1y")
    portfolio_risk_rating = _wavg("risk_rating")

    eur_weight = sum(r["weight_pct"] for r in rows if r["currency"] == "EUR")
    usd_weight = 100.0 - eur_weight

    suggestions = curation_suggestions(rows, price_targets, instruments,
                                        commissions["us_trade_eur"], commissions["eu_trade_eur"])

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

    return {
        "generated_at": generated_at.strftime("%Y-%m-%d %H:%M UTC"),
        "rows": rows,
        "total_value_eur": total_eur,
        "total_commissions_eur": total_commissions,
        "commission_drag_pct": (total_commissions / total_eur * 100) if total_eur else None,
        "wow": wow,
        "portfolio_beta": portfolio_beta,
        "portfolio_vol": portfolio_vol,
        "portfolio_risk_rating": portfolio_risk_rating,
        "eur_weight": eur_weight,
        "usd_weight": usd_weight,
        "suggestions": suggestions,
        "backtest": backtest,
        "backtest_chart": backtest_chart_html,
        "scenario_analysis": scenario_analysis,
        "scenario_keys": scenario_keys,
        "scenario_chart": scenario_chart_html,
        "weight_donut": weight_donut,
        "risk_bar": risk_bar,
        "price_targets": price_targets,
    }
