#!/usr/bin/env python3
"""
Standalone single-stock deep-dive report on Sanofi (SAN.PA): business
overview, 5-year price history with the major declines annotated (each
cause researched and sourced, not guessed), financial solidity, growth
projections, active pipeline, and a valuation against a DEDICATED
pharmaceutical peer group (not the "Consumer Goods" bucket used for
Sanofi in the two portfolio reports, which was a disclosed simplification
appropriate there but not for a report whose whole point is getting the
valuation right).

Run: python sanofi_deep_dive.py
Output: docs/sanofi-deep-dive.html
"""

from __future__ import annotations

import datetime as dt
from pathlib import Path

from screener.config import Instrument, SECTOR_CONSUMER
from screener.business_profile import BUSINESS_PROFILE
from screener.qualitative import MOAT
from screener.stock_deep_dive import build_deep_dive_context
from screener.report import render_report

ROOT = Path(__file__).parent
DOCS_DIR = ROOT / "docs"

TICKER_INSTRUMENT = Instrument("SAN.PA", "Sanofi SA", SECTOR_CONSUMER, "Euronext Paris", "EUR")

# Real pharmaceutical majors - a genuine peer group for valuation, unlike the
# Consumer Goods bucket used for SAN.PA in the two portfolio reports.
PEER_TICKERS = ["NVO", "AZN", "MRK", "LLY", "NOVN.SW", "PFE", "BMY", "GSK", "ABBV", "JNJ"]

# Each event researched via web search on the actual date of the largest 5y
# single-day moves (identified from live price history), sourced in
# README/report text. "y" is filled in automatically from the price series.
DECLINE_EVENTS = [
    {
        "date": "2022-08-10", "direction": "down",
        "label": "-8.2%: paura litigation Zantac (nota Morgan Stanley,\nstima passivita' settore $10.5-45mld)",
    },
    {
        "date": "2023-10-27", "direction": "down",
        "label": "-18.9% (record): abbandonato target margine 32% 2025,\nannuncio spin-off Opella per investire in R&D immunologia",
    },
    {
        "date": "2025-04-09", "direction": "down",
        "label": "-6.9%: minaccia dazi USA su farmaci (Trump),\nselloff settoriale, non specifico Sanofi",
    },
    {
        "date": "2025-09-04", "direction": "down",
        "label": "-8.3%: trial Fase 3 amlitelimab (eczema) sotto le attese\ndegli analisti pur avendo centrato gli endpoint",
    },
    {
        "date": "2026-07-30", "direction": "down",
        "label": "-9.0%: nuova CEO ammette \"decisioni poco disciplinate\"\nin R&D, stop a 3 programmi, nonostante utili sopra attese",
    },
]

# OPINION content - grounded in a live web search on Sanofi's disclosed
# late-stage pipeline (year-end 2025 pipeline review, ATS 2025/2026 press
# releases), not invented. Distinguishes active/promising programs from the
# discontinued ones already covered in DECLINE_EVENTS, for balance.
PIPELINE_PROJECTS = [
    {
        "name": "Dupixent (dupilumab) - espansione indicazioni", "status": "Attivo, in crescita",
        "detail": "Approvato per BPCO (studio di conferma Fase 3 NOTUS, pubblicato su NEJM) - un'espansione "
                   "enorme del mercato indirizzabile oltre le indicazioni originali (dermatite atopica, asma, "
                   "poliposi nasale). Approvato anche per rinosinusite fungina allergica (AFRS) nel 2025. "
                   "E' il principale motore di crescita del gruppo.",
    },
    {
        "name": "Rilzabrutinib (inibitore BTK)", "status": "Attivo, multi-indicazione",
        "detail": "Approvato negli USA e UE nel 2025 per la trombocitopenia immune (ITP). In corso lo studio di "
                   "Fase 3 RILIEF per la malattia IgG4-correlata (designazione orphan drug in Giappone) e uno "
                   "studio di Fase 2 per l'asma moderata-severa, dove potrebbe diventare il primo trattamento "
                   "orale avanzato della categoria.",
    },
    {
        "name": "ALTUVIIIO (emofilia)", "status": "Attivo, gia' blockbuster",
        "detail": "Ha raggiunto status blockbuster nel 2025 (~EUR 1,16 mld di vendite) - un secondo vero motore "
                   "di crescita oltre Dupixent, non ancora pienamente scontato dal mercato secondo alcuni analisti.",
    },
    {
        "name": "Tolebrutinib (sclerosi multipla) - INTERROTTO", "status": "Fallito (2025)",
        "detail": "Impairment di EUR 1,66 mld dopo il fallimento dello studio di Fase 3 PERSEUS nella SM "
                   "primariamente progressiva e una Complete Response Letter della FDA per la forma secondariamente "
                   "progressiva non-attiva. Il piu' grande smacco di pipeline recente.",
    },
    {
        "name": "Amlitelimab, itepekimab, balinatunfib (immunologia) - INTERROTTI", "status": "Fallito (2025-2026)",
        "detail": "Tutti e tre interrotti dopo readout deludenti - oltre EUR 1 mld di impairment nel Q2 2025. "
                   "Motivo diretto del crollo del 30 luglio 2026 e della dichiarazione della CEO su \"decisioni "
                   "poco disciplinate\" in R&D.",
    },
]


def main() -> None:
    run_started = dt.datetime.now(dt.timezone.utc)
    print(f"[{run_started.isoformat(timespec='seconds')}] Building Sanofi deep-dive report...")
    print(f"Peer group: {PEER_TICKERS}")

    context = build_deep_dive_context(
        TICKER_INSTRUMENT, PEER_TICKERS, DECLINE_EVENTS, PIPELINE_PROJECTS,
        BUSINESS_PROFILE.get("SAN.PA", {}), MOAT.get("SAN.PA", {}), run_started,
    )

    out_path = DOCS_DIR / "sanofi-deep-dive.html"
    render_report(context, out_path, template_name="stock_deep_dive_template.html")
    print(f"Report written to {out_path}")
    print(f"Price: {context['price_native']} {context['currency']}  |  "
          f"Method A bull/bear: {context['price_targets']['multiples'].get('bull_price')}/"
          f"{context['price_targets']['multiples'].get('bear_price')}  |  "
          f"Analyst mean target: {context['analyst'].get('target_mean')}")
    print("Done.")


if __name__ == "__main__":
    main()
