"""
All network I/O lives here: yfinance pulls plus FX, with retries and a
no-key fallback for FX. Nothing here invents data - missing fields are
passed through as None and handled downstream (metrics.py / report.py).
"""

from __future__ import annotations

import time
import datetime as dt
from dataclasses import dataclass, field

import pandas as pd
import requests
import yfinance as yf

from screener.config import Instrument, FX_FALLBACK_BASE_URL

UTC_NOW = lambda: dt.datetime.now(dt.timezone.utc)


@dataclass
class RawStock:
    instrument: Instrument
    as_of: str
    info: dict = field(default_factory=dict)
    income_stmt: "pd.DataFrame | None" = None
    balance_sheet: "pd.DataFrame | None" = None
    cashflow: "pd.DataFrame | None" = None
    dividends: "pd.Series | None" = None
    history: "pd.DataFrame | None" = None
    error: str | None = None


def _retry(fn, attempts=3, delay=1.5, *args, **kwargs):
    last_exc = None
    for i in range(attempts):
        try:
            return fn(*args, **kwargs)
        except Exception as exc:  # noqa: BLE001 - deliberately broad, network can fail many ways
            last_exc = exc
            time.sleep(delay * (i + 1))
    raise last_exc


def fetch_stock(instrument: Instrument) -> RawStock:
    as_of = UTC_NOW().isoformat(timespec="seconds")
    raw = RawStock(instrument=instrument, as_of=as_of)
    try:
        t = yf.Ticker(instrument.ticker)
        raw.info = _retry(lambda: t.info) or {}
        raw.income_stmt = _retry(lambda: t.income_stmt)
        raw.balance_sheet = _retry(lambda: t.balance_sheet)
        raw.cashflow = _retry(lambda: t.cashflow)
        raw.dividends = _retry(lambda: t.dividends)
        raw.history = _retry(lambda: t.history(period="2y", auto_adjust=False))
    except Exception as exc:  # noqa: BLE001
        raw.error = f"{type(exc).__name__}: {exc}"
    return raw


def fetch_universe(instruments: list[Instrument]) -> dict[str, RawStock]:
    results = {}
    for inst in instruments:
        results[inst.ticker] = fetch_stock(inst)
        time.sleep(0.4)  # be polite to Yahoo's endpoint, reduce 429s
    return results


def fetch_fx_rate_to_eur(currency: str) -> tuple[float | None, str, str]:
    """
    Returns (rate, as_of, source) where 1 unit of `currency` * rate = EUR.
    EUR itself returns rate=1.0. Tries yfinance first, then Frankfurter (ECB, no key).
    """
    as_of = UTC_NOW().isoformat(timespec="seconds")
    if currency == "EUR":
        return 1.0, as_of, "N/A (already EUR)"

    pair = f"{currency}EUR=X"
    try:
        hist = _retry(lambda: yf.Ticker(pair).history(period="5d"))
        if hist is not None and not hist.empty:
            return float(hist["Close"].iloc[-1]), as_of, f"Yahoo Finance ({pair})"
    except Exception:  # noqa: BLE001
        pass

    try:
        resp = requests.get(
            FX_FALLBACK_BASE_URL, params={"from": currency, "to": "EUR"}, timeout=10
        )
        resp.raise_for_status()
        data = resp.json()
        rate = data["rates"]["EUR"]
        return float(rate), as_of, "Frankfurter API (ECB reference rate, fallback)"
    except Exception as exc:  # noqa: BLE001
        return None, as_of, f"UNAVAILABLE ({exc})"


def fetch_all_fx(currencies: set[str]) -> dict[str, dict]:
    out = {}
    for ccy in currencies:
        rate, as_of, source = fetch_fx_rate_to_eur(ccy)
        out[ccy] = {"rate": rate, "as_of": as_of, "source": source}
    return out
