---
name: finops-audit
description: Weekly token spend review via ccusage — structured report appended to finops-history.md in the Local Brain vault
user-invocable: true
---

# finops-audit

Run **`/finops-audit`** every Monday to review last week's token spend and set a concrete improvement for the coming week.

## What it does

1. Runs ccusage for monthly and weekly breakdowns
2. Generates a structured report
3. Appends to `$BRAIN_PATH/resources/knowledge/operational/finops-history.md`

## Commands to run

```bash
# Monthly breakdown (includes last 7 days)
npx ccusage@latest monthly --breakdown

# Daily breakdown since last Monday (adjust date)
LAST_MONDAY=$(date -d "last monday" +%Y-%m-%d 2>/dev/null || date -v-monday +%Y-%m-%d)
npx ccusage@latest daily --breakdown
```

## Report format

After running the commands above, generate and append this report:

```markdown
## Token Audit — Week of <YYYY-MM-DD>

Total tokens: X | Sessions: N
Top model: <model> (<X>% of tokens)
Longest session: <date> — <X> tokens
Hotspot day: <weekday> (<X> tokens)
Recommendation: <one concrete change for next week>
```

Append to: `$BRAIN_PATH/resources/knowledge/operational/finops-history.md`

```bash
BRAIN_PATH=$(grep BRAIN_PATH ~/ai-dotfiles/config/brain.env | cut -d= -f2)
echo "## Token Audit — Week of $(date +%Y-%m-%d)" >> "$BRAIN_PATH/resources/knowledge/operational/finops-history.md"
# ... append full report
```

## Weekly habit triggers

| Signal | Action |
|--------|--------|
| Opus > 40% of weekly tokens | Audit which sessions used Opus; move to Sonnet |
| Any single session > 20k tokens | Was that session worth it? Add to pitfalls if not |
| Total > 200k tokens/week | Reduce brain-load verbosity (`BRAIN_LOAD_SLIM=1` for non-project work) |
| CLAUDE.md > 50 lines | Trim again |

## Cron reminder

Add to your calendar or shell alias: run `/finops-audit` every Monday before starting Claude Code.

```bash
# Optional cron (runs ccusage summary, not Claude)
# 0 9 * * 1  npx ccusage@latest monthly --breakdown >> ~/.claude/logs/finops-weekly.log
```
