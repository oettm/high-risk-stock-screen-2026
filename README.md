# High-Risk Growth Stock Screen — EUR 4,600 / 3-Year Horizon

A reproducible equity screening framework for a very-high-risk-tolerance, EUR 4,600,
3-year-horizon profile across **Semiconductors, Energy & Digital Infrastructure,
AI/Enterprise Software, Defence, and Consumer Goods**.

Every price, multiple, and fundamental in the report is fetched **live at run time**
from public, free, no-key data sources — nothing is hardcoded from a model's memory.
Re-run the script at any time and every figure refreshes with a new as-of date.

**Live report:** see the repository's GitHub Pages link (top of the GitHub repo page,
or ask whoever shared this link with you).

## What this is / is not

This is an educational, disclosed-methodology screening exercise, not personalised
financial advice. See the "Limitations & disclaimer" section at the bottom of the
report before acting on anything in it.

## How to run it

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

This will:
1. Fetch live FX rates (EUR conversion for every non-EUR ticker).
2. Fetch fundamentals, financials, dividends, and 2 years of price history for the
   50-name starting universe defined in `screener/config.py`.
3. Apply disclosed screening filters, compute a composite score, and select the
   top 10 (sector-diversified).
4. Compute 12-month bull/bear price targets (two methods), a 1-10 risk rating,
   entry zones/stop-losses, and a EUR 4,600 position-sizing plan.
5. Write `docs/index.html` (the shareable report) and two audit snapshots to `data/`:
   `universe_snapshot_<timestamp>.csv` (full raw pull) and
   `selected_10_<timestamp>.json` (final picks + every computed metric).

Runtime is a few minutes — the script deliberately pauses briefly between tickers
to avoid Yahoo Finance rate limits.

## Data sources (all free, no API key)

- **Prices, fundamentals, financials, dividends, analyst estimates:** [Yahoo Finance](https://finance.yahoo.com)
  via the [`yfinance`](https://github.com/ranaroussi/yfinance) library.
- **EUR/USD, EUR/GBP, EUR/CHF FX rates:** Yahoo Finance FX tickers (e.g. `USDEUR=X`),
  with a fallback to the [Frankfurter API](https://www.frankfurter.app/) (ECB
  reference rates, free, no key) if Yahoo is rate-limited.
- **Sector/peer valuation benchmark:** computed as the median forward P/E of the
  in-house sector peer group defined in `screener/config.py` — **not** a third-party
  index or paid subscription (e.g. no Bloomberg/FactSet/Damodaran data was used).
  This keeps the whole framework reproducible without credentials.

## Methodology summary

| Section | Method | Label |
|---|---|---|
| Starting universe | 50 curated, liquid tickers, 10 per sector, disclosed in `config.py` | Fact (the list itself is the methodology) |
| Screening filters | Market cap floor, ≥4y revenue history, positive revenue | Fact-derived |
| Composite score | Weighted percentile rank: revenue CAGR (35%), forward EPS growth (25%), in-sector valuation (20%), leverage (20%) | Estimate |
| Selection | Top-ranked name per sector guaranteed, remaining slots filled by score, max 3/sector | Estimate |
| Price targets | (A) peer forward-P/E bull/bear percentiles × forward EPS; (B) simplified single-stage DCF (beta-adjusted discount rate, capped growth, Gordon-growth terminal value) | Estimate |
| Risk rating (1-10) | Weighted percentile of beta, 1y realized volatility, leverage, non-EUR currency exposure | Estimate |
| Entry zone / stop-loss | 50-day moving average pullback band; stop = entry − 2×14-day ATR | Fact-derived |
| Moat / competitive advantage | Qualitative write-up (`screener/qualitative.py`) | **Opinion**, not from runtime data |
| Position sizing | Conviction-weighted (top 6 "core", remaining 4 "satellite"), fractional shares assumed, EUR 1/trade fee assumption disclosed | Estimate |

Full detail and every formula/assumption is shown inline in the report next to the
numbers it produced.

## Repository layout

```
main.py                     entry point - run this
screener/
  config.py                 universe, thresholds, weights, valuation & FX assumptions
  fetch.py                  yfinance + FX pulls, retries, fallbacks
  metrics.py                growth CAGR, leverage, dividends, beta/volatility, ATR/entry-stop
  valuation.py              multiples + simplified DCF bull/bear price targets
  scoring.py                screening filters, composite score, risk rating, top-10 selection
  sizing.py                 EUR 4,600 allocation logic
  qualitative.py            moat write-ups (OPINION, not runtime data)
  charts.py                 Plotly figure builders
  report.py                 Jinja2 context builder + HTML renderer
  templates/report_template.html
data/                       audit snapshots (raw universe pull + final picks), timestamped
docs/index.html             the final report (served by GitHub Pages)
requirements.txt
```

## Known limitations

- Yahoo Finance data can lag, be revised, or be temporarily unavailable for a given
  ticker; any such gap is shown as "N/A", never invented.
- Price targets depend on disclosed, simplified assumptions (a single-stage DCF,
  a capped growth rate, a fixed discount rate) — small changes in those assumptions
  materially move the output. They are estimates, not guarantees.
- The valuation benchmark is an in-house peer median, not a licensed third-party
  index.
- Moat assessments are qualitative analyst opinion, not derived from the live data
  pull.
- Fee and FX-shock figures in the position-sizing section are illustrative;
  confirm real costs and fractional-share support with your own broker.

## Disclaimer

This project is educational research, not personalised financial advice. It does
not account for your full financial situation, existing holdings, or tax treatment.
Final investment decisions — including whether to invest at all — are yours alone.
