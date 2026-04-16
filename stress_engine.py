import numpy as np
import pandas as pd
from scipy import stats
import anthropic, os, json, re
from dotenv import load_dotenv

load_dotenv()

HISTORICAL_SCENARIOS = {
    '2008 Financial Crisis': {
        'market_shock': -0.57,
        'sector_shocks': {
            'Financials': -0.80,
            'Real Estate': -0.65,
            'Consumer Discretionary': -0.45,
        },
        'rate_shock': -0.04,
        'severity_label': 'Extreme',
    },
    'COVID Crash (Feb-Mar 2020)': {
        'market_shock': -0.34,
        'sector_shocks': {
            'Energy': -0.55,
            'Consumer Discretionary': -0.40,
            'Technology': -0.10,
        },
        'rate_shock': -0.015,
        'severity_label': 'Severe',
    },
    'Dot-Com Bust (2000-2002)': {
        'market_shock': -0.49,
        'sector_shocks': {
            'Technology': -0.78,
            'Communication Services': -0.65,
        },
        'rate_shock': -0.025,
        'severity_label': 'Extreme',
    },
}

def simple_parse(text):
    text_lower = text.lower()
    market_shock = 0

    pct = re.findall(r'(\d+(?:\.\d+)?)%', text)
    if pct:
        market_shock = -float(pct[0]) / 100

    if not pct:
        if 'crash' in text_lower or 'crisis' in text_lower:
            market_shock = -0.30
        elif 'drop' in text_lower or 'fall' in text_lower:
            market_shock = -0.20
        elif 'correction' in text_lower:
            market_shock = -0.10

    rate_shock = 0
    rate_pct = re.findall(r'rates?\s+(?:up|rise|rise by|up by)\s+(\d+\.?\d*)%', text_lower)
    if rate_pct:
        rate_shock = float(rate_pct[0]) / 100

    return {
        'market_shock': market_shock,
        'sector_shocks': {},
        'rate_shock': rate_shock,
        'inflation_shock': 0,
        'severity_label': 'Extreme' if abs(market_shock) > 0.35 else ('Severe' if abs(market_shock) > 0.25 else 'Moderate'),
    }


def parse_scenario_with_ai(scenario_text: str) -> dict:
    api_key = os.getenv('ANTHROPIC_API_KEY')

    if not api_key:
        print("No API key found, using simple parser")
        return simple_parse(scenario_text)

    try:
        client = anthropic.Anthropic(api_key=api_key)
        prompt = f'''Parse this investment stress scenario into structured JSON.
Scenario: {scenario_text}

Return ONLY valid JSON with these keys:
- market_shock: float (e.g. -0.30 for a 30% crash, 0 if not mentioned)
- sector_shocks: object mapping sector names to shock floats
- rate_shock: float (e.g. 0.02 for +2% rate rise)
- inflation_shock: float
- severity_label: one of "Mild", "Moderate", "Severe", "Extreme"

Return only the JSON object, nothing else. No markdown, no backticks.'''

        message = client.messages.create(
            model='claude-opus-4-6',
            max_tokens=500,
            messages=[{'role': 'user', 'content': prompt}]
        )

        text = message.content[0].text.strip()

        # Remove markdown code blocks if present
        if '```' in text:
            text = re.sub(r'```(?:json)?', '', text).strip()

        return json.loads(text)

    except Exception as e:
        print(f"Claude parsing failed: {e}, using fallback parser")
        return simple_parse(scenario_text)


def run_stress_test(df: pd.DataFrame, live_data: dict, scenario_text: str) -> dict:
    scenario = parse_scenario_with_ai(scenario_text)

    market_shock = scenario.get('market_shock', 0)
    sector_shocks = scenario.get('sector_shocks', {})
    rate_shock = scenario.get('rate_shock', 0)

    positions = []
    total_value = 0
    stressed_value = 0

    for _, row in df.iterrows():
        ticker = row['ticker']
        weight = float(row['weight']) / 100
        value = float(row.get('value', 10000))

        stock_data = live_data.get(ticker, {})
        beta = stock_data.get('beta', 1.0)
        sector = stock_data.get('sector', 'Unknown')
        daily_returns = stock_data.get('daily_returns', [])

        beta_adj_market_shock = market_shock * beta
        sector_adj_shock = sector_shocks.get(sector, 0)
        rate_sensitivity = -5 * rate_shock if sector in ['Utilities', 'Real Estate'] else -2 * rate_shock

        total_shock = beta_adj_market_shock + sector_adj_shock + rate_sensitivity
        total_shock = max(total_shock, -0.99)

        if len(daily_returns) > 30:
            var_95 = float(np.percentile(daily_returns, 5))
            cvar_95 = float(np.mean([r for r in daily_returns if r <= var_95]))
        else:
            var_95 = -0.02
            cvar_95 = -0.03

        stressed_position_value = value * (1 + total_shock)
        loss = stressed_position_value - value

        total_value += value
        stressed_value += stressed_position_value

        positions.append({
            'ticker': ticker,
            'name': stock_data.get('name', ticker),
            'sector': sector,
            'weight': round(weight * 100, 2),
            'value': round(value, 2),
            'stressed_value': round(stressed_position_value, 2),
            'loss': round(loss, 2),
            'loss_pct': round(total_shock * 100, 2),
            'var_95': round(var_95 * 100, 2),
            'cvar_95': round(cvar_95 * 100, 2),
            'beta': round(beta, 2),
            'total_shock_pct': round(total_shock * 100, 2),
            'risk_level': 'High' if total_shock < -0.25 else ('Medium' if total_shock < -0.10 else 'Low'),
        })

    total_loss = stressed_value - total_value
    total_loss_pct = (total_loss / total_value * 100) if total_value > 0 else 0

    all_returns = [r for p in positions
                   for r in live_data.get(p['ticker'], {}).get('daily_returns', [])]
    if all_returns:
        avg_return = np.mean(all_returns) * 252
        std_return = np.std(all_returns) * np.sqrt(252)
        sharpe_before = round((avg_return - 0.05) / std_return, 2) if std_return > 0 else 0
        stressed_avg = avg_return + total_loss_pct / 100
        sharpe_after = round((stressed_avg - 0.05) / std_return, 2) if std_return > 0 else 0
    else:
        sharpe_before = sharpe_after = 0

    sector_weights = {}
    for pos in positions:
        s = pos['sector']
        sector_weights[s] = sector_weights.get(s, 0) + pos['weight']

    return {
        'positions': positions,
        'summary': {
            'total_value': round(total_value, 2),
            'stressed_value': round(stressed_value, 2),
            'total_loss': round(total_loss, 2),
            'total_loss_pct': round(total_loss_pct, 2),
            'sharpe_before': sharpe_before,
            'sharpe_after': sharpe_after,
            'severity_label': scenario.get('severity_label', 'Moderate'),
            'scenario_text': scenario_text,
            'parsed_scenario': scenario,
        },
        'charts': {
            'sector_weights': sector_weights,
            'loss_by_position': [
                {'ticker': p['ticker'], 'loss_pct': p['loss_pct']}
                for p in sorted(positions, key=lambda x: x['loss_pct'])
            ],
        }
    }