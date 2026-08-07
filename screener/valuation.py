"""
12-month bull/bear price targets, two disclosed methods, both labeled ESTIMATE.

1) Multiples method: bull/bear forward P/E taken from the stock's own
   in-universe sector-peer forward P/E distribution (25th/75th percentile),
   applied to the stock's own forward EPS estimate.
2) PEG method: bull/bear PEG ratio (forward P/E / forward EPS growth%) taken
   from the same in-universe sector-peer distribution, applied to the stock's
   own forward growth rate and forward EPS. PEG normalizes the multiple for
   growth, which the plain P/E method (1) does not - a stock trading at a
   high P/E because it's growing fast doesn't get penalized the way it does
   in a growth-blind peer-multiple comparison.

A prior version used a simplified single-stage DCF as method (2). It was
replaced (2026) because a DCF's terminal value is extremely sensitive to the
(small) spread between the discount rate and the terminal growth rate, which
produced counter-intuitive "bull case below current price" results for
richly-priced, debt-carrying names (e.g. AVGO) even when every input was
correct - a real weakness of that method for this use case, not a bug. PEG
avoids that specific sensitivity (no discount-rate/terminal-growth spread to
divide by) while still being a standard, reproducible, peer-anchored method.
"""

from __future__ import annotations

import numpy as np

from screener.config import MULTIPLES_BULL_PERCENTILE, MULTIPLES_BEAR_PERCENTILE
from screener.metrics import forward_eps_growth


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


def peg_target(metrics: dict, peer_pegs: list[float]) -> dict:
    fwd_eps = metrics.get("forward_eps")
    clean_peers = [p for p in peer_pegs if p is not None and p > 0 and np.isfinite(p)]

    fwd_growth = forward_eps_growth(metrics)["growth"]  # capped - see metrics.forward_eps_growth

    if fwd_eps is None or fwd_eps <= 0 or not fwd_growth or fwd_growth <= 0 or len(clean_peers) < 3:
        return {
            "method": "peg",
            "bull_price": None, "bear_price": None, "median_price": None,
            "bull_peg_used": None, "bear_peg_used": None, "median_peg_used": None,
            "forward_growth_used": fwd_growth,
            "peer_n": len(clean_peers),
            "warning": "Insufficient forward growth (must be positive) or peer sample (<3) for a PEG target",
        }

    bull_peg = float(np.percentile(clean_peers, MULTIPLES_BULL_PERCENTILE * 100))
    bear_peg = float(np.percentile(clean_peers, MULTIPLES_BEAR_PERCENTILE * 100))
    median_peg = float(np.median(clean_peers))
    growth_pct = fwd_growth * 100  # PEG convention: growth expressed as a plain number, e.g. 25 for 25%

    return {
        "method": "peg",
        "bull_price": round(bull_peg * growth_pct * fwd_eps, 2),
        "bear_price": round(bear_peg * growth_pct * fwd_eps, 2),
        "median_price": round(median_peg * growth_pct * fwd_eps, 2),
        "bull_peg_used": round(bull_peg, 2),
        "bear_peg_used": round(bear_peg, 2),
        "median_peg_used": round(median_peg, 2),
        "forward_growth_used": fwd_growth,
        "peer_n": len(clean_peers),
        "forward_eps_used": fwd_eps,
        "warning": None,
    }


def build_price_targets(metrics: dict, peer_forward_pes: list[float], peer_pegs: list[float]) -> dict:
    return {
        "multiples": multiples_target(metrics, peer_forward_pes),
        "peg": peg_target(metrics, peer_pegs),
    }
