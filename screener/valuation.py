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
from screener.fetch import RawStock
from screener.metrics import _first_available


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


def simplified_dcf(raw: RawStock, metrics: dict) -> dict:
    if raw.cashflow is None or raw.cashflow.empty:
        return {"method": "dcf", "bull_price": None, "bear_price": None,
                "warning": "No cash-flow statement available for DCF"}

    fcf0 = _first_available(raw.cashflow, ["Free Cash Flow"])
    shares = raw.info.get("sharesOutstanding")
    net_debt = None
    if raw.balance_sheet is not None and not raw.balance_sheet.empty:
        net_debt = _first_available(raw.balance_sheet, ["Net Debt"])

    if fcf0 is None or fcf0 <= 0 or not shares:
        return {"method": "dcf", "bull_price": None, "bear_price": None,
                "warning": "Missing or non-positive FCF / shares outstanding - DCF not computed"}

    beta = metrics.get("beta_vol", {}).get("beta")
    discount_rate = (
        DCF_HIGH_BETA_DISCOUNT_RATE
        if (beta is not None and beta > DCF_HIGH_BETA_THRESHOLD)
        else DCF_BASE_DISCOUNT_RATE
    )

    hist_cagr = metrics.get("revenue", {}).get("cagr")
    bull_growth = min(max(hist_cagr, 0.0), 0.40) if hist_cagr is not None else 0.08
    bear_growth = bull_growth * DCF_BEAR_GROWTH_HAIRCUT

    def _dcf_value(growth: float) -> float:
        pv_sum = 0.0
        fcf = fcf0
        for year in range(1, DCF_PROJECTION_YEARS + 1):
            fcf = fcf * (1 + growth)
            pv_sum += fcf / ((1 + discount_rate) ** year)
        terminal_fcf = fcf * (1 + DCF_TERMINAL_GROWTH)
        terminal_value = terminal_fcf / (discount_rate - DCF_TERMINAL_GROWTH)
        pv_terminal = terminal_value / ((1 + discount_rate) ** DCF_PROJECTION_YEARS)
        enterprise_value = pv_sum + pv_terminal
        equity_value = enterprise_value - (net_debt or 0.0)
        return equity_value / shares

    bull_price = _dcf_value(bull_growth)
    bear_price = _dcf_value(bear_growth)

    return {
        "method": "dcf",
        "bull_price": round(bull_price, 2),
        "bear_price": round(min(bear_price, bull_price), 2),
        "discount_rate": discount_rate,
        "terminal_growth": DCF_TERMINAL_GROWTH,
        "bull_growth_assumption": round(bull_growth, 4),
        "bear_growth_assumption": round(bear_growth, 4),
        "projection_years": DCF_PROJECTION_YEARS,
        "fcf_base": fcf0,
        "net_debt_used": net_debt or 0.0,
        "shares_outstanding": shares,
        "warning": None,
    }


def build_price_targets(raw: RawStock, metrics: dict, peer_forward_pes: list[float]) -> dict:
    return {
        "multiples": multiples_target(metrics, peer_forward_pes),
        "dcf": simplified_dcf(raw, metrics),
    }
