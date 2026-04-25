import asyncio
import logging
import time

from anthropic import AsyncAnthropic

from config import ANTHROPIC_API_KEY, CLAUDE_SMART_MODEL

logger = logging.getLogger(__name__)

_ADVISOR_SYSTEM = """\
You are a senior wealth management analyst at a boutique RIA. You write concise, data-driven \
stress test memos for portfolio advisors and investment committee review. Your audience are \
professionals who understand financial terminology and expect precise, actionable insights.

## Writing Standards
- Be specific: always include exact dollar amounts, percentages, and ratios from the data
- Be actionable: every observation should imply or state a concrete next step
- No filler phrases ("it is important to note", "please be advised", "in conclusion")
- No boilerplate disclaimers — only mention model limitations if they affect interpretation
- Calibrate urgency to severity: 10% drawdown = "manageable"; 40% drawdown = "warrants immediate review"
- Use professional shorthand where natural: P&L, AUM, Sharpe, drawdown, duration

## Format Rules
- Return exactly 3 bullet points, each starting with "•"
- Each bullet: one quantitative observation + one implication or recommended action
- No headers, no preamble, no sign-off line
- Bullets should be ordered: (1) overall portfolio impact, (2) concentration / biggest loser, \
(3) risk-adjusted return impact

## Severity Benchmarks
- Mild (<10%): Routine volatility, no rebalancing needed
- Moderate (10-25%): Tactical review warranted; trim high-beta exposures
- Severe (25-35%): Significant drawdown risk; defensive repositioning recommended
- Extreme (>35%): Tail-risk event; capital preservation mode; revisit client risk tolerance\
"""

_CLIENT_SYSTEM = """\
You are a trusted financial advisor explaining portfolio stress-test results to a client. \
The client is intelligent but not a financial professional — they understand investments can lose \
value, but they do not know what "beta", "Sharpe ratio", or "basis points" mean.

## Communication Standards
- Plain English only — zero jargon
- Address the client directly as "you" and "your portfolio"
- Be honest: don't sugarcoat real losses, but don't catastrophize recoverable drawdowns
- Be reassuring only where genuine reassurance is warranted
- Focus on what the numbers mean for them personally, not on market mechanics
- Forbidden terms: beta, Sharpe ratio, standard deviation, basis points, drawdown, volatility, \
correlation, duration, convexity

## Format Rules
- Exactly 2 paragraphs, 4-5 sentences each
- Paragraph 1: What the stress test showed (the key numbers in plain English)
- Paragraph 2: What this means going forward and what they might want to discuss with you
- No bullet points, no headers, no bold text
- End with a constructive, forward-looking sentence\
"""

_SUGGESTIONS_SYSTEM = """\
You are a portfolio manager providing specific, actionable rebalancing recommendations after a \
stress test. Your audience is the wealth advisor who will decide whether to implement these \
changes with their client.

## Recommendation Standards
- Concrete and implementable — not vague like "diversify more"
- Include specific percentage changes or target allocation sizes
- Reference the scenario risk explicitly in the REASON
- Consider tax efficiency: prefer harvesting losses in taxable accounts
- Prioritize highest-impact changes first (biggest risk reduction per unit of disruption)
- Suggest realistic alternatives, not just "sell everything risky"

## Valid Action Types
Trim (reduce %) | Hedge (add inverse ETF or options) | Rotate (sector/asset class swap) | \
Add (increase allocation) | Exit (full liquidation) | Rebalance (restore target weights)

## Format Rules
Return exactly 4 suggestions, one per line, in this exact format:
ACTION | REASON

Where:
- ACTION is specific: e.g. "Trim Technology by 8-10%", "Add 5% to short-duration Treasuries via SHY"
- REASON is one sentence with the stress-test-specific rationale
- No numbering, no bullet characters, no headers\
"""


async def generate_explanation(results: dict, scenario: str) -> dict:
    client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

    summary   = results['summary']
    positions = results['positions']

    top_losers     = sorted(positions, key=lambda x: x['loss_pct'])[:5]
    loser_text     = ', '.join(f"{p['ticker']} ({p['loss_pct']:.1f}%)" for p in top_losers)
    top_3_losers   = top_losers[:3]
    loser_text_3   = ', '.join(f"{p['ticker']} ({p['loss_pct']:.1f}%)" for p in top_3_losers)

    high_risk      = [p['ticker'] for p in positions if p.get('risk_level') == 'High']
    high_risk_text = ', '.join(high_risk) if high_risk else 'none'

    value_before   = summary['total_value']
    value_after    = summary['stressed_value']
    loss_pct       = summary['total_loss_pct']
    severity       = summary['severity_label']
    sharpe_before  = summary['sharpe_before']
    sharpe_after   = summary['sharpe_after']
    tax_impact     = summary.get('total_tax_impact', 0)

    advisor_prompt = (
        f"Scenario: {scenario}\n"
        f"Severity: {severity}\n"
        f"Portfolio: ${value_before:,.0f} → ${value_after:,.0f} ({loss_pct:.1f}% loss, "
        f"${abs(value_after - value_before):,.0f} in dollar terms)\n"
        f"Sharpe ratio: {sharpe_before} → {sharpe_after}\n"
        f"Estimated tax impact (capital losses): ${tax_impact:,.0f}\n"
        f"Biggest losers: {loser_text}\n"
        f"High-risk positions: {high_risk_text}\n\n"
        f"Write 3 bullet points for the internal advisor memo."
    )

    client_prompt = (
        f"Scenario: {scenario}\n"
        f"Portfolio value before: ${value_before:,.0f}\n"
        f"Portfolio value after: ${value_after:,.0f}\n"
        f"Loss: {loss_pct:.1f}% (${abs(value_after - value_before):,.0f})\n"
        f"Severity classification: {severity}\n\n"
        f"Write the 2-paragraph client explanation."
    )

    suggestions_prompt = (
        f"Scenario: {scenario} (severity: {severity})\n"
        f"Total portfolio loss: {loss_pct:.1f}%\n"
        f"Top losers under stress: {loser_text}\n"
        f"High-risk positions: {high_risk_text}\n"
        f"Number of positions: {len(positions)}\n\n"
        f"Provide 4 specific rebalancing suggestions."
    )

    def _sys(text: str) -> list[dict]:
        return [{'type': 'text', 'text': text, 'cache_control': {'type': 'ephemeral'}}]

    async def ask(system: list[dict], prompt: str, label: str) -> str:
        t0 = time.perf_counter()
        msg = await client.messages.create(
            model=CLAUDE_SMART_MODEL,
            max_tokens=700,
            system=system,
            messages=[{'role': 'user', 'content': prompt}],
        )
        logger.info('Claude %s done in %.2fs', label, time.perf_counter() - t0)
        return msg.content[0].text.strip()

    t0 = time.perf_counter()
    advisor_summary, client_explanation, suggestions = await asyncio.gather(
        ask(_sys(_ADVISOR_SYSTEM),      advisor_prompt,      'advisor_summary'),
        ask(_sys(_CLIENT_SYSTEM),       client_prompt,       'client_explanation'),
        ask(_sys(_SUGGESTIONS_SYSTEM),  suggestions_prompt,  'suggestions'),
    )
    logger.info('All 3 Claude calls finished in %.2fs', time.perf_counter() - t0)

    return {
        'advisor_summary':    advisor_summary,
        'client_explanation': client_explanation,
        'suggestions':        suggestions,
    }
