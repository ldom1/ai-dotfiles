---
name: token-watch
description: >-
  Snapshot current token burn rate — active window, daily breakdown, and session history
  via ccusage. Use whenever the user wants to check token usage, monitor spend, review
  Claude costs, or asks how many tokens were used. Trigger on: "how much have I spent?",
  "check my token usage", "am I burning too many tokens?", or before a /compact decision.
user-invocable: true
---

# token-watch

Run **`/token-watch`** to get a live view of your Claude Code token consumption.

## What it runs

```bash
# Active 5-hour window
npx ccusage@latest blocks --live

# Per-model breakdown today
npx ccusage@latest daily --breakdown

# By session
npx ccusage@latest session
```

## Inline context usage

At any point type `/context` in the Claude Code prompt to see a per-category token breakdown of the current context window (no ccusage needed).

## Weekly habit

Every Monday morning, run:

```bash
npx ccusage@latest monthly --breakdown
```

to review the previous week's spend before starting new work.

## Interpretation

| Signal | Action |
|--------|--------|
| >30k tokens used in window | Run `/compact` now, not later |
| Opus > 50% of daily tokens | Switch to Sonnet for remaining tasks |
| Single session > 15k tokens | Check if brain-load output is too verbose (BRAIN_LOAD_SLIM=1) |

## Model costs (relative)

- Opus: ~5x Sonnet input, ~3x output
- Sonnet: baseline
- Haiku: ~0.2x Sonnet

Use Haiku for: grep, rename, format, README edits, quick lookups.
