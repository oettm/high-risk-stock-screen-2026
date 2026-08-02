"""
Forward-looking 12-month scenario analysis for the selected portfolio - five
disclosed, formula-driven scenarios (no gut-feel numbers). Each scenario
computes a per-stock projected EUR price, then aggregates to a portfolio
outcome using the position-sizing weights from sizing.py.

Scenarios:
  1. Bull       - average of the multiples-method and DCF bull price targets.
  2. Base       - current price grows at the stock's own forward EPS growth
                  rate, multiple held flat (no re-rating either way).
  3. Bear       - average of the multiples-method and DCF bear price targets.
  4. Rate shock - the DCF bull-growth cash-flow path repriced at the bull
                  discount rate + 200bps, isolating pure duration/rate risk.
  5. FX headwind- Base-case fundamentals, but EUR appreciates 15% vs
                  USD/GBP/CHF, isolating currency risk for the EUR investor.
"""

from __future__ import annotations

from screener.config import (
    Instrument,
    SCENARIO_RATE_SHOCK_BPS,
    SCENARIO_FX_SHOCK_PCT,
    SCENARIO_BASE_FALLBACK_GROWTH,
)
from screener.fetch import RawStock
from screener.valuation import dcf_inputs, dcf_core

SCENARIO_KEYS = ["bull", "base", "bear", "rate_shock", "fx_headwind"]

SCENARIO_META = {
    "bull": {
        "label": "Bull - AI/infra capex supercycle continues",
        "method": "Average of the multiples-method and DCF bull price targets (local currency), current FX.",
    },
    "base": {
        "label": "Base - trend growth, no re-rating",
        "method": "Current price compounded at the stock's own forward EPS growth rate; multiple held flat, current FX.",
    },
    "bear": {
        "label": "Bear - growth disappoints, multiples compress",
        "method": "Average of the multiples-method and DCF bear price targets (local currency), current FX.",
    },
    "rate_shock": {
        "label": "Rate shock - discount rates +200bps",
        "method": "DCF bull-growth cash-flow path repriced at bull discount rate + 200bps, current FX.",
    },
    "fx_headwind": {
        "label": "FX headwind - EUR +15% vs USD/GBP/CHF",
        "method": "Base-case local-currency price, converted at a shocked FX rate (EUR appreciates 15% vs non-EUR currencies).",
    },
}


def _fwd_growth(metrics: dict) -> tuple[float, bool]:
    fe, te = metrics.get("forward_eps"), metrics.get("trailing_eps")
    if fe and te and te > 0:
        return (fe / te - 1), False
    return SCENARIO_BASE_FALLBACK_GROWTH, True


def stock_scenarios(
    raw: RawStock, metrics: dict, price_targets: dict, instrument: Instrument, fx_rates: dict
) -> dict:
    price_now = metrics.get("price_native")
    rate_now = fx_rates.get(instrument.currency, {}).get("rate")
    if price_now is None or rate_now is None:
        return {"warning": "Missing current price or FX rate - scenarios not computed", "scenarios": {}}

    price_eur_now = price_now * rate_now
    mult = price_targets["multiples"]
    dcf = price_targets["dcf"]

    def _avg(a, b):
        vals = [v for v in (a, b) if v is not None]
        return sum(vals) / len(vals) if vals else None

    bull_native = _avg(mult.get("bull_price"), dcf.get("bull_price"))
    bear_native = _avg(mult.get("bear_price"), dcf.get("bear_price"))

    fwd_growth, fwd_growth_is_fallback = _fwd_growth(metrics)
    base_native = price_now * (1 + fwd_growth)

    rate_shock_native = None
    dcf_in = dcf_inputs(raw, metrics)
    if dcf_in is not None:
        rate_shock_native = dcf_core(
            dcf_in["fcf0"], dcf_in["shares"], dcf_in["net_debt"],
            dcf_in["discount_rate"] + SCENARIO_RATE_SHOCK_BPS, dcf_in["bull_growth"],
        )

    shocked_rate = rate_now if instrument.currency == "EUR" else rate_now / (1 + SCENARIO_FX_SHOCK_PCT)
    fx_headwind_eur = base_native * shocked_rate

    def _to_return(native_price):
        if native_price is None:
            return None, None
        eur_price = native_price * rate_now
        return eur_price, (eur_price / price_eur_now - 1)

    bull_eur, bull_ret = _to_return(bull_native)
    base_eur, base_ret = _to_return(base_native)
    bear_eur, bear_ret = _to_return(bear_native)
    rate_shock_eur, rate_shock_ret = _to_return(rate_shock_native)
    fx_headwind_ret = (fx_headwind_eur / price_eur_now - 1) if price_eur_now else None

    return {
        "warning": None,
        "price_eur_now": price_eur_now,
        "fwd_growth_used": fwd_growth,
        "fwd_growth_is_fallback": fwd_growth_is_fallback,
        "scenarios": {
            "bull": {"price_eur": bull_eur, "return_pct": bull_ret},
            "base": {"price_eur": base_eur, "return_pct": base_ret},
            "bear": {"price_eur": bear_eur, "return_pct": bear_ret},
            "rate_shock": {"price_eur": rate_shock_eur, "return_pct": rate_shock_ret},
            "fx_headwind": {"price_eur": fx_headwind_eur, "return_pct": fx_headwind_ret},
        },
    }


def build_scenario_analysis(
    selected: list[str],
    raw: dict[str, RawStock],
    metrics: dict[str, dict],
    price_targets: dict[str, dict],
    instruments: dict[str, Instrument],
    fx_rates: dict,
    allocation: dict,
) -> dict:
    per_stock = {
        t: stock_scenarios(raw[t], metrics[t], price_targets[t], instruments[t], fx_rates)
        for t in selected
    }

    rows_by_ticker = {r["ticker"]: r for r in allocation["rows"]}
    investable = allocation["investable_eur"]

    portfolio = {}
    for key in SCENARIO_KEYS:
        ending_value = 0.0
        missing = []
        for t in selected:
            row = rows_by_ticker[t]
            sc = per_stock[t]["scenarios"].get(key, {})
            ret = sc.get("return_pct")
            if ret is None:
                ret = 0.0
                missing.append(t)
            ending_value += row["eur_amount"] * (1 + ret)
        portfolio[key] = {
            "ending_value_eur": ending_value,
            "return_pct": ending_value / investable - 1 if investable else None,
            "missing_tickers": missing,
        }

    return {"per_stock": per_stock, "portfolio": portfolio, "meta": SCENARIO_META}
