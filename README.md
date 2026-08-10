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

## Custom portfolio (user-specified basket)

`python custom_main.py` runs a second, independent analysis for a **hand-picked** basket
instead of the systematic screener's own selection: NVDA, MSFT, VRT, TSM, AVGO, AMD,
ASML.AS, OR.PA, EUR 7,000, equal-weight target. Unlike the main report, it respects a
**whole-shares-only** constraint (no fractional shares) via a greedy proportional
allocation algorithm (`screener/custom_sizing.py`), and adds portfolio-level annualized
volatility and a **Sharpe ratio** (risk-free proxy: US 13-week T-bill yield, `^IRX`) to
the backtest. Output: `docs/custom-portfolio.html`, cross-linked from the main report.
It reuses the main screener's fundamentals/valuation/backtest/scenario pipeline and the
same 50-name universe as the peer-benchmarking/risk-percentile population, for
methodological consistency between the two reports.

A second custom basket, `python custom_main_5k.py`, runs the same analysis for MSFT,
NVDA, TSM, VRT, NOW, CRWV (CoreWeave), IREN (IREN Limited), SAN.PA (Sanofi), JNJ.DE
(Johnson & Johnson, Xetra EUR listing) at EUR 5,000. CRWV and IREN aren't in the
curated 50-name universe, so they're added as extra `Instrument` entries bucketed into
an existing sector (AI / Enterprise Software and Energy & Digital Infrastructure
respectively) purely so they get a real in-universe peer group for valuation/risk
percentiles - see the top of `custom_main_5k.py`. Both are pre-profit on a forward-EPS
basis, so their Method A/B price targets correctly show "insufficient data" rather than
a number.

SAN.PA and JNJ.DE were added after a live low-beta/low-volatility screen against a
healthcare shortlist, specifically to reduce the basket's very high average beta/
volatility and its 100%-USD currency concentration - both are EUR-denominated. JNJ.DE
is the Xetra EUR cross-listing of Johnson & Johnson (same company as NYSE: JNJ, chosen
so the position is bought/held in EUR); Yahoo Finance does not carry forward analyst
EPS/PE estimates for this cross-listing, so JNJ.DE's Method A/B price targets show
"insufficient data" - a real data-coverage gap of the EUR listing, not the negative-
earnings case CRWV/IREN hit. Both are bucketed into Consumer Goods (`SECTOR_CONSUMER`)
for peer-percentile purposes as the closest available in-universe group of large,
low-beta, dividend-paying blue chips - not a claim that pharma is literally a
consumer-goods sector; this makes SAN.PA's multiples/PEG bull case look more inflated
than a genuine pharma-peer comparison would, since Consumer Staples names structurally
trade at higher P/E than Big Pharma. Output: `docs/custom-portfolio-5k.html`,
cross-linked with both other reports.

Runtime is a few minutes — the script deliberately pauses briefly between tickers
to avoid Yahoo Finance rate limits.

## Portfolio dashboard (real holdings, auto-refreshed weekly)

`python dashboard_main.py` builds a Bloomberg-style dark dashboard for the ACTUAL shares
held (real quantities: SAN.PA 14, NVDA 4, VRT 4, ASML.AS 1, CRWV 10, NOW 6 - edit the
`HOLDINGS` dict at the top of the script when the real position changes), not a
target-weight construction like the other two custom reports. It shows current market
value, weight per position, beta/volatility/risk-rating (portfolio-level weighted
averages and per-position), price targets, entry-zone/stop-loss, the same trailing-3y
backtest and 5-scenario analysis as the other reports, plus four things unique to this
page:

- **Real P&L**: `COST_BASIS_EUR` at the top of `dashboard_main.py` holds what was
  actually paid per position, in EUR, excluding commissions (`None` until filled in -
  a position without a cost basis renders "N/A", never a guessed number). Once set,
  the dashboard shows per-position and total gain/loss in EUR and %, clearly
  distinguished from the hindsight backtest below it.
- **Portfolio evolution chart**: unlike the backtest (a look-back over today's basket
  projected backward), this is the *real* portfolio value at each weekly run, read
  from `data/dashboard_history.json` - a single point on the first run, growing one
  point every Monday.
- **Full per-stock price charts**: 2y price history with entry-zone/stop-loss bands
  for each held name (`screener/dashboard_charts.py`'s `stock_price_chart_dark()`),
  in addition to the compact 90-day sparkline in the positions table.
- **News + sentiment, with a filter toggle**: `screener/news_sentiment.py` pulls each
  ticker's recent headlines via `yfinance`'s `Ticker.news` (no API key) and classifies
  each one Positive/Negative/Neutral with VADER - but VADER's base lexicon is tuned for
  social-media text and returns "neutral" on almost every financial headline (tested:
  "beats earnings estimates" and "stock plunges" both score 0.0 unmodified), so its
  lexicon is extended with ~70 hand-picked finance terms (`FINANCE_LEXICON`) layered on
  top of VADER's own negation/intensifier rules. This is a disclosed heuristic on
  headline+summary text, not a trained model or an editorial judgment - labeled
  Estimate in the dashboard. The in-page toggle (vanilla JS, no framework) filters the
  list to Tutte/Positive/Negative/Neutre.

An earlier version of this dashboard had a rule-based curation-suggestions panel
(concentration/risk/stop-loss/entry-zone/bull-bear-breach/currency-imbalance alerts);
it was removed at the user's request in favor of the features above.

Unlike the other reports, this one carries state between runs:
`data/dashboard_history.json` keeps the last ~26 weekly snapshots so the dashboard can
show week-over-week price/weight deltas and the real portfolio-evolution chart, not
just a point-in-time view. A GitHub Actions workflow
(`.github/workflows/weekly-dashboard.yml`) re-runs the script every Monday 06:00 UTC
and commits the refreshed `docs/dashboard.html` + history file automatically - no
manual step needed once it's set up (can also be triggered manually via the Actions
tab, `workflow_dispatch`). Output: `docs/dashboard.html`.

Commission assumptions (`COMMISSIONS` dict, user-stated): ~EUR 21/trade for US-listed
names, ~EUR 1/trade for EU-listed names - used only to estimate total commission drag,
not fed into any valuation.

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
| Price targets | (A) peer forward-P/E bull/bear percentiles × forward EPS; (B) peer PEG-ratio bull/bear percentiles × forward EPS growth × forward EPS | Estimate |
| Risk rating (1-10) | Weighted percentile of beta, 1y realized volatility, leverage, non-EUR currency exposure | Estimate |
| Entry zone / stop-loss | 50-day moving average pullback band; stop = entry − 2×14-day ATR | Fact-derived |
| Moat / competitive advantage | Qualitative write-up (`screener/qualitative.py`) | **Opinion**, not from runtime data |
| Business overview | Business units, customers, key business risks (`screener/business_profile.py`), covers only names that have appeared in the selected top 10 | **Opinion**, not from runtime data |
| Position sizing | Conviction-weighted (top 6 "core", remaining 4 "satellite"), fractional shares assumed, EUR 1/trade fee assumption disclosed | Estimate |
| Backtest | Trailing 3y, FX-adjusted, buy-and-hold EUR value of the current basket at its conviction weights, vs. S&P 500 and STOXX Europe 600 | Fact-derived, **hindsight-biased by construction** (see caveat below) |
| 5 forward scenarios | Bull/Base/Bear (peer multiples + PEG), Rate shock (PEG de-rates to sector peer median), FX headwind (EUR +15%) - each a disclosed formula, no probabilities assigned | Estimate |

Full detail and every formula/assumption is shown inline in the report next to the
numbers it produced.

### Backtest and scenario caveats (important)

- The **backtest** applies today's screened basket retroactively over the trailing 3 years. This is a real,
  material look-ahead/survivorship bias: the 10 names were selected *because* their trailing growth and valuation
  looked good, so of course the backtest looks strong. It describes how the current basket has recently behaved -
  it is **not** proof the screening method would have picked these same names 3 years ago, and it is **not** a
  forecast.
- The **5 forward scenarios** are mechanical formulas (peer forward-P/E and PEG percentiles, a fixed 15% FX shock),
  not probability-weighted forecasts. No likelihood is assigned to any of the five, and actual outcomes will differ
  from all of them.
- **Why PEG instead of a DCF for Method B**: an earlier version used a simplified discounted cash-flow model. It was
  replaced because a DCF's terminal value is extremely sensitive to the (small) spread between the discount rate
  and the terminal growth rate, which produced misleading "bull case below today's price" results for richly-valued,
  debt-carrying names (e.g. Broadcom) even with every input correct - a real weakness of that method for this
  use case, not a bug. PEG (Price/Earnings-to-Growth) avoids that specific sensitivity, is a standard growth-stock
  valuation heuristic, and reuses the same in-universe peer-percentile pattern as Method A - but note it is still a
  relative-value (peer-anchored) method, not an independent intrinsic-value check: if a stock's whole peer group is
  overvalued, PEG will say so too.

## Sanofi deep dive (single-stock research report)

`python sanofi_deep_dive.py` builds a standalone report on Sanofi (SAN.PA) answering
five things: what the business does, why the stock has declined (5-year price chart
with the largest single-day moves annotated - each cause identified via web search on
the actual date, not guessed, and disclosed as sector-wide vs. Sanofi-specific),
financial solidity (margins, leverage, liquidity, FCF/dividend coverage), growth
projections and valuation, and active pipeline programs. Output: `docs/sanofi-deep-dive.html`.

Unlike the two portfolio reports (where Sanofi/SAN.PA is bucketed into "Consumer Goods"
purely so it has *some* peer group for percentile valuation - a disclosed simplification
that visibly inflates its bull-case target), this report benchmarks against a dedicated
pharmaceutical peer group (`PEER_TICKERS` in `sanofi_deep_dive.py`: NVO, AZN, MRK, LLY,
NOVN.SW, PFE, BMY, GSK, ABBV, JNJ), producing materially more credible Method A/B targets
- still shown alongside live analyst consensus for comparison, with the gap between the
two disclosed and explained rather than hidden.

Architecture: `screener/stock_deep_dive.py` (context builder: financials, dedicated-peer
valuation via the existing `valuation.build_price_targets()`, forward-growth calc) +
`screener/charts.py`'s `decline_annotated_chart()` (5y price line with researched-cause
annotations at each major move) and `peer_valuation_bar_chart()` + the driver script's
own `DECLINE_EVENTS`/`PIPELINE_PROJECTS` lists (Opinion content, sourced via web search,
not invented) + `screener/templates/stock_deep_dive_template.html` (reuses the same
light-theme Fact/Estimate/Opinion system as the other 3 reports, and reuses the existing
`BUSINESS_PROFILE`/`MOAT` entries for SAN.PA from the shared `screener/business_profile.py`
/ `screener/qualitative.py` modules).

## Repository layout

```
main.py                     entry point for the systematic 10-stock screen
custom_main.py               entry point for the custom 8-stock, EUR 7,000, whole-share portfolio
custom_main_5k.py             entry point for the custom 9-stock, EUR 5,000, whole-share portfolio
dashboard_main.py             entry point for the real-holdings dashboard (re-run weekly)
sanofi_deep_dive.py            entry point for the standalone Sanofi single-stock report
screener/
  config.py                 universe, thresholds, weights, valuation & FX assumptions
  fetch.py                  yfinance + FX pulls, retries, fallbacks
  metrics.py                growth CAGR, leverage, dividends, beta/volatility, ATR/entry-stop
  valuation.py              multiples + PEG bull/bear price targets
  scoring.py                screening filters, composite score, risk rating, top-10 selection
  sizing.py                 EUR 4,600 fractional-share allocation logic (systematic screen)
  custom_sizing.py          whole-share (no fractional) greedy allocation logic (custom portfolio)
  backtest.py               trailing 3y, FX-adjusted backtest vs. S&P 500 / STOXX 600, incl. Sharpe ratio
  scenarios.py              5 forward-looking 12-month scenarios (bull/base/bear/rate/FX)
  qualitative.py            moat write-ups (OPINION, not runtime data)
  business_profile.py       business units / customers / key risks per covered stock (OPINION, not runtime data)
  charts.py                 Plotly figure builders (light theme, used by the 3 report pages)
  dashboard_charts.py       Plotly figure builders (dark theme, used by the dashboard only)
  dashboard.py              real-holdings context builder, week-over-week history, real P&L
  news_sentiment.py         yfinance news pull + finance-tuned VADER sentiment classification
  report.py                 Jinja2 context builder + HTML renderer (shared by all 4 pages)
  templates/report_template.html            systematic screen report
  templates/custom_portfolio_template.html  custom portfolio reports (EUR 7k and 5k)
  templates/dashboard_template.html         real-holdings dashboard
  templates/stock_deep_dive_template.html   single-stock deep-dive report (Sanofi)
data/                       audit snapshots (raw universe pull + final picks), timestamped
data/dashboard_history.json  weekly dashboard snapshots (kept, not timestamped-pruned - powers week-over-week deltas)
docs/index.html             the systematic screen report (served by GitHub Pages)
docs/custom-portfolio.html  the EUR 7,000 custom portfolio report (served by GitHub Pages)
docs/custom-portfolio-5k.html  the EUR 5,000 custom portfolio report (served by GitHub Pages)
docs/dashboard.html         the real-holdings dashboard, auto-refreshed weekly (served by GitHub Pages)
docs/sanofi-deep-dive.html  the standalone Sanofi research report (served by GitHub Pages)
.github/workflows/weekly-dashboard.yml  cron job that re-runs dashboard_main.py every Monday and commits the result
requirements.txt
```

## Known limitations

- Yahoo Finance data can lag, be revised, or be temporarily unavailable for a given
  ticker; any such gap is shown as "N/A", never invented.
- Price targets depend on disclosed, peer-relative assumptions (forward P/E and PEG
  percentiles from the in-house sector peer group) — they are not guarantees, and both
  methods will overstate value if the whole peer group is overvalued.
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
