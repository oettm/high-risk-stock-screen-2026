"""
Dark-theme Plotly figure builders for the Bloomberg-style holdings dashboard
(docs/dashboard.html). Kept separate from charts.py because that module's
figures render on the light report cards regardless of page theme; these
render on the dashboard's fixed dark background, so they need their own
template/background and, for the per-ticker donut, a stable qualitative
palette (charts.py's SECTOR_COLORS is keyed by sector, not ticker).
"""

from __future__ import annotations

import plotly.graph_objects as go

from screener.charts import STATUS_GOOD, STATUS_CRITICAL

DARK_TEMPLATE = "plotly_dark"
DARK_BG = "#0a0e14"
DARK_GRID = "#1c2230"
AMBER = "#f0b95a"
CYAN = "#4fc3f7"

# Same categorical hues used elsewhere in the project (sector pie, scenario
# chart), reassigned per-ticker. Sorting tickers alphabetically before
# assigning keeps colors stable week to week even if the holdings dict's
# insertion order changes.
QUALITATIVE_PALETTE = ["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4", "#4a3aa7", "#5ec8d8", "#c96b6b"]


def ticker_colors(tickers: list[str]) -> dict[str, str]:
    ordered = sorted(tickers)
    return {t: QUALITATIVE_PALETTE[i % len(QUALITATIVE_PALETTE)] for i, t in enumerate(ordered)}


def _dark_layout(fig: go.Figure, **kwargs) -> go.Figure:
    fig.update_layout(
        template=DARK_TEMPLATE,
        paper_bgcolor=DARK_BG,
        plot_bgcolor=DARK_BG,
        font=dict(color="#e8e6df"),
        **kwargs,
    )
    return fig


def sparkline_chart(closes: list[float]) -> str:
    """Minimal axis-free mini line chart for the position table - green if the
    shown window is up, red if down, matching the same status colors used for
    stop-loss/entry-zone bands elsewhere in the project."""
    if not closes or len(closes) < 2:
        return "<span style='color:#6b6a63;'>n/d</span>"
    color = STATUS_GOOD if closes[-1] >= closes[0] else STATUS_CRITICAL
    fig = go.Figure(go.Scatter(y=closes, mode="lines", line=dict(color=color, width=1.6)))
    fig.update_xaxes(visible=False)
    fig.update_yaxes(visible=False)
    fig.update_layout(
        template=DARK_TEMPLATE, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        height=44, width=140, margin=dict(l=0, r=0, t=2, b=2), showlegend=False,
    )
    return fig.to_html(full_html=False, include_plotlyjs=False, config={"staticPlot": True})


def weight_donut_dark(rows: list[dict]) -> str:
    colors_by_ticker = ticker_colors([r["ticker"] for r in rows])
    labels = [r["ticker"] for r in rows]
    values = [r["weight_pct"] for r in rows]
    colors = [colors_by_ticker[t] for t in labels]
    fig = go.Figure(go.Pie(
        labels=labels, values=values, hole=0.45, marker=dict(colors=colors, line=dict(color=DARK_BG, width=2)),
        textinfo="label+percent", textfont=dict(color="#e8e6df"),
    ))
    return _dark_layout(fig, height=360, margin=dict(l=10, r=10, t=30, b=10),
                         title="Peso per posizione (% valore corrente)", showlegend=False).to_html(
        full_html=False, include_plotlyjs=False)


def risk_bar_dark(rows: list[dict]) -> str:
    def color_for(rating):
        if rating is None:
            return "#4a4a44"
        if rating < 4:
            return STATUS_GOOD
        if rating < 7:
            return AMBER
        return STATUS_CRITICAL

    ordered = sorted(rows, key=lambda r: (r["risk_rating"] or 0))
    fig = go.Figure(go.Bar(
        x=[r["risk_rating"] for r in ordered], y=[r["ticker"] for r in ordered], orientation="h",
        marker_color=[color_for(r["risk_rating"]) for r in ordered],
        text=[f"{r['risk_rating']:.1f}" if r["risk_rating"] is not None else "n/d" for r in ordered],
        textposition="outside",
    ))
    fig.update_xaxes(range=[0, 10.5], gridcolor=DARK_GRID, title="Risk rating (1-10)")
    return _dark_layout(fig, height=300, margin=dict(l=60, r=30, t=30, b=30),
                         title="Risk rating per posizione").to_html(full_html=False, include_plotlyjs=False)


BACKTEST_SERIES_COLORS_DARK = [CYAN, "#eb6834", "#1baf7a"]


def backtest_chart_dark(dates: list[str], portfolio_values: list[float], benchmarks: dict) -> str:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=portfolio_values, mode="lines", name="Portafoglio reale",
                              line=dict(color=BACKTEST_SERIES_COLORS_DARK[0], width=2.5)))
    for i, (bm_ticker, bm) in enumerate(benchmarks.items()):
        fig.add_trace(go.Scatter(x=dates, y=bm["values"], mode="lines", name=bm["name"],
                                  line=dict(color=BACKTEST_SERIES_COLORS_DARK[(i + 1) % 3], width=1.5, dash="dot")))
    fig.update_xaxes(gridcolor=DARK_GRID)
    fig.update_yaxes(gridcolor=DARK_GRID, title="EUR")
    return _dark_layout(fig, height=380, margin=dict(l=50, r=10, t=30, b=30),
                         title="Backtest: valore EUR del portafoglio reale vs benchmark",
                         legend=dict(orientation="h", y=-0.15)).to_html(full_html=False, include_plotlyjs=False)


SCENARIO_COLORS_DARK = {
    "bull": STATUS_GOOD, "base": CYAN, "bear": STATUS_CRITICAL,
    "rate_shock": "#7a6ae0", "fx_headwind": AMBER,
}


def portfolio_evolution_chart_dark(dates: list[str], values: list[float], cost_basis_eur: float | None) -> str:
    """Real week-over-week portfolio value from data/dashboard_history.json -
    not the hindsight backtest. Starts as a single point on the first run and
    grows one point per week; a flat reference line marks total cost basis
    once the user has supplied entry prices (screener.dashboard's P&L)."""
    fig = go.Figure(go.Scatter(x=dates, y=values, mode="lines+markers", name="Valore portafoglio",
                                line=dict(color=CYAN, width=2.5), marker=dict(size=6)))
    if cost_basis_eur is not None:
        fig.add_hline(y=cost_basis_eur, line_dash="dash", line_color="#9c9a90",
                       annotation_text="Costo di carico totale", annotation_position="bottom left")
    fig.update_xaxes(gridcolor=DARK_GRID)
    fig.update_yaxes(gridcolor=DARK_GRID, title="EUR")
    return _dark_layout(fig, height=340, margin=dict(l=50, r=10, t=30, b=30),
                         title="Evoluzione del portafoglio (valore reale settimanale)").to_html(
        full_html=False, include_plotlyjs=False)


def stock_price_chart_dark(ticker: str, dates, closes: list[float], ma50, entry_low, entry_high,
                            stop_loss, currency: str) -> str:
    if closes is None or len(closes) == 0:
        return "<p class='muted'>Nessuno storico prezzi disponibile.</p>"
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dates, y=closes, mode="lines", name="Close", line=dict(color=CYAN, width=1.6)))
    if entry_low is not None and entry_high is not None:
        fig.add_hrect(y0=entry_low, y1=entry_high, fillcolor=STATUS_GOOD, opacity=0.15, line_width=0,
                      annotation_text="Zona di ingresso", annotation_position="top left")
    if stop_loss is not None:
        fig.add_hline(y=stop_loss, line_dash="dash", line_color=STATUS_CRITICAL,
                       annotation_text="Stop-loss", annotation_position="bottom left")
    fig.update_xaxes(gridcolor=DARK_GRID)
    fig.update_yaxes(gridcolor=DARK_GRID, title=currency)
    return _dark_layout(fig, height=300, margin=dict(l=45, r=10, t=35, b=30),
                         title=f"{ticker} - prezzo, zona di ingresso e stop-loss").to_html(
        full_html=False, include_plotlyjs=False)


def scenario_chart_dark(scenario_keys: list[str], labels: list[str], ending_values: list[float], current_value: float) -> str:
    colors = [SCENARIO_COLORS_DARK.get(k, "#9e9e9e") for k in scenario_keys]
    fig = go.Figure(go.Bar(
        x=labels, y=ending_values, marker_color=colors,
        text=[f"€{v:,.0f}" for v in ending_values], textposition="outside",
    ))
    fig.add_hline(y=current_value, line_dash="dash", line_color="#9c9a90",
                  annotation_text="Valore corrente", annotation_position="top left")
    fig.update_xaxes(gridcolor=DARK_GRID)
    fig.update_yaxes(gridcolor=DARK_GRID, title="EUR")
    return _dark_layout(fig, height=380, margin=dict(l=50, r=10, t=40, b=80),
                         title="Valore del portafoglio a 12 mesi, per scenario").to_html(
        full_html=False, include_plotlyjs=False)
