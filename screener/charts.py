"""Plotly figure builders. All figures share one CDN plotly.js load (in the
template head); individual figures are embedded with include_plotlyjs=False.
"""

from __future__ import annotations

import plotly.graph_objects as go

TEMPLATE = "plotly_white"

# Validated palette (see dataviz skill references/palette.md) - light-mode steps,
# used here because chart panels render on a fixed light card regardless of the
# surrounding page theme.
BLUE = "#2a78d6"
ORANGE = "#eb6834"
STATUS_GOOD = "#0ca30c"
STATUS_CRITICAL = "#d03b3b"
SECTOR_COLORS = {
    "Semiconductors": "#2a78d6",
    "Energy & Digital Infrastructure": "#eb6834",
    "AI / Enterprise Software": "#1baf7a",
    "Defence": "#eda100",
    "Consumer Goods": "#e87ba4",
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
    labels = list(sector_totals_pct.keys())
    values = list(sector_totals_pct.values())
    colors = [SECTOR_COLORS.get(label, "#9e9e9e") for label in labels]
    fig = go.Figure(go.Pie(labels=labels, values=values, hole=0.4, marker=dict(colors=colors)))
    fig.update_layout(
        template=TEMPLATE, height=360, margin=dict(l=10, r=10, t=30, b=10),
        title="Sector allocation (% of investable capital)",
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
