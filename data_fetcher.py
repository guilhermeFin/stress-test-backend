import asyncio
import logging
import time
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import yfinance as yf
from fredapi import Fred

from config import FRED_API_KEY

logger = logging.getLogger(__name__)

SECTOR_MAP = {
    'TLT': 'Fixed Income',
    'BND': 'Fixed Income',
    'AGG': 'Fixed Income',
    'IEF': 'Fixed Income',
    'SHV': 'Fixed Income',
    'BIL': 'Fixed Income',
    'GLD': 'Commodity',
    'SLV': 'Commodity',
    'USO': 'Commodity',
    'DJP': 'Commodity',
    'SPY': 'Broad Market',
    'QQQ': 'Broad Market',
    'IWM': 'Broad Market',
    'VTI': 'Broad Market',
    'DIA': 'Broad Market',
    'VOO': 'Broad Market',
    'SCHD': 'Broad Market',
    'VYM': 'Broad Market',
}

def _fetch_single_ticker(ticker: str) -> tuple[str, dict]:
    t0 = time.perf_counter()
    try:
        stock = yf.Ticker(ticker)
        hist  = stock.history(period='1y')
        info  = stock.info

        daily_returns = hist['Close'].pct_change().dropna()

        data = {
            'current_price': round(float(hist['Close'].iloc[-1]), 2),
            'daily_returns': daily_returns.tolist(),
            'beta':          info.get('beta', 1.0),
            'sector':        info.get('sector') or SECTOR_MAP.get(ticker.upper(), 'Unknown'),
            'market_cap':    info.get('marketCap', 0),
            'name':          info.get('longName', ticker),
        }
        logger.info('yfinance %s fetched in %.2fs', ticker, time.perf_counter() - t0)
        return ticker, data
    except Exception as exc:
        logger.warning('yfinance %s failed in %.2fs: %s', ticker, time.perf_counter() - t0, exc)
        return ticker, {
            'current_price': 100.0,
            'daily_returns': [],
            'beta':          1.0,
            'sector':        SECTOR_MAP.get(ticker.upper(), 'Unknown'),
            'market_cap':    0,
            'name':          ticker,
        }

async def fetch_live_data(tickers: list) -> dict:
    max_workers = min(len(tickers), 10)
    loop = asyncio.get_running_loop()

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        tasks = [
            loop.run_in_executor(pool, _fetch_single_ticker, ticker)
            for ticker in tickers
        ]
        pairs = await asyncio.gather(*tasks)

    return dict(pairs)

async def fetch_macro_data() -> dict:
    if not FRED_API_KEY:
        logger.warning('FRED_API_KEY not set — macro data unavailable')
        return {}
    try:
        def _fetch():
            fred = Fred(api_key=FRED_API_KEY)
            return {
                'fed_funds_rate': float(fred.get_series('FEDFUNDS').iloc[-1]),
                'cpi_yoy':        float(fred.get_series('CPIAUCSL').pct_change(12).iloc[-1] * 100),
                'unemployment':   float(fred.get_series('UNRATE').iloc[-1]),
            }
        return await asyncio.to_thread(_fetch)
    except Exception as exc:
        logger.warning('FRED fetch failed: %s', exc)
        return {}
