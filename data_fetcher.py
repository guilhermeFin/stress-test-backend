import yfinance as yf
import numpy as np
import os
from fredapi import Fred

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

def fetch_live_data(tickers: list) -> dict:
    result = {}

    for ticker in tickers:
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period='1y')
            info = stock.info

            daily_returns = hist['Close'].pct_change().dropna()

            result[ticker] = {
                'current_price': round(float(hist['Close'].iloc[-1]), 2),
                'daily_returns': daily_returns.tolist(),
                'beta': info.get('beta', 1.0),
                'sector': info.get('sector') or SECTOR_MAP.get(ticker.upper(), 'Unknown'),
                'market_cap': info.get('marketCap', 0),
                'name': info.get('longName', ticker),
            }
        except Exception as e:
            result[ticker] = {
                'current_price': 100.0,
                'daily_returns': [],
                'beta': 1.0,
                'sector': SECTOR_MAP.get(ticker.upper(), 'Unknown'),
                'market_cap': 0,
                'name': ticker,
            }

    return result

def fetch_macro_data() -> dict:
    fred = Fred(api_key=os.getenv('FRED_API_KEY'))
    return {
        'fed_funds_rate': float(fred.get_series('FEDFUNDS').iloc[-1]),
        'cpi_yoy': float(fred.get_series('CPIAUCSL').pct_change(12).iloc[-1] * 100),
        'unemployment': float(fred.get_series('UNRATE').iloc[-1]),
    }