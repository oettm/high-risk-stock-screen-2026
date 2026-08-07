"""
Business/company overview per stock: what the business does, its main
business units/segments, who its customers are, and its main business
risks (distinct from the competitive-moat threats in qualitative.py).

Like MOAT in qualitative.py, this is OPINION/reference content compiled from
publicly known business characteristics - not pulled from the live data feed.
Only covers names that have appeared in the selected top-10 (not the full
50-name universe) - if a future run selects a name not covered here, the
report falls back to "N/A" rather than inventing a profile.
"""

BUSINESS_PROFILE: dict[str, dict] = {
    "NVDA": {
        "summary": "Designs GPUs and full-stack AI compute systems (chips, networking, software) for data centers, gaming, and professional visualization.",
        "business_units": ["Data Center (AI/HPC GPUs, networking)", "Gaming (GeForce GPUs)", "Professional Visualization (RTX workstations)", "Automotive (self-driving compute platforms)", "OEM & Other"],
        "customers": "Hyperscale cloud providers (Microsoft, Google, Amazon, Meta, Oracle) and AI labs for Data Center; PC OEMs and gamers for Gaming; automakers for Automotive.",
        "key_risks": [
            "Extreme customer concentration in a handful of hyperscalers for Data Center revenue",
            "US export controls on advanced AI chips to China",
            "Supply chain dependency on TSMC for leading-edge manufacturing",
            "Cyclicality if AI capex spending slows",
        ],
    },
    "SMCI": {
        "summary": "Designs and assembles high-density servers and full-rack AI computing systems, working closely with NVIDIA on reference architectures to bring new GPU platforms to market quickly.",
        "business_units": ["Server/storage systems", "Subsystems and accessories"],
        "customers": "Cloud service providers, enterprises and AI labs needing fast access to the latest GPU server platforms.",
        "key_risks": [
            "Thin margins in a highly competitive, fast-moving hardware market",
            "Customer and component (NVIDIA GPU allocation) concentration",
            "History of accounting-control and governance concerns that raise idiosyncratic/regulatory risk",
        ],
    },
    "NOW": {
        "summary": "Provides cloud-based workflow automation software, originally for IT service management (ITSM), now expanding into HR, customer service and broader enterprise process automation with AI agents.",
        "business_units": ["IT Workflows", "Customer & Industry Workflows", "Employee Workflows", "Creator Workflows (platform/app dev)"],
        "customers": "Large enterprises across virtually every industry needing to automate internal workflows.",
        "key_risks": [
            "AI-agent disruption risk to the per-seat SaaS licensing model - the central driver of the stock's ~50% drawdown from its Jan-2025 high, sparked by fears (crystallized around Anthropic's Feb-2026 Claude Cowork launch, the market's 'SaaSpocalypse' moment) that AI agents could shrink the number of human seats software is priced on",
            "Premium valuation (P/E ~60x+ even after the drawdown) leaves little room for any further growth disappointment",
            "Guidance deceleration risk - even a beat-and-raise quarter has triggered double-digit single-day drops when forward growth guidance implies slowing subscription growth",
            "Competition from point solutions and Microsoft/SAP platform bundling",
            "Long enterprise sales and implementation cycles",
        ],
    },
    "PLTR": {
        "summary": "Builds data-integration and AI/analytics software platforms (Gotham for government/defense, Foundry for commercial enterprises), increasingly selling AI decision-support tools (AIP).",
        "business_units": ["Government (defense/intelligence contracts)", "Commercial (enterprise data platform, AIP)"],
        "customers": "US and allied government/defense/intelligence agencies; large commercial enterprises across industries (manufacturing, healthcare, energy).",
        "key_risks": [
            "Premium valuation leaves little room for growth disappointment",
            "Government-contract concentration and budget/political risk",
            "Long, complex enterprise sales cycles for commercial growth",
        ],
    },
    "AVGO": {
        "summary": "Diversified semiconductor and infrastructure software company - custom AI ASICs, networking chips, broadband/wireless components, plus enterprise software (VMware).",
        "business_units": ["Semiconductor Solutions (networking, custom AI accelerators, broadband, wireless, storage)", "Infrastructure Software (VMware, mainframe software, cybersecurity)"],
        "customers": "Hyperscalers (custom AI ASIC design partners such as Google), Apple (wireless components), enterprise IT departments (VMware).",
        "key_risks": [
            "Revenue concentration in a few large hyperscaler AI customers",
            "Integration execution risk from the VMware acquisition",
            "Apple customer concentration in the wireless segment",
        ],
    },
    "TSM": {
        "summary": "World's largest dedicated semiconductor foundry, manufacturing chips designed by other companies (fabless model) at leading-edge process nodes.",
        "business_units": ["Foundry services by node (3nm/5nm/7nm advanced nodes, mature nodes)", "Advanced packaging (CoWoS)"],
        "customers": "Apple, NVIDIA, AMD, Qualcomm, Broadcom and virtually every major fabless chip designer.",
        "key_risks": [
            "Geographic concentration in Taiwan - geopolitical/cross-strait risk",
            "Heavy capex cycle exposure",
            "Customer concentration (Apple is a very large single customer)",
            "US/China export-control exposure",
        ],
    },
    "VRT": {
        "summary": "Supplies power and thermal management equipment (including liquid cooling) for data centers, a direct beneficiary of rising AI server rack power density.",
        "business_units": ["Power (UPS, switchgear)", "Thermal (cooling systems, including liquid cooling)", "IT systems/software (racks, monitoring)"],
        "customers": "Hyperscale and colocation data-center operators, enterprise IT.",
        "key_risks": [
            "Customer concentration among a handful of large data-center builders",
            "Competition from Schneider Electric, Eaton",
            "Supply chain/component availability for rapidly scaling liquid-cooling demand",
        ],
    },
    "MU": {
        "summary": "Manufactures memory and storage chips (DRAM and NAND flash) used in servers, PCs, mobile devices, and increasingly AI accelerators (HBM).",
        "business_units": ["Compute & Networking (DRAM for servers/PCs, HBM for AI)", "Mobile", "Storage (NAND/SSD)", "Embedded"],
        "customers": "Server OEMs and hyperscalers, smartphone makers, PC OEMs, automotive/industrial customers.",
        "key_risks": [
            "Highly cyclical, commodity-like pricing for memory",
            "Capital-intensive with large capex swings",
            "Competition from Samsung and SK Hynix",
            "China market-access restrictions",
        ],
    },
    "PWR": {
        "summary": "Largest specialty contractor building and maintaining electrical transmission, renewable energy, and telecom infrastructure in North America.",
        "business_units": ["Electric Power", "Renewable Energy", "Underground Utility & Infrastructure", "Communications"],
        "customers": "Utilities, renewable energy developers, telecom companies, government infrastructure programs.",
        "key_risks": [
            "Thin-margin, labor-intensive contracting model",
            "Weather and permitting delays on large projects",
            "Skilled-labor availability constraints",
            "Project cost-overrun risk on fixed-price contracts",
        ],
    },
    "RHM.DE": {
        "summary": "Germany's leading land-systems and ammunition manufacturer (tanks, armored vehicles, munitions), a direct beneficiary of European rearmament following Russia's invasion of Ukraine.",
        "business_units": ["Vehicle Systems (armored vehicles)", "Weapon and Ammunition", "Electronic Solutions", "Sensors and Actuators"],
        "customers": "German and other European militaries, Ukraine (via European government orders), NATO allies.",
        "key_risks": [
            "Order book highly dependent on continued European defense-spending political will",
            "Capacity ramp execution risk as production scales rapidly",
            "Reputational/ESG sensitivity given the sector",
        ],
    },
    "LDO.MI": {
        "summary": "Italy's leading aerospace, defense and electronics group, majority state-influenced, with growing exposure to multinational fighter-jet development programs.",
        "business_units": ["Helicopters", "Electronics, Defense & Security Systems", "Aeronautics", "Space (joint ventures)"],
        "customers": "Italian Ministry of Defence, NATO allies, export customers, joint-program partners (UK, Japan on GCAP).",
        "key_risks": [
            "State-influenced ownership/governance considerations",
            "Execution risk on multinational joint programs (GCAP)",
            "Export-approval political risk on foreign sales",
        ],
    },
    "MDLZ": {
        "summary": "Global snacking company - the world's largest maker of biscuits and chocolate (Oreo, Cadbury, Milka, Toblerone), with strong emerging-market distribution.",
        "business_units": ["Biscuits and baked snacks", "Chocolate", "Gum and candy", "Beverages (regional)"],
        "customers": "Mass retailers, convenience stores, and consumers across both developed and emerging markets.",
        "key_risks": [
            "Cocoa-price inflation has severely pressured chocolate margins",
            "GLP-1 weight-loss drug demand-risk debate similar to other snack makers",
            "Emerging-market currency volatility",
        ],
    },
}
