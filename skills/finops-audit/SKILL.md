---
name: finops-audit
description: >-
  Weekly token spend review via ccusage — structured markdown + JSON reports. 
  Run every Monday to review token spend, set concrete improvements, and optionally 
  export JSON for external tools (dashboards, analytics, visualizers).
user-invocable: true
---

# finops-audit

Run this skill to generate token spend reports in markdown (appended to vault) and/or JSON (exported to file).

## Commands

### Default: Markdown report (append to vault)
```bash
/finops-audit
```
- Runs ccusage commands (monthly, daily breakdown)
- Generates markdown report
- Appends to `$BRAIN_PATH/resources/knowledge/operational/finops-history.md`

### JSON-only export
```bash
/finops-audit --json
```
- Generates JSON report
- Writes to `~/.claude/reports/token-report-<YYYY-MM-DD>.json` (configurable)
- Prints to stdout

### Both markdown and JSON
```bash
/finops-audit --both
```
- Generates both markdown and JSON
- Appends markdown to vault
- Writes JSON to file
- Prints both to stdout

### Silent JSON export (file only)
```bash
/finops-audit --json --quiet
```
- Generates JSON and writes to file
- No stdout output

## Configuration

Optional settings in `~/.claude/finops.json`:

```json
{
  "finops": {
    "enabled": true,
    "session_token_budget": 44000,
    "json_report_path": "~/.claude/reports",
    "json_report_filename_pattern": "token-report-{date}.json",
    "include_all_time_totals": true
  }
}
```

**Defaults:**
- `session_token_budget`: 44000 (Claude Code Pro 5-hour window)
- `json_report_path`: `~/.claude/reports`
- `include_all_time_totals`: true

## Markdown Report Format

```markdown
## Token Audit — Week of <YYYY-MM-DD>

Total tokens: X | Sessions: N
Top model: <model> (<X>% of tokens)
Longest session: <date> — <X> tokens
Hotspot day: <weekday> (<X> tokens)
Recommendation: <one concrete change for next week>
```

Appended to: `$BRAIN_PATH/resources/knowledge/operational/finops-history.md`

## JSON Report Schema

The JSON includes aggregates (year/month/week/day), projects, sessions, and current session snapshot.

```json
{
  "generated_at": "2026-04-12T14:32:00Z",
  "totals": {
    "all_time": { "tokens": 150000, "cost_usd": 2.5000 },
    "year": { "tokens": 145000, "cost_usd": 2.4500 },
    "month": { "tokens": 85000, "cost_usd": 1.4200 },
    "week": { "tokens": 25000, "cost_usd": 0.4100 },
    "day": { "tokens": 8500, "cost_usd": 0.1400 }
  },
  "projects": [ ... ],
  "sessions": [ ... ],
  "current_session": { ... }
}
```

See the implementation docs for complete schema.

## Weekly Habit

Every Monday morning, run:

```bash
/finops-audit --both
```

to review last week's spend AND export JSON for your tracking tool.

## Integration with External Tools

JSON export is designed for consumption by external applications:

```bash
/finops-audit --json --quiet
# Writes to ~/.claude/reports/token-report-2026-04-12.json
# Your visualizer can now read and display this data
```

## Troubleshooting

**Error: ccusage not found**

Install with:
```bash
npm install -g ccusage
```

Or use via npx (no installation):
```bash
npx ccusage@latest blocks --live
```

**Error: Cannot write to JSON path**

Check that `~/.claude/reports/` exists and is writable:
```bash
mkdir -p ~/.claude/reports && chmod 755 ~/.claude/reports
```

**No session data available**

This can happen if ccusage hasn't recorded any sessions yet. Run a Claude Code session first, then run finops-audit.
