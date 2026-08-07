"""
Historical backtest of the selected, conviction-weighted portfolio vs. two
benchmarks (S&P 500, STOXX Europe 600), over the trailing period defined by
BACKTEST_PERIOD (default 3y, matching the stated investment horizon).

IMPORTANT CAVEAT (also shown in the report): this is a look-back over a
basket that was selected TODAY using data that already reflects how these
stocks performed. It demonstrates how the current basket has recently
behaved - it is not evidence the screening method would have picked these
same 10 names 3 years ago, and it is not a forecast. See the report's
"hindsight bias" note.
"""

from __future__ import annotations

import math
import time

import numpy as np
import pandas as pd
import yfinance as yf

from screener.config import Instrument, BACKTEST_PERIOD, BACKTEST_BENCHMARKS, RISK_FREE_TICKER


def fetch_risk_free_rate() -> dict:
    """Live proxy for the risk-free rate used in Sharpe ratios: US 13-week
    T-bill yield (^IRX). Not a perfect match for a EUR investor (no free,
    no-key EUR short-rate series on Yahoo), but it's live, free, and a
    reasonable proxy given the portfolio is majority USD-denominated -
    disclosed as such in the report."""
    try:
        hist = yf.Ticker(RISK_FREE_TICKER).history(period="5d")
        if hist is not None and not hist.empty:
            return {"rate": float(hist["Close"].iloc[-1]) / 100.0, "source": f"Yahoo Finance ({RISK_FREE_TICKER}, US 13-week T-bill yield)"}
    except Exception:  # noqa: BLE001
        pass
    return {"rate": None, "source": "unavailable"}


def _native_close_series(ticker: str, instrument: Instrument, period: str) -> pd.Series | None:
    try:
        hist = yf.Ticker(ticker).history(period=period, auto_adjust=True)
    except Exception:  # noqa: BLE001
        return None
    if hist is None or hist.empty:
        return None
    scale = 100.0 if instrument.pence_quoted else 1.0
    s = hist["Close"] / scale
    s.index = s.index.tz_localize(None)
    return s


def _fx_series_to_eur(currency: str, period: str) -> pd.Series | None:
    if currency == "EUR":
        return None
    try:
        hist = yf.Ticker(f"{currency}EUR=X").history(period=period)
    except Exception:  # noqa: BLE001
        return None
    if hist is None or hist.empty:
        return None
    s = hist["Close"]
    s.index = s.index.tz_localize(None)
    return s


def _max_drawdown(values: pd.Series) -> float:
    cummax = values.cummax()
    drawdown = values / cummax - 1
    return float(drawdown.min())


def _series_metrics(values: pd.Series, risk_free_rate: float | None) -> dict:
    total_return = values.iloc[-1] / values.iloc[0] - 1
    n_days = (values.index[-1] - values.index[0]).days
    years = max(n_days / 365.25, 1 / 365.25)
    cagr = (values.iloc[-1] / values.iloc[0]) ** (1 / years) - 1
    daily_rets = values.pct_change().dropna()
    ann_vol = float(daily_rets.std() * math.sqrt(252))
    sharpe = ((cagr - risk_free_rate) / ann_vol) if (risk_free_rate is not None and ann_vol > 0) else None
    return {
        "total_return_pct": float(total_return),
        "cagr_pct": float(cagr),
        "annualized_volatility_pct": ann_vol,
        "max_drawdown_pct": _max_drawdown(values),
        "sharpe_ratio": sharpe,
        "start_date": values.index[0].strftime("%Y-%m-%d"),
        "end_date": values.index[-1].strftime("%Y-%m-%d"),
    }


def run_backtest(
    selected: list[str],
    allocation: dict,
    instruments: dict[str, Instrument],
    period: str = BACKTEST_PERIOD,
) -> dict:
    weights = {r["ticker"]: r["weight_pct"] / 100.0 for r in allocation["rows"]}
    investable = allocation["investable_eur"]

    native_panels = {}
    for t in selected:
        s = _native_close_series(t, instruments[t], period)
        if s is not None:
            native_panels[t] = s
        time.sleep(0.3)

    missing = [t for t in selected if t not in native_panels]

    currencies_needed = {instruments[t].currency for t in native_panels}
    fx_panels = {}
    for ccy in currencies_needed:
        s = _fx_series_to_eur(ccy, period)
        if s is not None:
            fx_panels[ccy] = s
        time.sleep(0.3)

    # common business-day index across everything we have, forward-filled
    all_index = None
    for s in list(native_panels.values()) + list(fx_panels.values()):
        all_index = s.index if all_index is None else all_index.union(s.index)
    all_index = all_index.sort_values()

    eur_prices = {}
    for t, s in native_panels.items():
        ccy = instruments[t].currency
        s_r = s.reindex(all_index).ffill()
        if ccy == "EUR":
            eur_prices[t] = s_r
        elif ccy in fx_panels:
            fx_r = fx_panels[ccy].reindex(all_index).ffill()
            eur_prices[t] = s_r * fx_r
        else:
            missing.append(t)

    if not eur_prices:
        return {"error": "No usable price history for any selected ticker - backtest not computed"}

    panel = pd.DataFrame(eur_prices).dropna(how="any")  # start where ALL selected names have data
    if panel.empty or len(panel) < 30:
        return {"error": "Insufficient overlapping price history across selected names for a backtest"}

    active_weights = {t: weights[t] for t in panel.columns}
    weight_sum = sum(active_weights.values())
    active_weights = {t: w / weight_sum for t, w in active_weights.items()}  # renormalize if any ticker dropped

    shares = {t: (investable * w) / panel[t].iloc[0] for t, w in active_weights.items()}
    portfolio_value = sum(shares[t] * panel[t] for t in panel.columns)

    rf = fetch_risk_free_rate()

    result = {
        "start_date": panel.index[0].strftime("%Y-%m-%d"),
        "end_date": panel.index[-1].strftime("%Y-%m-%d"),
        "n_tickers_used": len(panel.columns),
        "n_tickers_requested": len(selected),
        "excluded_tickers": [t for t in selected if t not in panel.columns],
        "dates": [d.strftime("%Y-%m-%d") for d in panel.index],
        "portfolio_values": portfolio_value.tolist(),
        "portfolio_metrics": _series_metrics(portfolio_value, rf["rate"]),
        "risk_free_rate": rf,
        "benchmarks": {},
    }

    for bm_ticker, bm_meta in BACKTEST_BENCHMARKS.items():
        try:
            bm_hist = yf.Ticker(bm_ticker).history(period=period)
        except Exception:  # noqa: BLE001
            continue
        if bm_hist is None or bm_hist.empty:
            continue
        bm_close = bm_hist["Close"]
        bm_close.index = bm_close.index.tz_localize(None)
        bm_close = bm_close.reindex(all_index).ffill()

        if bm_meta["currency"] != "EUR":
            fx = fx_panels.get(bm_meta["currency"])
            if fx is None:
                continue
            fx_r = fx.reindex(all_index).ffill()
            bm_close = bm_close * fx_r

        bm_aligned = bm_close.reindex(panel.index).dropna()
        if bm_aligned.empty:
            continue
        bm_value = investable * (bm_aligned / bm_aligned.iloc[0])
        result["benchmarks"][bm_ticker] = {
            "name": bm_meta["name"],
            "values": bm_value.tolist(),
            "metrics": _series_metrics(bm_value, rf["rate"]),
        }

    return result
