# PortfolioStress — Backend

## Claude's Role
You are helping build and improve the PortfolioStress backend.
Target user: independent wealth managers and RIAs.
The backend must be fast, reliable, and return clean structured data the frontend can display immediately.

## What This Product Does
PortfolioStress is a portfolio stress testing tool for wealth managers.
The user uploads an Excel file with their positions, picks a crisis scenario or describes one,
and gets a full institutional-grade risk analysis in 60 seconds.

## Tech Stack
- Framework: Python / FastAPI
- Port: 8080
- Hosting: Railway
- AI: Claude (Anthropic API)
- Data sources: FRED, SEC EDGAR, yfinance, news feeds

## Key Endpoints (already built)
- Excel upload and parsing (13-column template)
- Historical scenario analysis (6 presets)
- Custom scenario builder from plain English
- Custom shock builder (6 sliders)
- Factor risk model (5 factors: beta, rates, inflation, credit, growth)
- Correlation breakdown (normal vs stress)
- Liquidity stress analysis
- Monte Carlo simulation (1,000 paths, normal distribution / parametric assumptions)
- Benchmark comparison (S&P 500, 60/40, All-Weather, Global Bonds)
- AI analyst memo generation via Claude API
- PDF export generation

## Important Context on the Monte Carlo
The simulation currently uses parametric assumptions with a normal distribution.
This is intentional — the target user is wealth managers, not quants.
The tool is positioned as a communication and scenario planning layer, not a regulatory-grade risk model.
Do not over-engineer the simulation unless explicitly asked.

## Target User
Independent wealth managers and RIAs.
Speed and reliability matter most — analysis must complete in under 60 seconds.

## Business Context
- Frontend: https://stress-test-frontend-three.vercel.app
- Backend: https://stress-test-backend-production.up.railway.app
- Pricing: Starter $99/mo, Professional $299/mo, Enterprise $799/mo

## Roadmap (not yet built)
- CRM integration (Salesforce, Redtail)
- Custodian sync (Schwab, Fidelity, Interactive Brokers)
- Weekly intelligence reports by email
- Compliance audit trail
