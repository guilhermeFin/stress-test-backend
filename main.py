import asyncio
import io
import logging
import os
import re
import time
from contextlib import asynccontextmanager
from pathlib import Path

import pandas as pd
import yfinance as yf
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from ai_explainer import generate_explanation
from config import (
    ALLOWED_EXTENSIONS,
    ALLOWED_ORIGINS,
    ANTHROPIC_API_KEY,
    MARKET_SUMMARY_TTL,
    MAX_FILE_SIZE_BYTES,
    MAX_ROWS,
    MAX_SCENARIO_LENGTH,
    PORT,
    REQUIRED_COLUMNS,
)
from brazil_data import get_brazil_market_summary
from brazil_scenarios import brazil_router, stress_test_portfolio
from data_fetcher import fetch_live_data
from report_generator import create_pdf_report
from stress_engine import parse_scenario_with_ai, run_stress_test, _safe_float

load_dotenv()

# ── Security helpers ───────────────────────────────────────────────────────────
_FORMULA_START = re.compile(r'^[=+\-@|]')
_TICKER_RE     = re.compile(r'^[\^A-Z0-9.\-]{1,12}$')


def _sanitize_df(df: pd.DataFrame) -> pd.DataFrame:
    """Strip leading formula-injection characters from all string cells."""
    for col in df.select_dtypes(include=['object', 'str']).columns:
        df[col] = df[col].map(
            lambda v: _FORMULA_START.sub('', v).strip() if isinstance(v, str) else v
        )
    return df


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-8s  %(name)s — %(message)s',
    datefmt='%H:%M:%S',
)
logger = logging.getLogger(__name__)

# ── In-memory market summary cache ────────────────────────────────────────────
_market_cache: dict = {}
_market_cache_ts: float = 0.0


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not ANTHROPIC_API_KEY:
        logger.error('ANTHROPIC_API_KEY is not set — AI features will be unavailable')
    else:
        logger.info('Anthropic API key detected')
    logger.info('PortfolioStress API ready on port %s', PORT)
    yield


app = FastAPI(title='PortfolioStress API', lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(brazil_router, prefix='/brazil')


@app.get('/health')
async def health() -> dict:
    return {'status': 'ok', 'anthropic_key': bool(ANTHROPIC_API_KEY)}


@app.post('/api/stress-test')
async def stress_test(
    file: UploadFile = File(...),
    scenario: str = Form(...),
) -> dict:
    # ── Scenario validation ────────────────────────────────────────────────────
    scenario = scenario.strip()
    if not scenario:
        raise HTTPException(status_code=400, detail='Scenario description is required')
    if len(scenario) > MAX_SCENARIO_LENGTH:
        raise HTTPException(status_code=400, detail=f'Scenario too long (max {MAX_SCENARIO_LENGTH} characters)')

    # ── File size check ────────────────────────────────────────────────────────
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail='File exceeds 10 MB limit')

    # ── Extension check ────────────────────────────────────────────────────────
    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f'Unsupported file type "{suffix}". Allowed: {", ".join(ALLOWED_EXTENSIONS)}',
        )

    # ── Parse DataFrame ────────────────────────────────────────────────────────
    try:
        if suffix == '.csv':
            df = pd.read_csv(io.BytesIO(contents))
        else:
            df = pd.read_excel(io.BytesIO(contents))
    except Exception as exc:
        logger.warning('File parse error: %s', exc)
        raise HTTPException(status_code=400, detail='Could not parse the uploaded file. Ensure it is a valid Excel or CSV.')

    df.columns = df.columns.str.lower().str.strip()

    # ── Row count cap (prevents zip-bomb / memory DoS) ─────────────────────────
    if len(df) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f'File contains too many rows (max {MAX_ROWS} positions)')

    # ── Formula injection sanitization ─────────────────────────────────────────
    df = _sanitize_df(df)

    # ── Column validation ──────────────────────────────────────────────────────
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f'Missing required column(s): {", ".join(sorted(missing))}',
        )

    tickers = df['ticker'].dropna().astype(str).str.strip().str.upper().tolist()
    tickers = [t for t in tickers if _TICKER_RE.match(t)]
    if not tickers:
        raise HTTPException(status_code=400, detail='No valid ticker symbols found in file')

    # ── Run analysis concurrently where possible ───────────────────────────────
    t0 = time.perf_counter()
    try:
        live_data, parsed_scenario = await asyncio.gather(
            fetch_live_data(tickers),
            parse_scenario_with_ai(scenario),
        )
    except Exception as exc:
        logger.error('Data fetch / scenario parse failed: %s', exc)
        raise HTTPException(status_code=502, detail='Upstream data fetch failed')

    parsed_scenario['_scenario_text'] = scenario

    try:
        results = await asyncio.to_thread(run_stress_test, df, live_data, parsed_scenario)
    except Exception as exc:
        logger.error('Stress engine failed: %s', exc)
        raise HTTPException(status_code=500, detail='Stress calculation failed')

    try:
        explanation = await generate_explanation(results, scenario)
    except Exception as exc:
        logger.error('AI explanation failed: %s', exc)
        explanation = {
            'advisor_summary':    'AI explanation unavailable.',
            'client_explanation': 'AI explanation unavailable.',
            'suggestions':        'AI explanation unavailable.',
        }

    logger.info('stress-test completed in %.2fs (%d positions)', time.perf_counter() - t0, len(tickers))
    return {
        'positions':   results['positions'],
        'summary':     results['summary'],
        'charts':      results['charts'],
        'explanation': explanation,
    }


_PDF_MAX_BYTES = 2 * 1024 * 1024  # 2 MB of JSON is already enormous for a report


@app.post('/api/export-pdf')
async def export_pdf(data: dict) -> FileResponse:
    if not isinstance(data, dict):
        raise HTTPException(status_code=400, detail='Invalid report data')
    if len(str(data).encode()) > _PDF_MAX_BYTES:
        raise HTTPException(status_code=400, detail='Report data too large')
    try:
        pdf_path = await asyncio.to_thread(create_pdf_report, data)
        return FileResponse(pdf_path, filename='stress_test_report.pdf')
    except Exception as exc:
        logger.error('PDF export failed: %s', exc)
        raise HTTPException(status_code=500, detail='PDF generation failed')


@app.get('/api/market-summary')
async def market_summary() -> dict:
    global _market_cache, _market_cache_ts

    if _market_cache and (time.time() - _market_cache_ts) < MARKET_SUMMARY_TTL:
        return _market_cache

    try:
        def _fetch():
            sp500 = yf.Ticker('^GSPC').history(period='2d')['Close']
            vix   = yf.Ticker('^VIX').history(period='2d')['Close']
            tnx   = yf.Ticker('^TNX').history(period='2d')['Close']
            return {
                'sp500':        round(float(sp500.iloc[-1]), 2),
                'sp500_change': round(float(sp500.pct_change().iloc[-1] * 100), 2),
                'vix':          round(float(vix.iloc[-1]), 2),
                'yield_10y':    round(float(tnx.iloc[-1]), 2),
            }

        data = await asyncio.to_thread(_fetch)
        _market_cache    = data
        _market_cache_ts = time.time()
        return data
    except Exception as exc:
        logger.warning('market-summary fetch failed: %s', exc)
        if _market_cache:
            return _market_cache
        raise HTTPException(status_code=502, detail='Market data unavailable')


_brazil_cache: dict = {}
_brazil_cache_ts: float = 0.0


@app.get('/api/brazil-market-summary')
async def brazil_market_summary() -> dict:
    global _brazil_cache, _brazil_cache_ts

    if _brazil_cache and (time.time() - _brazil_cache_ts) < MARKET_SUMMARY_TTL:
        return _brazil_cache

    try:
        data = await get_brazil_market_summary()
        _brazil_cache    = data
        _brazil_cache_ts = time.time()
        return data
    except Exception as exc:
        logger.warning('brazil-market-summary fetch failed: %s', exc)
        if _brazil_cache:
            return _brazil_cache
        raise HTTPException(status_code=502, detail='Brazil market data unavailable')


_ASSET_TYPE_MAP = {
    'equity':         'equity',
    'stock':          'equity',
    'fixed income':   'cdb',
    'fixed_income':   'cdb',
    'bond':           'cdb',
    'bonds':          'cdb',
    'cdb':            'cdb',
    'lci':            'lci',
    'lca':            'lca',
    'fii':            'fii',
    'real estate':    'fii',
    'reit':           'fii',
    'tesouro_selic':  'tesouro_selic',
    'tesouro selic':  'tesouro_selic',
    'tesouro_ipca':   'tesouro_ipca',
    'tesouro ipca':   'tesouro_ipca',
    'debenture':      'debenture',
    'cash':           'cdi',
    'money market':   'cdi',
    'cdi':            'cdi',
}


def _map_asset_type(asset_class: str) -> str:
    return _ASSET_TYPE_MAP.get(asset_class.lower().strip(), 'equity')


@app.post('/api/brazil-stress-file')
async def brazil_stress_file(
    file: UploadFile = File(...),
    scenario_id: str = Form(...),
    brl_usd_rate: float = Form(5.20),
) -> dict:
    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_BYTES:
        raise HTTPException(status_code=413, detail='File exceeds 10 MB limit')

    suffix = Path(file.filename or '').suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f'Unsupported file type "{suffix}"')

    try:
        df = pd.read_csv(io.BytesIO(contents)) if suffix == '.csv' else pd.read_excel(io.BytesIO(contents))
    except Exception as exc:
        logger.warning('Brazil stress file parse error: %s', exc)
        raise HTTPException(status_code=400, detail='Could not parse the uploaded file')

    df.columns = df.columns.str.lower().str.strip()

    if len(df) > MAX_ROWS:
        raise HTTPException(status_code=400, detail=f'File contains too many rows (max {MAX_ROWS})')

    df = _sanitize_df(df)

    if 'ticker' not in df.columns:
        raise HTTPException(status_code=400, detail='Missing required column: ticker')

    positions = []
    for row in df.itertuples(index=False):
        rd = row._asdict()
        ticker = str(rd.get('ticker', '')).strip().upper()
        if not ticker or not _TICKER_RE.match(ticker):
            continue

        market_value = _safe_float(rd.get('market_value'))
        quantity     = _safe_float(rd.get('quantity'))
        price        = _safe_float(rd.get('price'))

        if market_value > 0:
            value = market_value
        elif quantity > 0 and price > 0:
            value = quantity * price
        else:
            value = _safe_float(rd.get('value'), 10_000.0)

        asset_class = str(rd.get('asset_class', 'equity')).strip()
        currency    = str(rd.get('currency', 'USD')).strip().upper()

        positions.append({
            'ticker':     ticker,
            'value':      value,
            'asset_type': _map_asset_type(asset_class),
            'currency':   currency,
        })

    if not positions:
        raise HTTPException(status_code=400, detail='No valid positions found in file')

    try:
        result = await asyncio.to_thread(
            stress_test_portfolio, positions, scenario_id, brl_usd_rate
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        logger.error('Brazil stress engine failed: %s', exc)
        raise HTTPException(status_code=500, detail='Brazil stress calculation failed')

    return result


@app.get('/api/download-template')
async def download_template() -> FileResponse:
    template_path = Path(__file__).parent / 'portfolio_template.xlsx'
    if not template_path.exists():
        raise HTTPException(status_code=404, detail='Template file not found')
    return FileResponse(
        str(template_path),
        filename='portfolio_template.xlsx',
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    )


@app.post('/api/compare-portfolios')
async def compare_portfolios(
    file_a: UploadFile = File(...),
    file_b: UploadFile = File(...),
    scenario: str = Form(...),
) -> dict:
    scenario = scenario.strip()
    if not scenario:
        raise HTTPException(status_code=400, detail='Scenario description is required')
    if len(scenario) > MAX_SCENARIO_LENGTH:
        raise HTTPException(status_code=400, detail=f'Scenario too long (max {MAX_SCENARIO_LENGTH} characters)')

    async def _run_one(upload: UploadFile) -> dict:
        contents = await upload.read()
        if len(contents) > MAX_FILE_SIZE_BYTES:
            raise HTTPException(status_code=413, detail=f'{upload.filename} exceeds 10 MB limit')
        suffix = Path(upload.filename or '').suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            raise HTTPException(status_code=400, detail=f'Unsupported file type: {suffix}')
        try:
            df = pd.read_csv(io.BytesIO(contents)) if suffix == '.csv' else pd.read_excel(io.BytesIO(contents))
        except Exception as exc:
            logger.warning('File parse error (%s): %s', upload.filename, exc)
            raise HTTPException(status_code=400, detail=f'Could not parse {upload.filename}. Ensure it is a valid Excel or CSV.')
        df.columns = df.columns.str.lower().str.strip()
        if len(df) > MAX_ROWS:
            raise HTTPException(status_code=400, detail=f'{upload.filename} contains too many rows (max {MAX_ROWS})')
        df = _sanitize_df(df)
        missing = REQUIRED_COLUMNS - set(df.columns)
        if missing:
            raise HTTPException(status_code=400, detail=f'Missing columns in {upload.filename}: {", ".join(sorted(missing))}')
        tickers   = df['ticker'].dropna().astype(str).str.strip().str.upper().tolist()
        tickers   = [t for t in tickers if _TICKER_RE.match(t)]
        live_data = await fetch_live_data(tickers)
        return df, live_data

    parsed_scenario, (df_a, live_a), (df_b, live_b) = await asyncio.gather(
        parse_scenario_with_ai(scenario),
        _run_one(file_a),
        _run_one(file_b),
    )
    parsed_scenario['_scenario_text'] = scenario

    results_a, results_b = await asyncio.gather(
        asyncio.to_thread(run_stress_test, df_a, live_a, parsed_scenario),
        asyncio.to_thread(run_stress_test, df_b, live_b, parsed_scenario),
    )
    return {'portfolio_a': results_a, 'portfolio_b': results_b}


if __name__ == '__main__':
    import uvicorn
    uvicorn.run('main:app', host='0.0.0.0', port=PORT, reload=False)
