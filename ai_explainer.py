import asyncio
import logging
import time

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY, CLAUDE_SMART_MODEL

logger = logging.getLogger(__name__)

async def generate_explanation(results: dict, scenario: str) -> dict:
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    summary   = results['summary']
    positions = results['positions']

    top_losers  = sorted(positions, key=lambda x: x['loss_pct'])[:3]
    loser_text  = ', '.join(f"{p['ticker']} ({p['loss_pct']:.1f}%)" for p in top_losers)

    advisor_prompt = f'''You are a senior wealth management advisor. Summarize these stress test results
in 3 concise bullet points for an internal advisor note.

Scenario: {scenario}
Total portfolio loss: {summary['total_loss_pct']:.1f}%
Portfolio value: ${summary['total_value']:,.0f} -> ${summary['stressed_value']:,.0f}
Biggest losers: {loser_text}
Sharpe ratio change: {summary['sharpe_before']} -> {summary['sharpe_after']}

Write exactly 3 bullet points. Be specific with numbers. No headers.'''

    client_prompt = f'''You are explaining investment risk to a non-expert client.
Write 2 short paragraphs (4-5 sentences each) in plain English.
No jargon. Use the word 'you' to address the client directly.
Be honest but reassuring. Do not use bullet points.

Scenario: {scenario}
Portfolio value before: ${summary['total_value']:,.0f}
Portfolio value after: ${summary['stressed_value']:,.0f}
Loss percentage: {summary['total_loss_pct']:.1f}%
Severity: {summary['severity_label']}'''

    suggestions_prompt = f'''You are a portfolio manager. Based on this stress test, give exactly 4 specific
rebalancing suggestions. Each suggestion must include:
- What to reduce (with specific %) or add
- Why (one sentence)
Format each as: ACTION | REASON

Top losers under stress: {loser_text}
Scenario: {scenario}
Total loss: {summary['total_loss_pct']:.1f}%'''

    async def ask(prompt: str, label: str) -> str:
        t0 = time.perf_counter()
        msg = await client.messages.create(
            model=CLAUDE_SMART_MODEL,
            max_tokens=600,
            messages=[{'role': 'user', 'content': prompt}],
        )
        logger.info('Claude %s done in %.2fs', label, time.perf_counter() - t0)
        return msg.content[0].text.strip()

    t0 = time.perf_counter()
    advisor_summary, client_explanation, suggestions = await asyncio.gather(
        ask(advisor_prompt,     'advisor_summary'),
        ask(client_prompt,      'client_explanation'),
        ask(suggestions_prompt, 'suggestions'),
    )
    logger.info('All 3 Claude calls finished in %.2fs', time.perf_counter() - t0)

    return {
        'advisor_summary':    advisor_summary,
        'client_explanation': client_explanation,
        'suggestions':        suggestions,
    }
