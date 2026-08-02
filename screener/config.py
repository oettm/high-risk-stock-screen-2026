"""
Central, disclosed configuration for the screener: starting universe, screening
thresholds, scoring weights, valuation assumptions, and position-sizing inputs.

Everything that is a judgment call (thresholds, weights, discount rates, fees)
lives here as a named constant so the methodology is fully inspectable and the
run is reproducible - change a number here, re-run, and the whole report updates
consistently.
"""

from dataclasses import dataclass, field

# ---------------------------------------------------------------------------
# Investor profile (from the user's brief)
# ---------------------------------------------------------------------------
CAPITAL_EUR = 4600.0
HORIZON_YEARS = 3
RISK_PROFILE = "very high / very tolerant"
BASE_CURRENCY = "EUR"

# ---------------------------------------------------------------------------
# Starting universe: 10 liquid, disclosed names per preferred sector (50 total).
# This list IS the disclosed "starting universe" - not an external index.
# `exchange` / `currency` are the *native* listing a European retail investor
# would realistically buy. `pence_quoted=True` flags LSE tickers Yahoo reports
# in GBX (pence), which must be divided by 100 before FX conversion to EUR.
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class Instrument:
    ticker: str
    name: str
    sector: str
    exchange: str
    currency: str
    pence_quoted: bool = False


SECTOR_SEMIS = "Semiconductors"
SECTOR_ENERGY_INFRA = "Energy & Digital Infrastructure"
SECTOR_AI = "AI / Enterprise Software"
SECTOR_DEFENCE = "Defence"
SECTOR_CONSUMER = "Consumer Goods"

UNIVERSE: list[Instrument] = [
    # --- Semiconductors ---
    Instrument("NVDA", "NVIDIA Corp", SECTOR_SEMIS, "NASDAQ", "USD"),
    Instrument("AMD", "Advanced Micro Devices", SECTOR_SEMIS, "NASDAQ", "USD"),
    Instrument("TSM", "Taiwan Semiconductor (ADR)", SECTOR_SEMIS, "NYSE", "USD"),
    Instrument("ASML.AS", "ASML Holding", SECTOR_SEMIS, "Euronext Amsterdam", "EUR"),
    Instrument("AVGO", "Broadcom Inc", SECTOR_SEMIS, "NASDAQ", "USD"),
    Instrument("MU", "Micron Technology", SECTOR_SEMIS, "NASDAQ", "USD"),
    Instrument("ARM", "Arm Holdings", SECTOR_SEMIS, "NASDAQ", "USD"),
    Instrument("QCOM", "Qualcomm Inc", SECTOR_SEMIS, "NASDAQ", "USD"),
    Instrument("LRCX", "Lam Research", SECTOR_SEMIS, "NASDAQ", "USD"),
    Instrument("BESI.AS", "BE Semiconductor Industries", SECTOR_SEMIS, "Euronext Amsterdam", "EUR"),

    # --- Energy & Digital Infrastructure (data centers / grid / power) ---
    Instrument("VST", "Vistra Corp", SECTOR_ENERGY_INFRA, "NYSE", "USD"),
    Instrument("CEG", "Constellation Energy", SECTOR_ENERGY_INFRA, "NASDAQ", "USD"),
    Instrument("NEE", "NextEra Energy", SECTOR_ENERGY_INFRA, "NYSE", "USD"),
    Instrument("EQIX", "Equinix Inc (REIT)", SECTOR_ENERGY_INFRA, "NASDAQ", "USD"),
    Instrument("DLR", "Digital Realty Trust (REIT)", SECTOR_ENERGY_INFRA, "NYSE", "USD"),
    Instrument("GEV", "GE Vernova", SECTOR_ENERGY_INFRA, "NYSE", "USD"),
    Instrument("VRT", "Vertiv Holdings", SECTOR_ENERGY_INFRA, "NYSE", "USD"),
    Instrument("ETN", "Eaton Corp", SECTOR_ENERGY_INFRA, "NYSE", "USD"),
    Instrument("PWR", "Quanta Services", SECTOR_ENERGY_INFRA, "NYSE", "USD"),
    Instrument("IBE.MC", "Iberdrola", SECTOR_ENERGY_INFRA, "BME Madrid", "EUR"),

    # --- AI / Enterprise Software & Compute ---
    Instrument("MSFT", "Microsoft Corp", SECTOR_AI, "NASDAQ", "USD"),
    Instrument("GOOGL", "Alphabet Inc", SECTOR_AI, "NASDAQ", "USD"),
    Instrument("PLTR", "Palantir Technologies", SECTOR_AI, "NYSE", "USD"),
    Instrument("CRWD", "CrowdStrike Holdings", SECTOR_AI, "NASDAQ", "USD"),
    Instrument("SNOW", "Snowflake Inc", SECTOR_AI, "NYSE", "USD"),
    Instrument("NOW", "ServiceNow Inc", SECTOR_AI, "NYSE", "USD"),
    Instrument("ORCL", "Oracle Corp", SECTOR_AI, "NYSE", "USD"),
    Instrument("ANET", "Arista Networks", SECTOR_AI, "NYSE", "USD"),
    Instrument("DELL", "Dell Technologies", SECTOR_AI, "NYSE", "USD"),
    Instrument("SMCI", "Super Micro Computer", SECTOR_AI, "NASDAQ", "USD"),

    # --- Defence ---
    Instrument("LMT", "Lockheed Martin", SECTOR_DEFENCE, "NYSE", "USD"),
    Instrument("RTX", "RTX Corp", SECTOR_DEFENCE, "NYSE", "USD"),
    Instrument("NOC", "Northrop Grumman", SECTOR_DEFENCE, "NYSE", "USD"),
    Instrument("GD", "General Dynamics", SECTOR_DEFENCE, "NYSE", "USD"),
    Instrument("LHX", "L3Harris Technologies", SECTOR_DEFENCE, "NYSE", "USD"),
    Instrument("KTOS", "Kratos Defense & Security", SECTOR_DEFENCE, "NASDAQ", "USD"),
    Instrument("RHM.DE", "Rheinmetall AG", SECTOR_DEFENCE, "Xetra", "EUR"),
    Instrument("BA.L", "BAE Systems", SECTOR_DEFENCE, "London Stock Exchange", "GBP", pence_quoted=True),
    Instrument("LDO.MI", "Leonardo S.p.A.", SECTOR_DEFENCE, "Borsa Italiana", "EUR"),
    Instrument("HII", "Huntington Ingalls Industries", SECTOR_DEFENCE, "NYSE", "USD"),

    # --- Consumer Goods ---
    Instrument("PG", "Procter & Gamble", SECTOR_CONSUMER, "NYSE", "USD"),
    Instrument("KO", "Coca-Cola Co", SECTOR_CONSUMER, "NYSE", "USD"),
    Instrument("PEP", "PepsiCo Inc", SECTOR_CONSUMER, "NASDAQ", "USD"),
    Instrument("NKE", "Nike Inc", SECTOR_CONSUMER, "NYSE", "USD"),
    Instrument("MDLZ", "Mondelez International", SECTOR_CONSUMER, "NASDAQ", "USD"),
    Instrument("EL", "Estee Lauder Companies", SECTOR_CONSUMER, "NYSE", "USD"),
    Instrument("CL", "Colgate-Palmolive", SECTOR_CONSUMER, "NYSE", "USD"),
    Instrument("MC.PA", "LVMH Moet Hennessy", SECTOR_CONSUMER, "Euronext Paris", "EUR"),
    Instrument("NESN.SW", "Nestle SA", SECTOR_CONSUMER, "SIX Swiss Exchange", "CHF"),
    Instrument("OR.PA", "L'Oreal SA", SECTOR_CONSUMER, "Euronext Paris", "EUR"),
]

# ---------------------------------------------------------------------------
# Screening filters applied to the raw universe pull
# ---------------------------------------------------------------------------
MIN_MARKET_CAP_EUR = 1_500_000_000       # liquidity floor
MIN_REVENUE_HISTORY_YEARS = 4            # must have >= 4 fiscal years of revenue data
REQUIRE_POSITIVE_REVENUE = True

# ---------------------------------------------------------------------------
# Composite scoring weights (must sum to 1.0) - percentile-ranked within the
# universe that passes screening. Higher score = more attractive.
#   growth:        5y revenue CAGR percentile
#   fwd_growth:     analyst forward EPS growth estimate percentile
#   valuation:      cheaper vs in-universe sector peer median forward P/E => higher percentile
#   leverage:       lower Net Debt/EBITDA (or D/E fallback) => higher percentile
# No volatility/beta penalty is applied: the stated risk profile is "very high
# tolerance", so beta/volatility is reported, not screened out.
# ---------------------------------------------------------------------------
SCORE_WEIGHTS = {
    "growth": 0.35,
    "fwd_growth": 0.25,
    "valuation": 0.20,
    "leverage": 0.20,
}
assert abs(sum(SCORE_WEIGHTS.values()) - 1.0) < 1e-9

MAX_PICKS_PER_SECTOR = 3   # diversification cap
TARGET_PORTFOLIO_SIZE = 10

# ---------------------------------------------------------------------------
# Valuation assumptions (ESTIMATE, disclosed - not fact)
# ---------------------------------------------------------------------------
DCF_TERMINAL_GROWTH = 0.025          # 2.5% perpetual growth
DCF_BASE_DISCOUNT_RATE = 0.09        # 9% for lower-beta names
DCF_HIGH_BETA_DISCOUNT_RATE = 0.12   # 12% for beta > DCF_HIGH_BETA_THRESHOLD
DCF_HIGH_BETA_THRESHOLD = 1.3
DCF_PROJECTION_YEARS = 5
DCF_BEAR_GROWTH_HAIRCUT = 0.5        # bear case uses 50% of historical CAGR

# Multiples-method bull/bear percentiles taken from each stock's own in-universe
# sector peer group forward P/E distribution.
MULTIPLES_BULL_PERCENTILE = 0.75
MULTIPLES_BEAR_PERCENTILE = 0.25

# ---------------------------------------------------------------------------
# Risk rating model (1-10, 10 = highest risk) - weights on standardized inputs
# ---------------------------------------------------------------------------
RISK_WEIGHTS = {
    "beta": 0.35,
    "volatility": 0.35,
    "leverage": 0.20,
    "fx_single_name": 0.10,
}

# ---------------------------------------------------------------------------
# Entry zone / stop-loss
# ---------------------------------------------------------------------------
ATR_WINDOW_DAYS = 14
ATR_STOP_MULTIPLE = 2.0
MOVING_AVERAGE_WINDOW = 50

# ---------------------------------------------------------------------------
# Position sizing assumptions (disclosed)
# ---------------------------------------------------------------------------
ASSUMED_FEE_PER_TRADE_EUR = 1.0   # flat per-trade fee, typical of EU fractional-share brokers
CORE_TIER_SIZE = 6                 # top N scored names get "core" weight
CORE_WEIGHT_MULTIPLIER = 1.6       # core names get 1.6x the base satellite weight
FRACTIONAL_SHARES_ASSUMED = True   # explicit assumption - verify with your own broker

# ---------------------------------------------------------------------------
# FX
# ---------------------------------------------------------------------------
FX_FALLBACK_BASE_URL = "https://api.frankfurter.app/latest"

# ---------------------------------------------------------------------------
# Backtest (historical, look-back only - see report for hindsight-bias caveat)
# ---------------------------------------------------------------------------
BACKTEST_PERIOD = "3y"   # matches the stated 3-year investment horizon
BACKTEST_BENCHMARKS = {
    "^GSPC": {"name": "S&P 500", "currency": "USD"},
    "^STOXX": {"name": "STOXX Europe 600", "currency": "EUR"},
}

# ---------------------------------------------------------------------------
# Forward-looking scenario analysis (12-month, disclosed methodology per scenario)
# ---------------------------------------------------------------------------
SCENARIO_RATE_SHOCK_BPS = 0.02          # +200bps discount-rate shock, DCF bull-growth path
SCENARIO_FX_SHOCK_PCT = 0.15            # EUR appreciates 15% vs USD/GBP/CHF
SCENARIO_BASE_FALLBACK_GROWTH = 0.06    # used only if forward EPS growth is unavailable
