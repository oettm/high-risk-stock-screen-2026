"""
Integer-share (whole-lot) position sizing for a user-specified custom
portfolio: unlike sizing.py (which assumes fractional shares), this respects
a hard constraint that only whole shares can be bought - the reality for many
retail brokers/instruments. Uses a greedy proportional-allocation algorithm to
approximate target weights as closely as possible under that constraint, and
reports the leftover, un-investable cash explicitly rather than hiding it.
"""

from __future__ import annotations

from screener.config import Instrument, ASSUMED_FEE_PER_TRADE_EUR
from screener.scoring import eur_value


def greedy_integer_shares(
    tickers: list[str], price_eur: dict[str, float], target_weights: dict[str, float], investable: float
) -> dict[str, int]:
    """Two-phase allocation:
    1) Seed pass: give every affordable ticker its mandatory FIRST share,
       most expensive first - so a pricey name (e.g. one share costing more
       than its equal-weight target) still ends up HELD, instead of being
       silently crowded out by cheaper names that can fill the proportional
       score more efficiently. A user who names 8 stocks wants a portfolio
       containing all 8, not 7.
    2) Fill pass: with whatever cash remains, keep buying one more share of
       whichever ticker is currently furthest BELOW its target proportion of
       money deployed so far - minimizes (value_i + price_i) / target_weight_i,
       the standard greedy heuristic for proportional allocation under an
       integer-lot constraint. Because the seed share already dominates a
       pricey name's target weight, this pass naturally favors the other names
       until they catch up - no special-casing needed.
    """
    shares = {t: 0 for t in tickers}
    value = {t: 0.0 for t in tickers}
    remaining = investable

    seed_order = sorted(tickers, key=lambda t: price_eur.get(t) or 0, reverse=True)
    for t in seed_order:
        p = price_eur.get(t)
        if p and p <= remaining:
            shares[t] += 1
            value[t] += p
            remaining -= p

    affordable = [t for t in tickers if price_eur.get(t) and price_eur[t] <= remaining]
    while affordable:
        best_t, best_score = None, None
        for t in affordable:
            score = (value[t] + price_eur[t]) / target_weights[t]
            if best_score is None or score < best_score:
                best_t, best_score = t, score
        shares[best_t] += 1
        value[best_t] += price_eur[best_t]
        remaining -= price_eur[best_t]
        affordable = [t for t in tickers if price_eur.get(t) and price_eur[t] <= remaining]

    return shares


def build_integer_allocation(
    selected: list[str],
    metrics: dict[str, dict],
    fx_rates: dict,
    instruments: dict[str, Instrument],
    capital_eur: float,
    target_weights: dict[str, float] | None = None,
) -> dict:
    if target_weights is None:
        target_weights = {t: 1.0 / len(selected) for t in selected}

    total_fees = len(selected) * ASSUMED_FEE_PER_TRADE_EUR
    investable = capital_eur - total_fees

    price_eur = {}
    unaffordable = []
    for t in selected:
        m = metrics[t]
        inst = instruments[t]
        p = eur_value(m["price_native"], inst.currency, fx_rates)
        price_eur[t] = p
        if p is None or p > investable:
            unaffordable.append(t)

    buyable = [t for t in selected if t not in unaffordable]
    shares = greedy_integer_shares(buyable, price_eur, {t: target_weights[t] for t in buyable}, investable)

    rows = []
    sector_totals: dict[str, float] = {}
    non_eur_eur_amount = 0.0
    total_deployed = 0.0

    for t in selected:
        m = metrics[t]
        inst = instruments[t]
        n_shares = shares.get(t, 0)
        eur_amount = n_shares * price_eur[t] if price_eur.get(t) else 0.0
        total_deployed += eur_amount

        sector_totals[inst.sector] = sector_totals.get(inst.sector, 0.0) + eur_amount
        if inst.currency != "EUR":
            non_eur_eur_amount += eur_amount

        rows.append({
            "ticker": t,
            "name": m["long_name"],
            "sector": inst.sector,
            "tier": "held" if n_shares > 0 else "unaffordable",
            "target_weight_pct": target_weights[t] * 100,
            "weight_pct": (eur_amount / total_deployed * 100) if total_deployed else 0.0,  # filled in properly below
            "eur_amount": eur_amount,
            "price_native": m["price_native"],
            "currency": inst.currency,
            "price_eur": price_eur.get(t),
            "shares": n_shares,
            "fee_eur": ASSUMED_FEE_PER_TRADE_EUR,
        })

    # second pass: realized weight is % of money actually deployed, not of investable budget
    for r in rows:
        r["weight_pct"] = (r["eur_amount"] / total_deployed * 100) if total_deployed else 0.0
        r["deviation_from_target_pct"] = r["weight_pct"] - r["target_weight_pct"]

    leftover_cash = investable - total_deployed
    fee_drag_pct = (total_fees / capital_eur) * 100
    non_eur_pct = (non_eur_eur_amount / total_deployed) * 100 if total_deployed else 0.0
    fx_shock_impact_eur = non_eur_eur_amount * 0.10

    return {
        "capital_eur": capital_eur,
        "total_fees_eur": total_fees,
        "fee_drag_pct": fee_drag_pct,
        "investable_eur": total_deployed,   # what backtest.py/scenarios.py treat as the invested base
        "budget_investable_eur": investable,  # capital minus fees, before the integer-share rounding gap
        "leftover_cash_eur": leftover_cash,
        "unaffordable_tickers": unaffordable,
        "rows": rows,
        "sector_totals_eur": sector_totals,
        "sector_totals_pct": {s: v / total_deployed * 100 for s, v in sector_totals.items()} if total_deployed else {},
        "non_eur_exposure_pct": non_eur_pct,
        "fx_10pct_shock_impact_eur": fx_shock_impact_eur,
        "n_positions": len([r for r in rows if r["shares"] > 0]),
    }
