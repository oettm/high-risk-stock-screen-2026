"""
Qualitative moat / competitive-advantage assessments.

These are OPINION, not runtime data: grounded in publicly known business-model
characteristics, not pulled live. They are clearly badged as OPINION in the
report and are the one section of the framework that is deliberately
judgment-based, because "moat durability" is not a number any API returns.
"""

MOAT: dict[str, dict] = {
    "CRWV": {
        "source": "Early-mover scale in purpose-built AI-training cloud infrastructure, deep NVIDIA relationship (early/priority GPU access), and large multi-year contracts with anchor customers.",
        "durability": "Low-medium",
        "threats": "Hyperscalers (Microsoft, Google, Amazon, Meta) building competing in-house AI cloud capacity; thin differentiation versus other GPU-cloud specialists once supply constraints ease; heavy debt load raises refinancing/execution risk.",
    },
    "IREN": {
        "source": "Low-cost renewable power access and data-center site control built up during its Bitcoin-mining phase, now being repurposed for AI/GPU cloud hosting.",
        "durability": "Low",
        "threats": "Unproven competitive position in AI cloud versus purpose-built players (CoreWeave, Nebius) and hyperscalers; Bitcoin-mining legacy business remains exposed to crypto-price cycles; execution risk on the pivot.",
    },
    "NVDA": {
        "source": "CUDA software ecosystem lock-in, top-to-bottom AI compute stack (chips, networking via Mellanox/NVLink, software), and multi-generation lead in high-end AI accelerators.",
        "durability": "High, but narrowing",
        "threats": "Custom silicon from hyperscalers (Google TPU, AWS Trainium, Microsoft Maia), AMD's MI-series closing the gap, and China export restrictions capping the addressable market.",
    },
    "AMD": {
        "source": "Second-source credibility in CPUs/GPUs at lower cost than Intel/NVIDIA, chiplet manufacturing expertise, growing data-center GPU share.",
        "durability": "Medium",
        "threats": "NVIDIA's software moat (CUDA) limits AI GPU share gains; Intel resurgence risk in CPUs.",
    },
    "TSM": {
        "source": "Dominant leading-edge foundry (sub-3nm), enormous capex scale advantage, deep customer co-design relationships with Apple/NVIDIA/AMD.",
        "durability": "Very high",
        "threats": "Geopolitical/Taiwan concentration risk; Intel Foundry and Samsung trying to close the process-node gap with subsidies.",
    },
    "ASML.AS": {
        "source": "Sole global supplier of EUV lithography machines - a true monopoly at the leading edge, protected by multi-billion-dollar R&D and patent barriers.",
        "durability": "Very high",
        "threats": "China export controls cut off a large customer segment; long-term risk if alternative patterning technologies emerge (low probability, long horizon).",
    },
    "AVGO": {
        "source": "Custom ASIC design for hyperscaler AI accelerators, entrenched networking silicon (Jericho/Tomahawk), and VMware software cross-sell.",
        "durability": "High",
        "threats": "Customer concentration (a few hyperscalers = large % of AI revenue); enterprise software integration execution risk from the VMware deal.",
    },
    "MU": {
        "source": "One of only three global DRAM/NAND makers at scale, benefiting from AI-driven HBM memory demand.",
        "durability": "Medium",
        "threats": "Memory is a commodity, cyclical, price-war prone; Samsung/SK Hynix have comparable or better HBM technology in places.",
    },
    "ARM": {
        "source": "Architecture licensing model embedded in nearly all mobile SoCs and increasingly in data-center/PC chips; extremely high switching costs for licensees.",
        "durability": "High",
        "threats": "RISC-V open-standard architecture is a long-term structural threat to the licensing model; customer-turned-competitor dynamics (Qualcomm litigation).",
    },
    "QCOM": {
        "source": "Dominant modem/SoC IP in premium Android smartphones, broad patent portfolio (licensing revenue).",
        "durability": "Medium",
        "threats": "Apple in-house modem transition removes a major customer over time; Android OEMs developing in-house silicon (Samsung Exynos).",
    },
    "LRCX": {
        "source": "Leading position in deposition/etch equipment, tightly integrated into leading-edge fabs' process recipes.",
        "durability": "Medium-high",
        "threats": "Cyclical semiconductor capex spending; competition from Applied Materials and Tokyo Electron in overlapping tool categories.",
    },
    "BESI.AS": {
        "source": "Leading hybrid bonding / advanced packaging equipment supplier, well positioned for AI-chip packaging (CoWoS-type) demand.",
        "durability": "Medium",
        "threats": "Small-cap-style customer concentration (mainly with a handful of leading-edge packaging customers); competition from ASM International and Japanese toolmakers.",
    },
    "VST": {
        "source": "Large competitive power generation fleet (nuclear + gas) in deregulated Texas/PJM markets, direct beneficiary of data-center electricity demand.",
        "durability": "Medium",
        "threats": "Merchant power price volatility; regulatory intervention risk on data-center power deals; nuclear relicensing/operating risk.",
    },
    "CEG": {
        "source": "Largest US nuclear generation fleet - a scarce, carbon-free, 24/7 baseload asset increasingly contracted directly to hyperscalers (e.g. Microsoft PPA).",
        "durability": "High",
        "threats": "Regulatory/political risk around nuclear restart economics; long-dated capex risk on plant life extensions.",
    },
    "NEE": {
        "source": "Largest US regulated utility + renewables developer (NextEra Energy Resources), scale advantages in wind/solar project development.",
        "durability": "Medium-high",
        "threats": "Interest-rate sensitivity as a capital-intensive utility; regulatory/political risk to renewables incentives.",
    },
    "EQIX": {
        "source": "Largest global carrier-neutral data-center/interconnection network - strong network effects (more tenants attract more interconnection partners).",
        "durability": "High",
        "threats": "Power availability constraints; hyperscalers increasingly building their own data centers instead of colocating.",
    },
    "DLR": {
        "source": "Second-largest global data-center REIT, large hyperscale and enterprise tenant base, scale in land/power procurement.",
        "durability": "Medium-high",
        "threats": "Rising power/construction costs compress development yields; interest-rate sensitivity as a REIT.",
    },
    "GEV": {
        "source": "Leading grid equipment and gas-turbine manufacturer at a moment of structural under-investment reversal in grid capacity.",
        "durability": "Medium",
        "threats": "Execution risk as a recent spin-off; cyclicality of power-equipment capex; competition from Siemens Energy.",
    },
    "VRT": {
        "source": "Leading supplier of data-center power/thermal management (liquid cooling), direct beneficiary of AI rack power-density increases.",
        "durability": "Medium",
        "threats": "Competition from Schneider Electric, Eaton; customer concentration in a handful of large data-center builders.",
    },
    "ETN": {
        "source": "Broad electrical equipment portfolio benefiting from grid modernization and data-center/reshoring capex, strong distribution network.",
        "durability": "Medium-high",
        "threats": "Cyclical industrial exposure; competition from Schneider Electric and ABB.",
    },
    "PWR": {
        "source": "Largest specialty electrical/grid infrastructure contractor in North America, deep skilled-labor and permitting relationships.",
        "durability": "Medium",
        "threats": "Labor-intensive, thin-margin contracting model; project execution/weather risk.",
    },
    "IBE.MC": {
        "source": "One of the largest global renewables + regulated-network utilities, geographically diversified (Spain, UK, US, Brazil).",
        "durability": "Medium-high",
        "threats": "Regulatory/tariff risk across multiple jurisdictions; high capex/leverage sensitivity to interest rates.",
    },
    "MSFT": {
        "source": "Enterprise software lock-in (Office/Windows/Azure AD), Azure cloud scale, OpenAI partnership giving early enterprise AI distribution via Copilot.",
        "durability": "Very high",
        "threats": "Cloud capex intensity pressures near-term margins; antitrust/regulatory scrutiny of AI partnerships.",
    },
    "GOOGL": {
        "source": "Search distribution + advertising data scale, in-house TPU silicon reducing AI infrastructure costs, YouTube and Cloud growth.",
        "durability": "High",
        "threats": "Generative-AI answer engines could erode search-query volume/monetization over time; ongoing antitrust remedies.",
    },
    "PLTR": {
        "source": "Deep, sticky government/defense data-integration contracts (Gotham) plus growing commercial AI platform (Foundry/AIP) adoption.",
        "durability": "Medium",
        "threats": "Premium valuation leaves little room for growth disappointment; government-contract concentration and political/budget risk.",
    },
    "CRWD": {
        "source": "Cloud-native endpoint security platform with strong land-and-expand economics and a unified agent/data model (Falcon).",
        "durability": "Medium-high",
        "threats": "Intensely competitive cybersecurity market (SentinelOne, Microsoft Defender bundling); reputational risk from any major outage/incident.",
    },
    "SNOW": {
        "source": "Cloud data-warehouse/lakehouse platform with strong multi-cloud neutrality and consumption-based expansion within existing customers.",
        "durability": "Medium",
        "threats": "Databricks is a well-funded direct competitor; hyperscaler-native data platforms (Redshift, BigQuery) compete on price/integration.",
    },
    "NOW": {
        "source": "Entrenched enterprise workflow platform (ITSM) with high switching costs, expanding into broader AI-driven process automation.",
        "durability": "High",
        "threats": "Premium valuation; competition from point solutions and Microsoft/SAP platform bundling.",
    },
    "ORCL": {
        "source": "Entrenched enterprise database installed base plus a fast-growing cloud-infrastructure (OCI) business increasingly used for AI training capacity.",
        "durability": "Medium-high",
        "threats": "Heavy debt-funded capex buildout for OCI; execution risk against AWS/Azure/GCP scale.",
    },
    "ANET": {
        "source": "High-performance cloud/AI networking switches with a software-driven (EOS) architecture favored by hyperscalers and AI clusters.",
        "durability": "Medium-high",
        "threats": "Customer concentration in a few hyperscalers; Cisco and white-box networking competition.",
    },
    "DELL": {
        "source": "Scale server/infrastructure manufacturer with a growing AI-server backlog and direct enterprise sales relationships.",
        "durability": "Medium",
        "threats": "Low-margin, highly competitive hardware business; customer concentration risk in large AI server deals.",
    },
    "SMCI": {
        "source": "Fast time-to-market AI server/rack integration, close design partnership with NVIDIA on reference architectures.",
        "durability": "Low-medium",
        "threats": "Thin margins, customer/component concentration, and a history of accounting-control and governance concerns that materially raise idiosyncratic risk.",
    },
    "LMT": {
        "source": "Prime contractor on multi-decade defense programs (F-35), extremely high switching costs and program lock-in with the US government.",
        "durability": "Very high",
        "threats": "Program cost-overrun/schedule risk (F-35 sustainment costs); US defense budget political risk.",
    },
    "RTX": {
        "source": "Diversified defense/aerospace prime plus large commercial jet-engine aftermarket (Pratt & Whitney) annuity-like revenue.",
        "durability": "High",
        "threats": "Geared Turbofan engine durability/recall issues have been a recurring execution risk; commercial aerospace cyclicality.",
    },
    "NOC": {
        "source": "Prime contractor on strategic/classified programs (B-21 bomber, space systems) with very high barriers to entry.",
        "durability": "Very high",
        "threats": "Fixed-price development program cost-overrun risk; budget concentration in a handful of large programs.",
    },
    "GD": {
        "source": "Leading submarine/combat-ship builder (Electric Boat) and business-jet franchise (Gulfstream) - both high-switching-cost franchises.",
        "durability": "High",
        "threats": "Shipbuilding execution/labor-capacity constraints; business-jet cyclicality.",
    },
    "LHX": {
        "source": "Entrenched defense electronics/communications supplier across many platforms, benefiting from post-merger scale (L3+Harris).",
        "durability": "Medium-high",
        "threats": "Integration risk from the merger; smaller scale than the largest primes.",
    },
    "KTOS": {
        "source": "Niche low-cost unmanned/attritable drone and hypersonics-testing systems provider aligned with modern attritable-warfare defense doctrine.",
        "durability": "Medium",
        "threats": "Small-cap execution and contract-timing risk; unproven at large-scale production volumes versus legacy primes.",
    },
    "RHM.DE": {
        "source": "Leading European land-systems/ammunition manufacturer, direct beneficiary of European rearmament and Ukraine-related orders.",
        "durability": "Medium-high",
        "threats": "Order book highly dependent on continued European defense-spending political will; capacity ramp execution risk.",
    },
    "BA.L": {
        "source": "UK's largest defense prime with deep, multi-decade programs across air, sea, land, and cyber, plus significant US business (BAE Systems Inc.).",
        "durability": "High",
        "threats": "UK/European budget risk; large program execution risk (e.g. submarines).",
    },
    "LDO.MI": {
        "source": "Italy's leading aerospace/defense/electronics group with growing European joint-program exposure (e.g. GCAP fighter program).",
        "durability": "Medium-high",
        "threats": "State-influenced ownership/governance considerations; execution risk on multinational joint programs.",
    },
    "HII": {
        "source": "Sole builder of US Navy nuclear-powered aircraft carriers and a lead submarine builder - effectively irreplaceable strategic capacity.",
        "durability": "Very high",
        "threats": "Shipyard labor-capacity constraints have caused chronic schedule slippage; single-customer (US Navy) concentration.",
    },
    "PG": {
        "source": "Portfolio of category-leading household/personal-care brands, massive scale in advertising and retail-shelf-space negotiation.",
        "durability": "High",
        "threats": "Private-label competition; slow structural growth in developed staples markets.",
    },
    "KO": {
        "source": "World's largest beverage brand/distribution network, asset-light bottler franchise model.",
        "durability": "Very high",
        "threats": "Structural decline in sugary-drink consumption in developed markets; input-cost (aluminum, sugar) inflation.",
    },
    "PEP": {
        "source": "Diversified beverage + snacks (Frito-Lay) portfolio with strong route-to-market/distribution scale.",
        "durability": "High",
        "threats": "GLP-1 weight-loss drugs are a debated long-term demand risk for snacking/soda volumes; input-cost inflation.",
    },
    "NKE": {
        "source": "Strongest global sportswear brand with direct-to-consumer scale and athlete/franchise marketing lock-in.",
        "durability": "Medium-high",
        "threats": "Market-share losses to On, Hoka, and adidas resurgence; DTC-transition execution has been rocky recently.",
    },
    "MDLZ": {
        "source": "Global #1 in biscuits/chocolate with strong emerging-market distribution scale (Cadbury, Oreo, Milka).",
        "durability": "High",
        "threats": "Cocoa-price inflation has pressured margins severely; GLP-1 demand-risk debate similar to other snack names.",
    },
    "EL": {
        "source": "Prestige beauty brand portfolio (Estee Lauder, Clinique, La Mer) with strong travel-retail/duty-free distribution.",
        "durability": "Medium",
        "threats": "Heavy China/travel-retail dependence has driven a multi-year earnings reset; brand relevance risk versus indie beauty brands.",
    },
    "CL": {
        "source": "Global #1 in toothpaste/oral care with very high emerging-market distribution penetration.",
        "durability": "High",
        "threats": "Private-label and regional-brand competition in price-sensitive emerging markets; slow developed-market volume growth.",
    },
    "MC.PA": {
        "source": "World's largest luxury group by far, with a portfolio of irreplaceable heritage maisons (Louis Vuitton, Dior) and full control of distribution.",
        "durability": "Very high",
        "threats": "Chinese/Asian luxury demand cyclicality; aspirational-consumer pullback risk in a downturn.",
    },
    "NESN.SW": {
        "source": "World's largest food/beverage company by revenue, extreme category and geographic diversification, strong emerging-market distribution.",
        "durability": "High",
        "threats": "Structural volume growth has slowed; portfolio complexity has weighed on execution/margin in recent years.",
    },
    "OR.PA": {
        "source": "World's largest cosmetics group with a multi-tier brand portfolio (luxury to mass) and heavy, effective R&D/marketing reinvestment.",
        "durability": "High",
        "threats": "China beauty-market slowdown; intensifying competition from indie/DTC beauty brands online.",
    },
}
