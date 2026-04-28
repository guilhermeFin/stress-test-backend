"""
brazil_scenarios.py — Stress scenario configs for PortfolioStress
------------------------------------------------------------------
Six historically calibrated Brazilian crisis scenarios.
Each scenario defines asset-class shocks; apply_scenario_to_position()
maps those shocks to individual holdings; stress_test_portfolio() runs
the full portfolio.

Depends on: brazil_data.py  (is_b3_ticker)
"""

from dataclasses import dataclass, field
from typing import Optional
from brazil_data import is_b3_ticker

# ---------------------------------------------------------------------------
# Scenario dataclass
# ---------------------------------------------------------------------------

@dataclass
class BrazilScenario:
    id:          str
    name:        str
    year:        int
    description: str      # technical description for advisor
    narrative:   str      # plain-language for client presentation

    # Asset-class shocks — all as decimal fractions (e.g. -0.40 = -40%)
    brl_usd_shock:          float   # BRL vs USD  (negative = BRL weakens)
    ibovespa_shock:         float   # Ibovespa total return in BRL
    b3_financials_shock:    float   # Brazilian banks / financials
    b3_commodities_shock:   float   # Petrobras, Vale, miners
    cdi_spread_shock:       float   # spread widening in PERCENTAGE POINTS
    real_estate_brl_shock:  float   # Brazilian real estate in BRL
    usd_equities_shock:     float   # S&P 500 / global equities in USD
    usd_bonds_shock:        float   # IG bonds in USD
    usd_em_shock:           float   # EM equities in USD

    # Recovery
    recovery_months: int
    recovery_note:   str

    # Metadata
    severity:         int            # 1 (mild) – 5 (severe)
    correlation_note: Optional[str] = None


# ---------------------------------------------------------------------------
# Scenario definitions
# ---------------------------------------------------------------------------

BRAZIL_SCENARIOS: dict[str, BrazilScenario] = {

    "2002_lula_election": BrazilScenario(
        id    = "2002_lula_election",
        name  = "2002 — Lula Election Panic",
        year  = 2002,
        description = (
            "Markets panicked ahead of Lula's first presidential election, fearing debt default "
            "and radical economic policy. Brazil's EMBI+ country risk reached 2,400 bps. "
            "BRL lost 40% of its value. Lula moderated post-election, driving a sharp recovery."
        ),
        narrative = (
            "In a scenario like 2002, your portfolio's Brazilian holdings could fall sharply — "
            "but your USD assets would actually gain purchasing power in BRL terms as the real weakened. "
            "Investors who held through the panic recovered fully within 18 months."
        ),
        brl_usd_shock         = -0.40,
        ibovespa_shock        = -0.45,
        b3_financials_shock   = -0.50,
        b3_commodities_shock  = -0.35,
        cdi_spread_shock      =  5.00,
        real_estate_brl_shock = -0.25,
        usd_equities_shock    = -0.22,   # dot-com aftermath
        usd_bonds_shock       =  0.05,
        usd_em_shock          = -0.30,
        recovery_months = 18,
        recovery_note   = "Full recovery by mid-2004 as Lula maintained fiscal orthodoxy",
        severity         = 5,
        correlation_note = "USD assets partially buffered losses — BRL depreciation was the key risk",
    ),

    "2008_global_crisis": BrazilScenario(
        id    = "2008_global_crisis",
        name  = "2008 — Global Financial Crisis",
        year  = 2008,
        description = (
            "Lehman Brothers collapse triggered a global credit freeze. Brazil was hit by "
            "commodity price collapse, capital outflows, and a 35% BRL devaluation at the worst. "
            "Ibovespa fell 55% peak-to-trough. Brazil recovered faster than developed markets."
        ),
        narrative = (
            "The 2008 crisis hit hard but briefly — Brazil recovered within 14 months, "
            "faster than the US or Europe, helped by China's commodity demand. "
            "This scenario shows why holding some USD fixed income matters: bonds rose while everything else fell."
        ),
        brl_usd_shock         = -0.35,
        ibovespa_shock        = -0.55,
        b3_financials_shock   = -0.50,
        b3_commodities_shock  = -0.60,
        cdi_spread_shock      =  2.50,
        real_estate_brl_shock = -0.15,
        usd_equities_shock    = -0.45,
        usd_bonds_shock       =  0.08,   # flight to quality
        usd_em_shock          = -0.55,
        recovery_months = 14,
        recovery_note   = "Ibovespa recovered to pre-crisis levels by early 2010",
        severity         = 5,
        correlation_note = "All risk assets fell together — only US Treasuries provided a cushion",
    ),

    "2015_brazil_crisis": BrazilScenario(
        id    = "2015_brazil_crisis",
        name  = "2015 — Brazil Fiscal & Political Crisis",
        year  = 2015,
        description = (
            "Brazil's worst recession in a century: fiscal collapse under Dilma Rousseff, "
            "Petrobras corruption scandal (Lava Jato), credit downgrade to junk by S&P, "
            "and stagflation. BRL fell 47% for the year. GDP contracted 3.8%. "
            "US markets were largely unaffected — the crisis was purely domestic."
        ),
        narrative = (
            "This is the scenario that most clearly shows the value of offshore USD diversification. "
            "While Brazilian assets collapsed, USD-denominated portfolios held their value — "
            "and in BRL terms, a flat USD portfolio looked like a 47% gain. "
            "This is exactly why keeping money offshore makes sense."
        ),
        brl_usd_shock         = -0.47,
        ibovespa_shock        = -0.13,   # -13% in BRL; devastating in USD
        b3_financials_shock   = -0.30,
        b3_commodities_shock  = -0.40,
        cdi_spread_shock      =  2.00,
        real_estate_brl_shock = -0.20,
        usd_equities_shock    = -0.01,   # S&P 500 nearly flat that year
        usd_bonds_shock       =  0.01,
        usd_em_shock          = -0.15,
        recovery_months = 36,
        recovery_note   = "Ibovespa in USD terms took until 2019 to fully recover",
        severity         = 4,
        correlation_note = "Classic decoupling — USD assets were the safe harbour for Brazilian investors",
    ),

    "2018_election_shock": BrazilScenario(
        id    = "2018_election_shock",
        name  = "2018 — Election Uncertainty",
        year  = 2018,
        description = (
            "Market volatility surrounding Brazil's 2018 presidential election. "
            "BRL hit a record low of R$4.20/USD in September 2018. "
            "Markets were uncertain about both leading candidates. "
            "Shock was significant but short-lived once Bolsonaro's economic team was confirmed."
        ),
        narrative = (
            "A sharp but brief shock — the BRL fell 15% in the run-up to the election "
            "then rebounded quickly. Well-diversified portfolios barely noticed. "
            "This is a good example of political risk that looks scary but doesn't last."
        ),
        brl_usd_shock         = -0.15,
        ibovespa_shock        = -0.20,
        b3_financials_shock   = -0.25,
        b3_commodities_shock  = -0.15,
        cdi_spread_shock      =  1.50,
        real_estate_brl_shock = -0.08,
        usd_equities_shock    = -0.07,
        usd_bonds_shock       =  0.02,
        usd_em_shock          = -0.18,
        recovery_months = 6,
        recovery_note   = "Ibovespa rallied strongly post-election on reform optimism",
        severity         = 2,
        correlation_note = "Moderate, short-lived shock — Ibovespa ended 2018 positive in BRL terms",
    ),

    "2020_covid": BrazilScenario(
        id    = "2020_covid",
        name  = "2020 — COVID-19 Pandemic",
        year  = 2020,
        description = (
            "The pandemic triggered a global selloff compounded by Brazil-specific risks: "
            "political chaos around the COVID response, fiscal stimulus blowing out the deficit, "
            "and BRL hitting a record low of R$5.70/USD. Ibovespa fell 45% peak-to-trough. "
            "Extraordinary global monetary stimulus drove the fastest recovery in history."
        ),
        narrative = (
            "The fastest crash and recovery ever recorded. Within 6 months, most portfolios "
            "were back to pre-crisis levels. Clients who panicked and sold at the bottom locked "
            "in permanent losses. This scenario is a powerful argument for staying the course."
        ),
        brl_usd_shock         = -0.28,
        ibovespa_shock        = -0.45,
        b3_financials_shock   = -0.40,
        b3_commodities_shock  = -0.45,
        cdi_spread_shock      =  1.00,
        real_estate_brl_shock = -0.10,
        usd_equities_shock    = -0.34,
        usd_bonds_shock       =  0.08,
        usd_em_shock          = -0.32,
        recovery_months = 6,
        recovery_note   = "Global stimulus drove fastest equity market recovery in history",
        severity         = 4,
        correlation_note = "Rare case where both BRL assets and global equities fell simultaneously",
    ),

    "custom_em_crisis": BrazilScenario(
        id    = "custom_em_crisis",
        name  = "Hypothetical — EM Currency Crisis",
        year  = 2025,
        description = (
            "A forward-looking scenario: broad EM selloff triggered by USD strength, "
            "rising US rates, or a China slowdown. Parameters averaged from "
            "1994 Tequila, 1997 Asia, and 1998 Russia crises. "
            "Not a prediction — a planning benchmark."
        ),
        narrative = (
            "This isn't a prediction — it's a planning tool. "
            "We're asking: if the world looked like it did in 1998 or 1997, "
            "how would your portfolio hold up? Portfolios that survive this scenario "
            "with an acceptable outcome are well-prepared for most realistic downside cases."
        ),
        brl_usd_shock         = -0.30,
        ibovespa_shock        = -0.35,
        b3_financials_shock   = -0.38,
        b3_commodities_shock  = -0.30,
        cdi_spread_shock      =  3.00,
        real_estate_brl_shock = -0.15,
        usd_equities_shock    = -0.20,
        usd_bonds_shock       =  0.04,
        usd_em_shock          = -0.40,
        recovery_months = 24,
        recovery_note   = "Estimated based on average historical EM crisis recovery times",
        severity         = 4,
        correlation_note = "Forward-looking — severity calibrated to average of three major EM crises",
    ),
}


# ---------------------------------------------------------------------------
# Position-level stress calculator
# ---------------------------------------------------------------------------

_COMMODITY_TICKERS = {
    "PETR4", "PETR3", "VALE3", "VALE5", "CSNA3", "GGBR4",
    "SUZB3", "KLBN11", "FIBR3", "BRAP4", "CMIN3",
}
_FINANCIAL_TICKERS = {
    "ITUB4", "ITUB3", "BBDC4", "BBDC3", "BBAS3",
    "SANB11", "B3SA3", "BPAC11", "ABCB4", "BRSR6",
}
_FI_TYPES = {"cdb", "lci", "lca", "tesouro_selic", "cdi"}
_LONG_FI_TYPES = {"tesouro_ipca", "debenture"}
_EM_TICKERS = {"EEM", "VWO", "IEMG", "GMF"}


def _pick_shock(
    asset_type: str,
    ticker: str,
    scenario: BrazilScenario,
) -> float:
    """Select the appropriate shock multiplier for a position."""
    at = asset_type.lower()
    base = ticker.upper().replace(".SA", "")

    if at in _FI_TYPES:
        # Short-duration: moderate sensitivity to spread widening (~0.5yr duration)
        return -(scenario.cdi_spread_shock / 100) * 0.5

    if at in _LONG_FI_TYPES:
        # Longer duration: ~2yr sensitivity
        return -(scenario.cdi_spread_shock / 100) * 2.0

    if at == "fii":
        return scenario.real_estate_brl_shock

    if is_b3_ticker(ticker):
        if base in _COMMODITY_TICKERS:
            return scenario.b3_commodities_shock
        if base in _FINANCIAL_TICKERS:
            return scenario.b3_financials_shock
        return scenario.ibovespa_shock   # generic B3

    if base in _EM_TICKERS or "EM" in base:
        return scenario.usd_em_shock

    # Default: treat as international USD equity
    return scenario.usd_equities_shock


def apply_scenario_to_position(
    position_value:    float,
    asset_type:        str,
    ticker:            str,
    scenario:          BrazilScenario,
    is_brl_denominated: bool  = False,
    brl_usd_rate:      float = 5.20,
) -> dict:
    """
    Apply a stress scenario to a single position.

    Returns a dict with:
      original_value, stressed_value, shock_applied,
      impact_usd, impact_brl, currency
    """
    shock = _pick_shock(asset_type, ticker, scenario)
    stressed_value = position_value * (1 + shock)
    impact = stressed_value - position_value

    if is_brl_denominated:
        # Position is in BRL; convert impact to USD at stressed rate
        stressed_rate = brl_usd_rate / (1 + scenario.brl_usd_shock)  # BRL weakens → more BRL per USD
        impact_brl  = impact
        impact_usd  = impact / stressed_rate
    else:
        # Position is in USD; show BRL equivalent gain from USD appreciation
        impact_usd  = impact
        brl_multiplier = 1 / (1 + scenario.brl_usd_shock)            # BRL weakens → fewer USD per BRL
        impact_brl  = impact_usd * brl_usd_rate * brl_multiplier

    return {
        "original_value": round(position_value, 2),
        "stressed_value": round(stressed_value, 2),
        "shock_applied":  round(shock, 4),
        "impact_usd":     round(impact_usd, 2),
        "impact_brl":     round(impact_brl, 2),
        "currency":       "BRL" if is_brl_denominated else "USD",
    }


# ---------------------------------------------------------------------------
# Portfolio-level stress test
# ---------------------------------------------------------------------------

def stress_test_portfolio(
    positions:     list[dict],
    scenario_id:   str,
    brl_usd_rate:  float = 5.20,
) -> dict:
    """
    Run a full stress test on a portfolio.

    Each position dict must have:
        ticker:     str
        value:      float   (in the position's native currency)
        asset_type: str     (equity | cdb | lci | lca | tesouro_selic |
                             tesouro_ipca | debenture | cdi | fii)
        currency:   str     (USD | BRL)

    Returns full results with position-level and portfolio-level impacts.
    """
    if scenario_id not in BRAZIL_SCENARIOS:
        raise ValueError(
            f"Unknown scenario '{scenario_id}'. "
            f"Available: {list(BRAZIL_SCENARIOS.keys())}"
        )

    scenario = BRAZIL_SCENARIOS[scenario_id]

    position_results   = []
    total_original_usd = 0.0
    total_stressed_usd = 0.0

    stressed_rate = brl_usd_rate / (1 + scenario.brl_usd_shock)  # BRL weakens

    for pos in positions:
        is_brl = pos.get("currency", "USD").upper() == "BRL"
        value  = float(pos["value"])

        # Normalise to USD for portfolio totals
        value_usd = value / brl_usd_rate if is_brl else value
        total_original_usd += value_usd

        res = apply_scenario_to_position(
            position_value     = value,
            asset_type         = pos.get("asset_type", "equity"),
            ticker             = pos.get("ticker", ""),
            scenario           = scenario,
            is_brl_denominated = is_brl,
            brl_usd_rate       = brl_usd_rate,
        )

        stressed_usd = res["stressed_value"] / stressed_rate if is_brl else res["stressed_value"]
        total_stressed_usd += stressed_usd

        position_results.append({**pos, **res})

    impact_usd  = total_stressed_usd - total_original_usd
    impact_pct  = (impact_usd / total_original_usd * 100) if total_original_usd else 0.0

    total_original_brl = total_original_usd * brl_usd_rate
    total_stressed_brl = total_stressed_usd * stressed_rate

    return {
        "scenario": {
            "id":              scenario.id,
            "name":            scenario.name,
            "year":            scenario.year,
            "description":     scenario.description,
            "narrative":       scenario.narrative,
            "severity":        scenario.severity,
            "recovery_months": scenario.recovery_months,
            "recovery_note":   scenario.recovery_note,
            "correlation_note": scenario.correlation_note,
        },
        "portfolio_summary": {
            "original_value_usd":     round(total_original_usd, 2),
            "stressed_value_usd":     round(total_stressed_usd, 2),
            "impact_usd":             round(impact_usd, 2),
            "impact_pct":             round(impact_pct, 2),
            "original_value_brl":     round(total_original_brl, 2),
            "stressed_value_brl":     round(total_stressed_brl, 2),
            "brl_usd_rate_original":  brl_usd_rate,
            "brl_usd_rate_stressed":  round(stressed_rate, 4),
        },
        "positions":    position_results,
        "shocks_applied": {
            "brl_usd":        scenario.brl_usd_shock,
            "ibovespa":       scenario.ibovespa_shock,
            "cdi_spread_pts": scenario.cdi_spread_shock,
            "usd_equities":   scenario.usd_equities_shock,
        },
    }


# ---------------------------------------------------------------------------
# FastAPI router
# ---------------------------------------------------------------------------

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

brazil_router = APIRouter(tags=["brazil"])


class BrazilStressRequest(BaseModel):
    positions:    list[dict]
    scenario_id:  str
    brl_usd_rate: float = 5.20


@brazil_router.post("/stress")
async def brazil_stress(req: BrazilStressRequest):
    try:
        return stress_test_portfolio(req.positions, req.scenario_id, req.brl_usd_rate)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@brazil_router.get("/scenarios")
async def list_scenarios():
    return [
        {
            "id":       s.id,
            "name":     s.name,
            "year":     s.year,
            "severity": s.severity,
            "description": s.description,
            "narrative":   s.narrative,
            "recovery_months": s.recovery_months,
        }
        for s in BRAZIL_SCENARIOS.values()
    ]
