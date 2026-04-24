import os
from dotenv import load_dotenv

load_dotenv()

# ── Claude models ─────────────────────────────────────────────────────────────
# Change these env vars to override without touching code.
CLAUDE_FAST_MODEL  = os.getenv("CLAUDE_FAST_MODEL",  "claude-sonnet-4-5")
CLAUDE_SMART_MODEL = os.getenv("CLAUDE_SMART_MODEL", "claude-opus-4-6")

# ── API keys ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
FRED_API_KEY      = os.getenv("FRED_API_KEY")  # optional — macro data degrades gracefully

# ── Server ────────────────────────────────────────────────────────────────────
PORT = int(os.getenv("PORT", 8080))

# ── CORS ──────────────────────────────────────────────────────────────────────
ALLOWED_ORIGINS = [
    "https://stress-test-frontend-three.vercel.app",
    "http://localhost:3000",
    "http://localhost:3001",
]

# ── File upload ───────────────────────────────────────────────────────────────
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS  = {".xlsx", ".csv"}

# ── DataFrame validation ──────────────────────────────────────────────────────
REQUIRED_COLUMNS = {"ticker"}

# ── Cache ─────────────────────────────────────────────────────────────────────
MARKET_SUMMARY_TTL = 300  # seconds (5 minutes)
