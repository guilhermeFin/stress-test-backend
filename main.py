from fastapi import FastAPI, File, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import pandas as pd
import io, os, json, sys
from dotenv import load_dotenv

from stress_engine import run_stress_test
from data_fetcher import fetch_live_data
from ai_explainer import generate_explanation
from report_generator import create_pdf_report

load_dotenv()

app = FastAPI(title='Portfolio Stress Test API')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_methods=['*'],
    allow_headers=['*'],
)

@app.post('/api/stress-test')
async def stress_test(
    file: UploadFile = File(...),
    scenario: str = Form(...),
):
    contents = await file.read()
    if file.filename and file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    else:
        df = pd.read_excel(io.BytesIO(contents))
    df.columns = df.columns.str.lower().str.strip()
    tickers = df['ticker'].tolist()
    live_data = fetch_live_data(tickers)
    results = run_stress_test(df, live_data, scenario)
    explanation = generate_explanation(results, scenario)
    return {
        'positions': results['positions'],
        'summary': results['summary'],
        'charts': results['charts'],
        'explanation': explanation,
    }


@app.post('/api/export-pdf')
async def export_pdf(data: dict):
    pdf_path = create_pdf_report(data)
    return FileResponse(pdf_path, filename='stress_test_report.pdf')


@app.get('/api/market-summary')
async def market_summary():
    import yfinance as yf
    try:
        sp500 = yf.Ticker('^GSPC').history(period='2d')['Close']
        vix   = yf.Ticker('^VIX').history(period='2d')['Close']
        tnx   = yf.Ticker('^TNX').history(period='2d')['Close']
        return {
            'sp500': round(float(sp500.iloc[-1]), 2),
            'sp500_change': round(float(sp500.pct_change().iloc[-1] * 100), 2),
            'vix': round(float(vix.iloc[-1]), 2),
            'yield_10y': round(float(tnx.iloc[-1]), 2),
        }
    except:
        return {'sp500': 0, 'sp500_change': 0, 'vix': 0, 'yield_10y': 0}


@app.get('/api/download-template')
async def download_template():
    template_path = os.path.join(os.path.dirname(__file__), 'portfolio_template.xlsx')
    return FileResponse(
        template_path,
        filename='portfolio_template.xlsx',
        media_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )


@app.post('/api/run-pipeline')
async def run_pipeline_endpoint():
    engine_path = os.path.join(os.path.dirname(__file__), '..', 'portfolio_stress_engine')
    sys.path.insert(0, engine_path)
    try:
        from run_engine import run_pipeline
        output = run_pipeline(hours_back=24, use_claude=True)
        return {
            'status':  'success',
            'run_id':  output['run_id'],
            'summary': output['summary'],
            'signals': output['signals'],
        }
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.get('/api/stress-results')
async def stress_results():
    engine_path = os.path.join(os.path.dirname(__file__), '..', 'portfolio_stress_engine')
    sys.path.insert(0, engine_path)
    try:
        from signals.stress_test import run_stress_test as run_st
        results = run_st()
        return {'status': 'success', 'results': results}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


@app.get('/api/memo')
async def get_memo():
    engine_path = os.path.join(os.path.dirname(__file__), '..', 'portfolio_stress_engine')
    sys.path.insert(0, engine_path)
    try:
        from reports.memo_generator import generate_memo
        memo = generate_memo()
        return {'status': 'success', 'memo': memo}
    except Exception as e:
        return {'status': 'error', 'message': str(e)}


if __name__ == '__main__':
    import uvicorn
    port = int(os.environ.get('PORT', 8080))
    uvicorn.run('main:app', host='0.0.0.0', port=port, reload=False)