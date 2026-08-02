"""
Screening filters, composite scoring, risk rating, and sector-diversified
top-10 selection. Every sub-score is a disclosed percentile rank - no
subjective overrides.

Valuation is ranked *within sector* (semis and staples trade at structurally
different multiples, so cross-sector P/E comparison would be misleading).
Growth, forward growth, and leverage are ranked *across the whole screened
universe* (a very-high-risk-tolerance mandate is comparing growth/balance-sheet
quality broadly, not just within a sector bucket).
"""

from __future__ import annotations

import numpy as np

from screener.config import (
    Instrument,
    MIN_MARKET_CAP_EUR,
    MIN_REVENUE_HISTORY_YEARS,
    REQUIRE_POSITIVE_REVENUE,
    SCORE_WEIGHTS,
    MAX_PICKS_PER_SECTOR,
    TARGET_PORTFOLIO_SIZE,
    RISK_WEIGHTS,
)


def eur_value(native_value: float | None, currency: str, fx_rates: dict) -> float | None:
    if native_value is None:
        return None
    rate = fx_rates.get(currency, {}).get("rate")
    if rate is None:
        return None
    return native_value * rate


def apply_screen(all_metrics: dict[str, dict], instruments: dict[str, Instrument], fx_rates: dict):
    passed, rejected = {}, {}
    for ticker, m in all_metrics.items():
        inst = instruments[ticker]
        reasons = []

        if m.get("data_error"):
            reasons.append(f"fetch error: {m['data_error']}")

        mcap_eur = eur_value(m.get("market_cap_native"), inst.currency, fx_rates)
        if mcap_eur is None:
            reasons.append("market cap unavailable")
        elif mcap_eur < MIN_MARKET_CAP_EUR:
            reasons.append(f"market cap EUR {mcap_eur:,.0f} < floor EUR {MIN_MARKET_CAP_EUR:,.0f}")

        rev = m.get("revenue", {})
        if rev.get("n_years", 0) < MIN_REVENUE_HISTORY_YEARS:
            reasons.append(f"only {rev.get('n_years', 0)} fiscal years of revenue (< {MIN_REVENUE_HISTORY_YEARS})")
        if REQUIRE_POSITIVE_REVENUE and rev.get("revenues") and rev["revenues"][-1] <= 0:
            reasons.append("latest revenue is not positive")

        if reasons:
            rejected[ticker] = reasons
        else:
            passed[ticker] = m
    return passed, rejected


def _percentile_ranks(values: dict[str, float | None], higher_is_better: bool = True) -> dict[str, float]:
    clean = {k: v for k, v in values.items() if v is not None and np.isfinite(v)}
    if len(clean) < 2:
        return {k: 0.5 for k in values}
    order = sorted(clean, key=lambda k: clean[k])
    n = len(order)
    ranks = {}
    for i, k in enumerate(order):
        pct = i / (n - 1)
        ranks[k] = pct if higher_is_better else 1 - pct
    for k in values:
        if k not in ranks:
            ranks[k] = 0.5  # neutral for missing data, not penalized nor rewarded
    return ranks


def compute_composite_scores(passed_metrics: dict[str, dict], instruments: dict[str, Instrument]) -> dict[str, dict]:
    growth_vals = {t: m["revenue"]["cagr"] for t, m in passed_metrics.items()}

    fwd_growth_vals = {}
    for t, m in passed_metrics.items():
        fe, te = m.get("forward_eps"), m.get("trailing_eps")
        fwd_growth_vals[t] = (fe / te - 1) if (fe and te and te > 0) else None

    leverage_vals = {}
    for t, m in passed_metrics.items():
        lev = m["leverage"]
        leverage_vals[t] = lev.get("net_debt_to_ebitda") if lev.get("net_debt_to_ebitda") is not None else lev.get("debt_to_equity")

    # valuation: within-sector percentile on forward P/E (fallback trailing P/E)
    valuation_pct: dict[str, float] = {}
    by_sector: dict[str, list[str]] = {}
    for t, m in passed_metrics.items():
        by_sector.setdefault(m["sector"], []).append(t)
    for sector, tickers in by_sector.items():
        pe_vals = {t: (passed_metrics[t].get("forward_pe") or passed_metrics[t].get("trailing_pe")) for t in tickers}
        valuation_pct.update(_percentile_ranks(pe_vals, higher_is_better=False))

    growth_pct = _percentile_ranks(growth_vals, higher_is_better=True)
    fwd_growth_pct = _percentile_ranks(fwd_growth_vals, higher_is_better=True)
    leverage_pct = _percentile_ranks(leverage_vals, higher_is_better=False)

    scores = {}
    for t in passed_metrics:
        components = {
            "growth": growth_pct[t],
            "fwd_growth": fwd_growth_pct[t],
            "valuation": valuation_pct[t],
            "leverage": leverage_pct[t],
        }
        composite = sum(components[k] * SCORE_WEIGHTS[k] for k in SCORE_WEIGHTS)
        scores[t] = {"components": components, "composite": composite,
                      "peer_forward_pe_sector": [
                          passed_metrics[p].get("forward_pe") for p in by_sector[passed_metrics[t]["sector"]]
                          if passed_metrics[p].get("forward_pe")
                      ]}
    return scores


def compute_risk_ratings(passed_metrics: dict[str, dict]) -> dict[str, dict]:
    beta_vals = {t: m["beta_vol"].get("beta") for t, m in passed_metrics.items()}
    vol_vals = {t: m["beta_vol"].get("annualized_volatility_1y") for t, m in passed_metrics.items()}
    lev_vals = {t: (m["leverage"].get("net_debt_to_ebitda") or m["leverage"].get("debt_to_equity")) for t, m in passed_metrics.items()}
    fx_vals = {t: (0.0 if m["currency"] == "EUR" else 1.0) for t, m in passed_metrics.items()}

    beta_pct = _percentile_ranks(beta_vals, higher_is_better=True)
    vol_pct = _percentile_ranks(vol_vals, higher_is_better=True)
    lev_pct = _percentile_ranks(lev_vals, higher_is_better=True)  # higher leverage = higher risk

    ratings = {}
    for t in passed_metrics:
        raw = (
            RISK_WEIGHTS["beta"] * beta_pct[t]
            + RISK_WEIGHTS["volatility"] * vol_pct[t]
            + RISK_WEIGHTS["leverage"] * lev_pct[t]
            + RISK_WEIGHTS["fx_single_name"] * fx_vals[t]
        )
        rating_1_10 = round(1 + raw * 9, 1)
        ratings[t] = {
            "rating": rating_1_10,
            "drivers": {
                "beta": passed_metrics[t]["beta_vol"].get("beta"),
                "annualized_volatility_1y": passed_metrics[t]["beta_vol"].get("annualized_volatility_1y"),
                "leverage_metric": lev_vals[t],
                "non_eur_currency": passed_metrics[t]["currency"] != "EUR",
            },
        }
    return ratings


def select_top_n(scores: dict[str, dict], instruments: dict[str, Instrument], n: int = TARGET_PORTFOLIO_SIZE) -> list[str]:
    ranked = sorted(scores.keys(), key=lambda t: scores[t]["composite"], reverse=True)

    selected: list[str] = []
    per_sector_count: dict[str, int] = {}

    # Pass 1: guarantee each preferred sector's top-ranked name is included
    sectors_seen = set()
    for t in ranked:
        sector = instruments[t].sector
        if sector not in sectors_seen:
            selected.append(t)
            sectors_seen.add(sector)
            per_sector_count[sector] = 1
        if len(sectors_seen) == len({instruments[x].sector for x in scores}):
            break

    # Pass 2: fill remaining slots by score, respecting the per-sector cap
    for t in ranked:
        if len(selected) >= n:
            break
        if t in selected:
            continue
        sector = instruments[t].sector
        if per_sector_count.get(sector, 0) >= MAX_PICKS_PER_SECTOR:
            continue
        selected.append(t)
        per_sector_count[sector] = per_sector_count.get(sector, 0) + 1

    # re-sort the final selection by score, descending
    selected.sort(key=lambda t: scores[t]["composite"], reverse=True)
    return selected[:n]
