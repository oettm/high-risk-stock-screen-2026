"""
12-month bull/bear price targets, two disclosed methods, both labeled ESTIMATE.

1) Multiples method: bull/bear forward P/E taken from the stock's own
   in-universe sector-peer forward P/E distribution (25th/75th percentile),
   applied to the stock's own forward EPS estimate.
2) Simplified DCF: project Free Cash Flow off the historical revenue CAGR
   (bull = full CAGR, bear = CAGR x haircut), discount at a beta-dependent
   rate, add a Gordon-growth terminal value, subtract net debt, divide by
   shares outstanding. This is a simplification (single-stage growth, no
   margin-expansion modeling) - disclosed as such in the report.
"""

from __future__ import annotations

import numpy as np

from screener.config import (
    DCF_TERMINAL_GROWTH,
    DCF_BASE_DISCOUNT_RATE,
    DCF_HIGH_BETA_DISCOUNT_RATE,
    DCF_HIGH_BETA_THRESHOLD,
    DCF_PROJECTION_YEARS,
    DCF_BEAR_GROWTH_HAIRCUT,
    MULTIPLES_BULL_PERCENTILE,
    MULTIPLES_BEAR_PERCENTILE,
)
import yfinance as yf

from screener.fetch import RawStock
from screener.metrics import _first_available


def _financial_to_price_fx(raw: RawStock) -> float | None:
    """Some ADRs (e.g. TSM) report financial statements in a different currency
    than the price (financialCurrency != currency, e.g. TWD financials vs. a USD
    ADR price). Fetch a live conversion rate so FCF/net-debt aren't mixed with a
    mismatched share count; return None (disabling the DCF) if the rate can't be
    fetched, rather than silently producing a wrong per-share value."""
    price_ccy = raw.info.get("currency")
    fin_ccy = raw.info.get("financialCurrency")
    if not price_ccy or not fin_ccy or price_ccy == fin_ccy:
        return 1.0
    try:
        hist = yf.Ticker(f"{fin_ccy}{price_ccy}=X").history(period="5d")
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1])
    except Exception:  # noqa: BLE001
        pass
    return None


def multiples_target(metrics: dict, peer_forward_pes: list[float]) -> dict:
    fwd_eps = metrics.get("forward_eps")
    clean_peers = [p for p in peer_forward_pes if p is not None and p > 0 and np.isfinite(p)]

    if fwd_eps is None or fwd_eps <= 0 or len(clean_peers) < 3:
        return {
            "method": "multiples",
            "bull_price": None,
            "bear_price": None,
            "bull_pe_used": None,
            "bear_pe_used": None,
            "peer_n": len(clean_peers),
            "warning": "Insufficient forward EPS or peer sample (<3) for a multiples target",
        }

    bull_pe = float(np.percentile(clean_peers, MULTIPLES_BULL_PERCENTILE * 100))
    bear_pe = float(np.percentile(clean_peers, MULTIPLES_BEAR_PERCENTILE * 100))
    return {
        "method": "multiples",
        "bull_price": round(bull_pe * fwd_eps, 2),
        "bear_price": round(bear_pe * fwd_eps, 2),
        "bull_pe_used": round(bull_pe, 1),
        "bear_pe_used": round(bear_pe, 1),
        "peer_n": len(clean_peers),
        "forward_eps_used": fwd_eps,
        "warning": None,
    }


def dcf_core(fcf0: float, shares: float, net_debt: float, discount_rate: float,
              growth: float, terminal_growth: float = DCF_TERMINAL_GROWTH,
              years: int = DCF_PROJECTION_YEARS) -> float:
    """Single-stage FCF projection -> Gordon-growth terminal value -> equity value/share."""
    pv_sum = 0.0
    fcf = fcf0
    for year in range(1, years + 1):
        fcf = fcf * (1 + growth)
        pv_sum += fcf / ((1 + discount_rate) ** year)
    terminal_fcf = fcf * (1 + terminal_growth)
    terminal_value = terminal_fcf / (discount_rate - terminal_growth)
    pv_terminal = terminal_value / ((1 + discount_rate) ** years)
    enterprise_value = pv_sum + pv_terminal
    equity_value = enterprise_value - (net_debt or 0.0)
    return equity_value / shares


def dcf_inputs(raw: RawStock, metrics: dict) -> dict | None:
    """Shared inputs (fcf0, shares, net_debt, base discount rate, bull/bear growth)
    used by both the report's DCF price target and the scenario engine, so the two
    stay consistent with each other."""
    if raw.cashflow is None or raw.cashflow.empty:
        return None
    fcf0 = _first_available(raw.cashflow, ["Free Cash Flow"])
    shares = raw.info.get("sharesOutstanding")
    net_debt = None
    if raw.balance_sheet is not None and not raw.balance_sheet.empty:
        net_debt = _first_available(raw.balance_sheet, ["Net Debt"])
    if fcf0 is None or fcf0 <= 0 or not shares:
        return None

    fx = _financial_to_price_fx(raw)
    if fx is None:
        return None
    fcf0 = fcf0 * fx
    net_debt = (net_debt * fx) if net_debt is not None else None

    beta = metrics.get("beta_vol", {}).get("beta")
    discount_rate = (
        DCF_HIGH_BETA_DISCOUNT_RATE
        if (beta is not None and beta > DCF_HIGH_BETA_THRESHOLD)
        else DCF_BASE_DISCOUNT_RATE
    )
    hist_cagr = metrics.get("revenue", {}).get("cagr")
    bull_growth = min(max(hist_cagr, 0.0), 0.40) if hist_cagr is not None else 0.08
    bear_growth = bull_growth * DCF_BEAR_GROWTH_HAIRCUT

    return {
        "fcf0": fcf0, "shares": shares, "net_debt": net_debt or 0.0,
        "discount_rate": discount_rate, "bull_growth": bull_growth, "bear_growth": bear_growth,
    }


def simplified_dcf(raw: RawStock, metrics: dict) -> dict:
    inputs = dcf_inputs(raw, metrics)
    if inputs is None:
        return {"method": "dcf", "bull_price": None, "bear_price": None,
                "warning": "No cash-flow statement, or missing/non-positive FCF / shares outstanding - DCF not computed"}

    bull_price = dcf_core(inputs["fcf0"], inputs["shares"], inputs["net_debt"],
                            inputs["discount_rate"], inputs["bull_growth"])
    bear_price = dcf_core(inputs["fcf0"], inputs["shares"], inputs["net_debt"],
                            inputs["discount_rate"], inputs["bear_growth"])

    return {
        "method": "dcf",
        "bull_price": round(bull_price, 2),
        "bear_price": round(min(bear_price, bull_price), 2),
        "discount_rate": inputs["discount_rate"],
        "terminal_growth": DCF_TERMINAL_GROWTH,
        "bull_growth_assumption": round(inputs["bull_growth"], 4),
        "bear_growth_assumption": round(inputs["bear_growth"], 4),
        "projection_years": DCF_PROJECTION_YEARS,
        "fcf_base": inputs["fcf0"],
        "net_debt_used": inputs["net_debt"],
        "shares_outstanding": inputs["shares"],
        "warning": None,
    }


def build_price_targets(raw: RawStock, metrics: dict, peer_forward_pes: list[float]) -> dict:
    return {
        "multiples": multiples_target(metrics, peer_forward_pes),
        "dcf": simplified_dcf(raw, metrics),
    }
