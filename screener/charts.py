"""Plotly figure builders. All figures share one CDN plotly.js load (in the
template head); individual figures are embedded with include_plotlyjs=False.
"""

from __future__ import annotations

import plotly.graph_objects as go

from screener.config import SECTOR_SEMIS, SECTOR_ENERGY_INFRA, SECTOR_AI, SECTOR_DEFENCE, SECTOR_CONSUMER

TEMPLATE = "plotly_white"

# Validated palette (see dataviz skill references/palette.md) - light-mode steps,
# used here because chart panels render on a fixed light card regardless of the
# surrounding page theme.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"

# Fixed categorical order (validator-checked: adjacent-pair CVD/normal-vision all
# PASS in this exact sequence). Sector order is pinned - not data-dependent - so
# a pie chart only ever puts validated-adjacent colors next to each other; the
# WARN-band contrast on aqua/yellow/magenta is offset by always-visible wedge labels.
SECTOR_ORDER = [SECTOR_SEMIS, SECTOR_ENERGY_INFRA, SECTOR_AI, SECTOR_DEFENCE, SECTOR_CONSUMER]
SECTOR_COLORS = {
    SECTOR_SEMIS: "#2a78d6",
    SECTOR_ENERGY_INFRA: "#eb6834",
    SECTOR_AI: "#1baf7a",
    SECTOR_DEFENCE: "#eda100",
    SECTOR_CONSUMER: "#e87ba4",
}


def revenue_growth_chart(ticker: str, years: list[int], revenues: list[float], currency: str) -> str:
    if not years:
        return "<p><em>No revenue history available to chart.</em></p>"
    fig = go.Figure(go.Bar(x=years, y=[r / 1e9 for r in revenues], marker_color=BLUE))
    fig.update_layout(
        template=TEMPLATE, height=260, margin=dict(l=40, r=10, t=30, b=30),
        title=f"{ticker} - Annual revenue ({currency} bn)",
        yaxis_title=f"{currency} bn", xaxis=dict(type="category"),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def price_history_chart(ticker: str, dates, closes: list[float], ma50, entry_low, entry_high, stop_loss, currency: str) -> str:
    if closes is None or len(closes) == 0:
        return "<p><em>No price history available to chart.</em></p>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=closes, mode="lines", name="Close", line=dict(color=BLUE)))
    if entry_low is not None and entry_high is not None:
        fig.add_hrect(y0=entry_low, y1=entry_high, fillcolor=STATUS_GOOD, opacity=0.15, line_width=0,
                      annotation_text="Entry zone", annotation_position="top left")
    if stop_loss is not None:
        fig.add_hline(y=stop_loss, line_dash="dash", line_color=STATUS_CRITICAL,
                       annotation_text="Stop-loss", annotation_position="bottom left")
    fig.update_layout(
        template=TEMPLATE, height=280, margin=dict(l=40, r=10, t=30, b=30),
        title=f"{ticker} - 2y price history ({currency}), entry zone & stop-loss",
        yaxis_title=currency,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def composite_score_chart(tickers: list[str], scores: list[float]) -> str:
    fig = go.Figure(go.Bar(x=tickers, y=scores, marker_color=BLUE))
    fig.update_layout(
        template=TEMPLATE, height=320, margin=dict(l=40, r=10, t=30, b=30),
        title="Composite score by pick (0-1, higher = more attractive)",
        yaxis_title="Composite score", xaxis=dict(type="category"),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def allocation_pie_chart(sector_totals_pct: dict[str, float]) -> str:
    # Render in the fixed canonical sector order (not input/data order) so only
    # validator-checked adjacent color pairs ever end up touching on the wheel.
    labels = [s for s in SECTOR_ORDER if s in sector_totals_pct]
    values = [sector_totals_pct[s] for s in labels]
    colors = [SECTOR_COLORS.get(label, "#9e9e9e") for label in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.4, marker=dict(colors=colors),
        textinfo="label+percent", textposition="outside",
    ))
    fig.update_layout(
        template=TEMPLATE, height=400, margin=dict(l=10, r=10, t=30, b=10),
        title="Sector allocation (% of investable capital)", showlegend=False,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


def allocation_bar_chart(rows: list[dict]) -> str:
    fig = go.Figure(go.Bar(
        x=[r["ticker"] for r in rows],
        y=[r["eur_amount"] for r in rows],
        marker_color=[BLUE if r["tier"] == "core" else ORANGE for r in rows],
        text=[r["tier"] for r in rows],
    ))
    fig.update_layout(
        template=TEMPLATE, height=320, margin=dict(l=40, r=10, t=30, b=30),
        title="EUR allocation per position (blue = core, orange = satellite)",
        yaxis_title="EUR",
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


# Categorical slots 1-3 (blue/orange/aqua) - validated for 3-series all-pairs use.
BACKTEST_SERIES_COLORS = ["#2a78d6", "#eb6834", "#1baf7a"]


def backtest_chart(dates: list[str], portfolio_values: list[float], benchmarks: dict) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=portfolio_values, mode="lines", name="Proposed portfolio",
                              line=dict(color=BACKTEST_SERIES_COLORS[0], width=2.5)))
    for i, (bm_ticker, bm) in enumerate(benchmarks.items()):
        fig.add_trace(go.Scatter(x=dates, y=bm["values"], mode="lines", name=bm["name"],
                                  line=dict(color=BACKTEST_SERIES_COLORS[(i + 1) % 3], width=1.5, dash="dot")))
    fig.update_layout(
        template=TEMPLATE, height=380, margin=dict(l=50, r=10, t=30, b=30),
        title="Backtest: EUR value of the proposed allocation vs. benchmarks",
        yaxis_title="EUR", legend=dict(orientation="h", y=-0.15),
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)


# Validator-checked in this exact order (SCENARIO_KEYS' fixed sequence): worst
# adjacent pair (violet<->red) clears CVD normal-vision by a wide margin. Bull/bear
# keep the intuitive status green/red; the middle three use categorical hues rather
# than reusing status "warning"/"serious" (those two read too close to each other).
SCENARIO_COLORS = {
    "bull": STATUS_GOOD,
    "base": BLUE,
    "bear": STATUS_CRITICAL,
    "rate_shock": "#4a3aa7",
    "fx_headwind": "#eda100",
}


def scenario_chart(scenario_keys: list[str], labels: list[str], ending_values: list[float], current_value: float) -> str:
    colors = [SCENARIO_COLORS.get(k, "#9e9e9e") for k in scenario_keys]
    fig = go.Figure(go.Bar(
        x=labels, y=ending_values, marker_color=colors,
        text=[f"€{v:,.0f}" for v in ending_values], textposition="outside",
    ))
    fig.add_hline(y=current_value, line_dash="dash", line_color="#52514e",
                  annotation_text="Capital invested today", annotation_position="top left")
    fig.update_layout(
        template=TEMPLATE, height=380, margin=dict(l=50, r=10, t=40, b=80),
        title="Portfolio value in 12 months, by scenario (EUR)",
        yaxis_title="EUR",
    )
    return fig.to_html(full_html=False, include_plotlyjs=False)
