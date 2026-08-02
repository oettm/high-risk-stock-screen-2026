"""
EUR 4,600 position sizing across the selected names: conviction-weighted
(not equal-weight), fractional shares, FX conversion, and an explicit
transaction-cost and FX-sensitivity readout.
"""

from __future__ import annotations

from screener.config import (
    Instrument,
    CAPITAL_EUR,
    ASSUMED_FEE_PER_TRADE_EUR,
    CORE_TIER_SIZE,
    CORE_WEIGHT_MULTIPLIER,
)
from screener.scoring import eur_value


def build_allocation(
    selected: list[str],
    metrics: dict[str, dict],
    scores: dict[str, dict],
    fx_rates: dict,
    instruments: dict[str, Instrument],
) -> dict:
    ranked = sorted(selected, key=lambda t: scores[t]["composite"], reverse=True)

    raw_weights = {}
    for i, t in enumerate(ranked):
        raw_weights[t] = CORE_WEIGHT_MULTIPLIER if i < CORE_TIER_SIZE else 1.0
    weight_sum = sum(raw_weights.values())
    weights = {t: w / weight_sum for t, w in raw_weights.items()}

    total_fees = len(selected) * ASSUMED_FEE_PER_TRADE_EUR
    investable = CAPITAL_EUR - total_fees

    rows = []
    sector_totals: dict[str, float] = {}
    non_eur_eur_amount = 0.0

    for t in ranked:
        m = metrics[t]
        inst = instruments[t]
        eur_amount = investable * weights[t]
        price_eur = eur_value(m["price_native"], inst.currency, fx_rates)
        shares = (eur_amount / price_eur) if price_eur else None

        sector_totals[inst.sector] = sector_totals.get(inst.sector, 0.0) + eur_amount
        if inst.currency != "EUR":
            non_eur_eur_amount += eur_amount

        rows.append({
            "ticker": t,
            "name": m["long_name"],
            "sector": inst.sector,
            "tier": "core" if raw_weights[t] == CORE_WEIGHT_MULTIPLIER else "satellite",
            "weight_pct": weights[t] * 100,
            "eur_amount": eur_amount,
            "price_native": m["price_native"],
            "currency": inst.currency,
            "price_eur": price_eur,
            "shares": shares,
            "fee_eur": ASSUMED_FEE_PER_TRADE_EUR,
        })

    fee_drag_pct = (total_fees / CAPITAL_EUR) * 100
    non_eur_pct = (non_eur_eur_amount / investable) * 100 if investable else 0.0
    fx_shock_impact_eur = non_eur_eur_amount * 0.10  # illustrative 10% EUR appreciation shock

    return {
        "capital_eur": CAPITAL_EUR,
        "total_fees_eur": total_fees,
        "fee_drag_pct": fee_drag_pct,
        "investable_eur": investable,
        "rows": rows,
        "sector_totals_eur": sector_totals,
        "sector_totals_pct": {s: v / investable * 100 for s, v in sector_totals.items()},
        "non_eur_exposure_pct": non_eur_pct,
        "fx_10pct_shock_impact_eur": fx_shock_impact_eur,
        "n_positions": len(selected),
    }
