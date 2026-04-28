"""
brazil_data.py — Brazilian financial data module for PortfolioStress
---------------------------------------------------------------------
Handles:
  - B3 ticker normalization  (PETR4 → PETR4.SA)
  - BCB public API           (CDI, SELIC, IPCA, PTAX) — no API key
  - BRL/USD rate             (yfinance primary, BCB PTAX fallback)
  - Ibovespa history         (^BVSP via yfinance)
  - Fixed income estimation  (CDI-based returns for CDB/LCI/LCA/Tesouro)
"""

import asyncio
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from typing import Optional

import pandas as pd
import requests
import yfinance as yf

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BCB (Banco Central do Brasil) series codes — public API, no key required
# ---------------------------------------------------------------------------
BCB_SERIES = {
    "cdi_daily":     12,    # CDI daily rate (%)
    "selic_daily":   11,    # SELIC daily rate (%)
    "ipca_monthly":  433,   # IPCA monthly inflation (%)
    "usd_brl_ptax":  1,     # USD/BRL PTAX official rate
    "igpm_monthly":  189,   # IGP-M monthly (%)
}

BCB_URL = (
    "https://api.bcb.gov.br/dados/serie/bcdata.sgs.{series}"
    "/dados/ultimos/{n}?formato=json"
)

# ---------------------------------------------------------------------------
# Ticker helpers
# ---------------------------------------------------------------------------

# B3 pattern: 4 uppercase letters + 1-2 digits  (e.g. PETR4, HGLG11)
_B3_RE = re.compile(r"^[A-Z]{4}\d{1,2}$")


def normalize_b3_ticker(ticker: str) -> str:
    """
    Add .SA suffix if the ticker looks like a B3 stock and doesn't already have it.
    PETR4 → PETR4.SA   |   PETR4.SA → PETR4.SA   |   AAPL → AAPL
    """
    t = ticker.strip().upper()
    if t.endswith(".SA"):
        return t
    if _B3_RE.match(t):
        return f"{t}.SA"
    return t


def is_b3_ticker(ticker: str) -> bool:
    """Return True if the ticker looks like a Brazilian B3 stock."""
    return _B3_RE.match(ticker.strip().upper().replace(".SA", "")) is not None


# ---------------------------------------------------------------------------
# BCB API
# ---------------------------------------------------------------------------

def fetch_bcb_series(series_code: int, n_periods: int = 252) -> pd.DataFrame:
    """
    Pull a BCB time-series.  Returns DataFrame with columns:
      data  (datetime)  |  valor  (float)
    Returns empty DataFrame on error — callers must handle gracefully.
    """
    url = BCB_URL.format(series=series_code, n=n_periods)
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        df = pd.DataFrame(resp.json())
        df["data"]  = pd.to_datetime(df["data"],  format="%d/%m/%Y")
        df["valor"] = pd.to_numeric(df["valor"],  errors="coerce")
        return df.dropna().reset_index(drop=True)
    except Exception as exc:
        logger.error("BCB API error series=%s: %s", series_code, exc)
        return pd.DataFrame(columns=["data", "valor"])


# ---------------------------------------------------------------------------
# Rate helpers
# ---------------------------------------------------------------------------

def get_cdi_rate() -> float:
    """
    Current CDI annualised rate (% p.a.).
    Daily CDI is expressed as % per day; we compound to annual.
    Falls back to 10.5 if BCB is unreachable.
    """
    df = fetch_bcb_series(BCB_SERIES["cdi_daily"], n_periods=5)
    if df.empty:
        logger.warning("CDI unavailable — using 10.5% fallback")
        return 10.5
    daily = df["valor"].iloc[-1] / 100
    annual = ((1 + daily) ** 252 - 1) * 100
    return round(annual, 2)


def get_selic_rate() -> float:
    """Current SELIC annualised rate (% p.a.)."""
    df = fetch_bcb_series(BCB_SERIES["selic_daily"], n_periods=5)
    if df.empty:
        return 10.5
    daily = df["valor"].iloc[-1] / 100
    return round(((1 + daily) ** 252 - 1) * 100, 2)


def get_ipca_trailing_12m() -> float:
    """
    Compounded IPCA inflation over the trailing 12 months (% p.a.).
    Falls back to 4.5 if BCB is unreachable.
    """
    df = fetch_bcb_series(BCB_SERIES["ipca_monthly"], n_periods=13)
    if df.empty:
        return 4.5
    monthly = df["valor"].tail(12) / 100
    return round(((1 + monthly).prod() - 1) * 100, 2)


def get_brl_usd_rate() -> float:
    """
    Current BRL/USD spot rate (R$ per USD).
    Uses yfinance first; falls back to BCB PTAX; then hardcodes 5.20.
    """
    try:
        hist = yf.Ticker("BRL=X").history(period="5d")
        if not hist.empty:
            return round(float(hist["Close"].iloc[-1]), 4)
    except Exception as exc:
        logger.warning("yfinance BRL/USD failed: %s", exc)

    df = fetch_bcb_series(BCB_SERIES["usd_brl_ptax"], n_periods=5)
    if not df.empty:
        return round(float(df["valor"].iloc[-1]), 4)

    logger.warning("BRL/USD unavailable — using 5.20 fallback")
    return 5.20


# ---------------------------------------------------------------------------
# Market data
# ---------------------------------------------------------------------------

def get_ibovespa_history(period: str = "2y") -> pd.DataFrame:
    """Ibovespa (^BVSP) OHLCV history as a DataFrame with a 'ibovespa' column."""
    try:
        hist = yf.Ticker("^BVSP").history(period=period)
        return hist[["Close"]].rename(columns={"Close": "ibovespa"})
    except Exception as exc:
        logger.error("Ibovespa fetch failed: %s", exc)
        return pd.DataFrame()


def get_b3_price_history(tickers: list[str], period: str = "2y") -> pd.DataFrame:
    """
    Price history for a list of B3 tickers (auto-normalised to .SA).
    Returns a DataFrame with one column per ticker.
    """
    normalised = [normalize_b3_ticker(t) for t in tickers]
    try:
        raw = yf.download(normalised, period=period, auto_adjust=True, progress=False)
        if len(normalised) == 1:
            return raw[["Close"]].rename(columns={"Close": normalised[0]})
        return raw["Close"] if "Close" in raw.columns.get_level_values(0) else raw
    except Exception as exc:
        logger.error("B3 price fetch failed %s: %s", tickers, exc)
        return pd.DataFrame()


# ---------------------------------------------------------------------------
# Fixed income estimation
# ---------------------------------------------------------------------------

_COMMODITY_TICKERS = {
    "PETR4", "PETR3", "VALE3", "VALE5", "CSNA3", "GGBR4",
    "SUZB3", "KLBN11", "FIBR3", "BRAP4", "CMIN3",
}
_FINANCIAL_TICKERS = {
    "ITUB4", "ITUB3", "BBDC4", "BBDC3", "BBAS3",
    "SANB11", "B3SA3", "BPAC11", "ABCB4", "BRSR6",
}


def estimate_fixed_income_return(
    asset_type: str,
    spread_over_cdi: float = 0.0,
    cdi_rate: Optional[float] = None,
) -> float:
    """
    Estimate annual expected return for a Brazilian fixed income instrument.

    asset_type options:
        cdi | cdb | lci | lca | tesouro_selic | tesouro_ipca | debenture | fii

    spread_over_cdi: extra spread in percentage points (e.g. 1.5 means CDI+1.5%)
    """
    if cdi_rate is None:
        cdi_rate = get_cdi_rate()

    mapping = {
        "cdi":           cdi_rate,
        "cdb":           cdi_rate * 1.02 + spread_over_cdi,   # typical 102% CDI
        "lci":           cdi_rate * 0.93,                      # tax-free, issued at ~93%
        "lca":           cdi_rate * 0.93,
        "tesouro_selic": cdi_rate * 0.99,
        "tesouro_ipca":  get_ipca_trailing_12m() + 6.0,        # real yield ~6%
        "debenture":     cdi_rate + 2.0 + spread_over_cdi,
        "fii":           8.0,                                   # typical FII dividend yield
    }
    return round(mapping.get(asset_type.lower(), cdi_rate), 2)


# ---------------------------------------------------------------------------
# Portfolio currency classifier
# ---------------------------------------------------------------------------

def classify_portfolio_currency(positions: list[dict]) -> dict:
    """
    Given a list of positions (each with 'ticker', 'value', 'asset_type', 'currency'),
    split the portfolio into BRL vs USD exposure buckets.
    """
    fi_types = {"cdb", "lci", "lca", "tesouro_selic", "tesouro_ipca",
                "debenture", "cdi", "fii"}

    brl_value = usd_value = 0.0
    b3_positions, intl_positions, fi_positions = [], [], []

    for pos in positions:
        ticker     = pos.get("ticker", "")
        value      = float(pos.get("value", 0))
        asset_type = pos.get("asset_type", "equity").lower()
        currency   = pos.get("currency", "USD").upper()

        if asset_type in fi_types or currency == "BRL":
            brl_value += value
            (fi_positions if asset_type in fi_types else b3_positions).append(pos)
        elif is_b3_ticker(ticker):
            brl_value += value
            b3_positions.append(pos)
        else:
            usd_value += value
            intl_positions.append(pos)

    total = brl_value + usd_value or 1  # avoid div/0
    return {
        "total_value":             total,
        "brl_value":               brl_value,
        "usd_value":               usd_value,
        "brl_pct":                 round(brl_value / total * 100, 1),
        "usd_pct":                 round(usd_value / total * 100, 1),
        "b3_positions":            b3_positions,
        "international_positions": intl_positions,
        "fixed_income_positions":  fi_positions,
    }


# ---------------------------------------------------------------------------
# Async market summary
# ---------------------------------------------------------------------------

async def get_brazil_market_summary() -> dict:
    """
    Fetch CDI, SELIC, IPCA, BRL/USD, and Ibovespa YTD concurrently.
    Safe to cache for 5 minutes (matches the existing cache TTL pattern).
    """
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor(max_workers=4) as pool:
        cdi, selic, ipca, brl_usd = await asyncio.gather(
            loop.run_in_executor(pool, get_cdi_rate),
            loop.run_in_executor(pool, get_selic_rate),
            loop.run_in_executor(pool, get_ipca_trailing_12m),
            loop.run_in_executor(pool, get_brl_usd_rate),
        )

    ibov_ytd = 0.0
    ibov_hist = get_ibovespa_history(period="1y")
    if not ibov_hist.empty:
        this_year = ibov_hist[ibov_hist.index.year == datetime.now().year]
        if len(this_year) >= 2:
            ibov_ytd = round(
                (this_year["ibovespa"].iloc[-1] / this_year["ibovespa"].iloc[0] - 1) * 100, 2
            )

    return {
        "cdi_annual_pct":        cdi,
        "selic_annual_pct":      selic,
        "ipca_trailing_12m_pct": ipca,
        "brl_per_usd":           brl_usd,
        "ibovespa_ytd_pct":      ibov_ytd,
        "timestamp":             datetime.utcnow().isoformat(),
    }
