"""
Per-stock fundamental & technical metrics computed from a RawStock.
Every function tolerates missing data and returns None rather than guessing.

Note on GBX/pence-quoted LSE tickers (e.g. BA.L): Yahoo Finance reports
*price-like* fields (currentPrice, target prices, 52w high/low, OHLC history,
raw dividend-per-payment series) in GBX (pence), while *per-share fundamentals*
(trailing/forward EPS, book value, dividendRate) and aggregates (marketCap,
balance-sheet/income-statement lines) are already in GBP. `_price()` below
divides only the price-like fields by 100 for instruments flagged
`pence_quoted=True`; everything else is left as reported.
"""

from __future__ import annotations

import math
import pandas as pd

from screener.config import (
    Instrument,
    ATR_WINDOW_DAYS,
    ATR_STOP_MULTIPLE,
    MOVING_AVERAGE_WINDOW,
    MIN_REVENUE_HISTORY_YEARS,
)
from screener.fetch import RawStock


def _pence_scale(instrument: Instrument) -> float:
    return 100.0 if instrument.pence_quoted else 1.0


def current_price(raw: RawStock) -> float | None:
    scale = _pence_scale(raw.instrument)
    price = raw.info.get("currentPrice") or raw.info.get("regularMarketPrice")
    if price is None and raw.history is not None and not raw.history.empty:
        price = float(raw.history["Close"].iloc[-1])
    return (price / scale) if price is not None else None


def revenue_history(raw: RawStock) -> dict:
    """Returns {years: [...], revenues: [...], cagr, n_years, warning}."""
    if raw.income_stmt is None or raw.income_stmt.empty or "Total Revenue" not in raw.income_stmt.index:
        return {"years": [], "revenues": [], "cagr": None, "n_years": 0,
                "warning": "Total Revenue not available from Yahoo Finance"}

    series = raw.income_stmt.loc["Total Revenue"].dropna()
    series = series.sort_index()  # ascending by fiscal year
    years = [c.year for c in series.index]
    revenues = [float(v) for v in series.values]

    warning = None
    n_years = len(revenues)
    if n_years < MIN_REVENUE_HISTORY_YEARS:
        warning = f"Only {n_years} fiscal year(s) of revenue available (wanted >= {MIN_REVENUE_HISTORY_YEARS})"

    cagr = None
    if n_years >= 2 and revenues[0] > 0:
        cagr = (revenues[-1] / revenues[0]) ** (1 / (n_years - 1)) - 1

    return {"years": years, "revenues": revenues, "cagr": cagr, "n_years": n_years, "warning": warning}


def leverage(raw: RawStock) -> dict:
    """Debt/Equity and Net Debt/EBITDA, both FACT where available."""
    de = None
    net_debt_ebitda = None
    warning = None

    if raw.balance_sheet is not None and not raw.balance_sheet.empty:
        bs = raw.balance_sheet
        total_debt = _first_available(bs, ["Total Debt"])
        equity = _first_available(bs, ["Stockholders Equity", "Common Stock Equity"])
        net_debt = _first_available(bs, ["Net Debt"])

        if total_debt is not None and equity not in (None, 0):
            de = total_debt / equity

        if net_debt is not None and raw.income_stmt is not None and "EBITDA" in raw.income_stmt.index:
            ebitda = raw.income_stmt.loc["EBITDA"].dropna()
            if not ebitda.empty and ebitda.iloc[0] not in (0, None):
                net_debt_ebitda = net_debt / ebitda.iloc[0]

    if de is None and net_debt_ebitda is None:
        # fallback to yfinance's own pre-computed ratio
        info_de = raw.info.get("debtToEquity")
        if info_de is not None:
            de = info_de / 100.0  # yfinance reports this as a percentage
        else:
            warning = "Debt/Equity and Net Debt/EBITDA unavailable from Yahoo Finance"

    return {"debt_to_equity": de, "net_debt_to_ebitda": net_debt_ebitda, "warning": warning}


def _first_available(df: pd.DataFrame, row_names: list[str]):
    for name in row_names:
        if name in df.index:
            val = df.loc[name].dropna()
            if not val.empty:
                return float(val.iloc[0])
    return None


def dividend_metrics(raw: RawStock, price: float | None) -> dict:
    scale = _pence_scale(raw.instrument)
    div_yield = raw.info.get("dividendYield")  # already a percentage, e.g. 3.01 = 3.01%
    payout_ratio = raw.info.get("payoutRatio")  # fraction, e.g. 0.64

    fcf_payout = None
    if raw.cashflow is not None and not raw.cashflow.empty:
        fcf = _first_available(raw.cashflow, ["Free Cash Flow"])
        div_paid = _first_available(raw.cashflow, ["Cash Dividends Paid", "Common Stock Dividend Paid"])
        if fcf not in (None, 0) and div_paid is not None:
            fcf_payout = abs(div_paid) / fcf

    history_note = "No dividend history on file (or non-payer)"
    cut_flag = False
    if raw.dividends is not None and not raw.dividends.empty:
        by_year = (raw.dividends / scale).groupby(raw.dividends.index.year).sum()
        by_year = by_year.tail(6)
        if len(by_year) >= 2:
            diffs = by_year.diff().dropna()
            cut_flag = bool((diffs < -0.001).any())
            history_note = (
                f"Annual dividend/share by year: "
                + ", ".join(f"{y}: {v:.3f}" for y, v in by_year.items())
            )

    return {
        "dividend_yield_pct": div_yield,
        "payout_ratio": payout_ratio,
        "fcf_payout_ratio": fcf_payout,
        "history_note": history_note,
        "cut_in_last_6y": cut_flag,
    }


def beta_and_volatility(raw: RawStock) -> dict:
    beta = raw.info.get("beta")
    ann_vol = None
    if raw.history is not None and len(raw.history) > 30:
        rets = raw.history["Close"].pct_change(fill_method=None).dropna()
        rets = rets.tail(252)
        if len(rets) > 20:
            ann_vol = float(rets.std() * math.sqrt(252))
    return {"beta": beta, "annualized_volatility_1y": ann_vol}


def technical_levels(raw: RawStock) -> dict:
    """50-day moving average, 14-day ATR, entry zone, stop-loss. All FACT, price-history derived."""
    scale = _pence_scale(raw.instrument)
    if raw.history is None or raw.history.empty:
        return {"ma50": None, "atr14": None, "entry_zone_low": None, "entry_zone_high": None,
                "stop_loss": None, "warning": "No price history available"}

    h = raw.history.copy()
    for col in ["Open", "High", "Low", "Close"]:
        h[col] = h[col] / scale

    close = h["Close"]
    ma50 = close.rolling(MOVING_AVERAGE_WINDOW).mean().iloc[-1] if len(close) >= MOVING_AVERAGE_WINDOW else None

    high, low, prev_close = h["High"], h["Low"], close.shift(1)
    tr = pd.concat([
        (high - low),
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    atr14 = tr.rolling(ATR_WINDOW_DAYS).mean().iloc[-1] if len(tr) >= ATR_WINDOW_DAYS else None

    last_price = float(close.iloc[-1])
    entry_high = last_price
    entry_low = float(ma50) if ma50 is not None and not math.isnan(ma50) else last_price * 0.93
    if entry_low > entry_high:
        entry_low, entry_high = entry_high, entry_low * 0.97  # ma50 above price (uptrend) -> use a pullback band instead
    stop_loss = None
    if atr14 is not None and not math.isnan(atr14):
        stop_loss = entry_low - ATR_STOP_MULTIPLE * float(atr14)

    return {
        "ma50": None if ma50 is None or math.isnan(ma50) else float(ma50),
        "atr14": None if atr14 is None or math.isnan(atr14) else float(atr14),
        "entry_zone_low": round(entry_low, 2),
        "entry_zone_high": round(entry_high, 2),
        "stop_loss": None if stop_loss is None else round(stop_loss, 2),
        "warning": None,
    }


def compute_all_metrics(raw: RawStock) -> dict:
    price = current_price(raw)
    return {
        "ticker": raw.instrument.ticker,
        "as_of": raw.as_of,
        "price_native": price,
        "currency": raw.instrument.currency,
        "market_cap_native": raw.info.get("marketCap"),
        "trailing_pe": raw.info.get("trailingPE"),
        "forward_pe": raw.info.get("forwardPE"),
        "forward_eps": raw.info.get("forwardEps"),
        "trailing_eps": raw.info.get("trailingEps"),
        "revenue": revenue_history(raw),
        "leverage": leverage(raw),
        "dividend": dividend_metrics(raw, price),
        "beta_vol": beta_and_volatility(raw),
        "technicals": technical_levels(raw),
        "sector": raw.instrument.sector,
        "long_name": raw.info.get("longName") or raw.instrument.name,
        "data_error": raw.error,
    }
