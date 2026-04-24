import io
from unittest.mock import AsyncMock, patch

import openpyxl
import pytest
from httpx import ASGITransport, AsyncClient

from main import app

# ── helpers ───────────────────────────────────────────────────────────────────

def _make_excel(rows: list[dict]) -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    if rows:
        ws.append(list(rows[0].keys()))
        for row in rows:
            ws.append(list(row.values()))
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


FAKE_LIVE_DATA = {
    'AAPL': {
        'current_price': 150.0,
        'daily_returns': [-0.01, 0.02, -0.005] * 70,
        'beta': 1.2,
        'sector': 'Technology',
        'market_cap': 2_000_000_000_000,
        'name': 'Apple Inc.',
    }
}

FAKE_EXPLANATION = {
    'advisor_summary':    'Test advisor summary.',
    'client_explanation': 'Test client explanation.',
    'suggestions':        'Test suggestions.',
}

FAKE_PARSED_SCENARIO = {
    'market_shock':    -0.30,
    'sector_shocks':   {},
    'rate_shock':      0.0,
    'inflation_shock': 0.0,
    'severity_label':  'Severe',
}


@pytest.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url='http://test') as c:
        yield c


# ── tests ─────────────────────────────────────────────────────────────────────

async def test_health(client):
    r = await client.get('/health')
    assert r.status_code == 200
    assert r.json()['status'] == 'ok'


async def test_market_summary_cached(client):
    import main as m
    m._market_cache    = {'sp500': 5000.0, 'sp500_change': 0.5, 'vix': 15.0, 'yield_10y': 4.2}
    m._market_cache_ts = 9_999_999_999.0  # far in the future

    r = await client.get('/api/market-summary')
    assert r.status_code == 200
    assert r.json()['sp500'] == 5000.0


async def test_stress_test_success(client):
    xlsx = _make_excel([{'ticker': 'AAPL', 'value': 10000}])

    with (
        patch('main.fetch_live_data',      new=AsyncMock(return_value=FAKE_LIVE_DATA)),
        patch('main.parse_scenario_with_ai', new=AsyncMock(return_value=dict(FAKE_PARSED_SCENARIO))),
        patch('main.generate_explanation', new=AsyncMock(return_value=FAKE_EXPLANATION)),
    ):
        r = await client.post(
            '/api/stress-test',
            files={'file': ('portfolio.xlsx', xlsx, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
            data={'scenario': 'Market crashes 30%'},
        )

    assert r.status_code == 200
    body = r.json()
    assert 'positions' in body
    assert 'summary'   in body
    assert body['summary']['total_value'] > 0


async def test_missing_ticker_column(client):
    xlsx = _make_excel([{'symbol': 'AAPL', 'value': 10000}])
    r = await client.post(
        '/api/stress-test',
        files={'file': ('portfolio.xlsx', xlsx, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        data={'scenario': 'Market crashes 30%'},
    )
    assert r.status_code == 400
    assert 'ticker' in r.json()['detail'].lower()


async def test_file_too_large(client):
    big = b'x' * (11 * 1024 * 1024)
    r = await client.post(
        '/api/stress-test',
        files={'file': ('big.xlsx', big, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')},
        data={'scenario': 'crash'},
    )
    assert r.status_code == 413


async def test_invalid_file_type(client):
    r = await client.post(
        '/api/stress-test',
        files={'file': ('data.pdf', b'%PDF', 'application/pdf')},
        data={'scenario': 'crash'},
    )
    assert r.status_code == 400
    assert 'unsupported' in r.json()['detail'].lower()
