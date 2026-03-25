# OCC Scanner

When a company does a stock split, merger, or spinoff, your options contracts change. The OCC publishes memos about this but most traders never see them. By the time they notice something is wrong, it's too late to act.

This skill watches the OCC website for you. Every day it checks for new memos on the stocks you hold options on. When it finds one, it sends you a plain-English alert explaining exactly what changed and what you need to do.

## Why this matters

Say you hold a covered call on a stock that does a reverse split. Overnight:

- Your option gets a new symbol
- The number of shares you need as collateral drops
- The contract becomes very hard to trade wide spreads, few buyers
- You can no longer open new positions, only close

None of this shows up as a notification from your broker. You have to know to look for it. This skill looks for it automatically.

## What you get

- A daily scan of OCC memos for every ticker you track
- A Telegram alert written like a text from a friend who knows options — not a legal document
- The exact exercise math for your contract (what you pay, what you receive)
- A clear answer to: can you still trade this, or only close it?

## Setup

You need Python 3 and a one-time install:

```bash
python3 -m venv ~/.openclaw/occ-venv
source ~/.openclaw/occ-venv/bin/activate
pip install playwright pypdf yfinance
playwright install chromium
```

Create your positions file if it doesn't exist:

```bash
echo "[]" > ~/.openclaw/workspace/positions.json
```

## How to use it

Just talk to Claude:

- "add NVDA to my positions"
- "remove WOLF"
- "show what I'm tracking"
- "scan OCC now"
- "scan OCC for SOXS"
- "set up a daily OCC scan at 8am"

## Running the script directly

```bash
source ~/.openclaw/occ-venv/bin/activate

# Scan all your saved positions
python3 ~/.openclaw/workspace/skills/occ-scanner/scripts/scrape_occ.py

# Scan one ticker
python3 ~/.openclaw/workspace/skills/occ-scanner/scripts/scrape_occ.py WOLF

# Re-scan everything, even memos you've seen before
python3 ~/.openclaw/workspace/skills/occ-scanner/scripts/scrape_occ.py --fresh
```

## Files

| File | What it does |
|------|-------------|
| `~/.openclaw/workspace/positions.json` | The tickers you want to monitor |
| `~/.openclaw/occ_seen_ids.json` | Memos already sent — so you don't get the same alert twice |
