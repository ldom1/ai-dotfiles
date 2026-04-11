---
name: brain-route
description: Session mode decision router—determines whether to run maintenance or normal context load based on vault state
user-invocable: false
---

# brain-route

Session mode decision router. Inspects Local Brain vault state and decides whether to run in **normal mode** (context load via brain-load) or **maintenance mode** (vault audit via brain-audit).

## Quick start

```bash
bash ~/ai-dotfiles/skills/brain-route/scripts/route.sh
```

Prints decision outcome and session_mode variable, then calls the appropriate downstream skill.

## Decision logic

Routes to **maintenance mode** (brain-audit) if ANY of these conditions are true:

1. `--maintenance` flag passed to route.sh
2. More than 7 days since last brain maintenance timestamp
3. More than 50 raw note files in vault (bloat check)

Routes to **normal mode** (brain-load) otherwise.

## What it does

| Step | Action |
|------|--------|
| 1. Load config | Read `BRAIN_PATH` from `BRAIN_ENV_FILE`, `brain.env`, or `config/brain.env` |
| 2. Check flags | Look for `--maintenance` flag |
| 3. Check maintenance state | Read `$BRAIN_PATH/.brain/last-maintenance` timestamp |
| 4. Check vault bloat | Count files in `$BRAIN_PATH/` (excluding `.git`, `.obsidian`, etc.) |
| 5. Log decision | Write human-readable decision to `$BRAIN_PATH/.brain/route.log` |
| 6. Call downstream | Execute `brain-load` (normal) or `brain-audit` (maintenance) |

## Configuration

`BRAIN_PATH` must be the **absolute path** to a **git repository** (your Obsidian vault). The script loads it from the **first match**:

1. `BRAIN_ENV_FILE` — environment variable pointing to an env file with `BRAIN_PATH=…`
2. `brain.env` beside `scripts/route.sh` — for standalone usage
3. `config/brain.env` at the ai-dotfiles root — default when using the full install

See `reference/brain.env.example` for the template.

## Decision output

The route.sh script outputs JSON (or key=value pairs) with:

```
session_mode=normal|maintenance
reason=<string>
timestamp=<ISO8601>
file_count=<count>
last_maintenance_age_days=<days>
```

This output is consumed by the harness (SessionStart hook) to determine which downstream skill to call.

## Scripts

| Script | Role |
|--------|------|
| `scripts/route.sh` | Main decision logic + downstream call |
| `scripts/_brain_env.sh` | Config loader (sourced by route.sh) |

## Autonomous execution (SessionStart hook)

```bash
bash ~/ai-dotfiles/skills/brain-route/scripts/route.sh
```

Runs **before** brain-load or brain-audit. Examines vault state, decides which skill to run next, and logs the decision.

**On failure:**
- Missing `BRAIN_PATH` → warn once, skip to normal mode (brain-load).
- Script not found → warn once, continue with normal mode.
- Upstream skill (brain-load/brain-audit) fails → propagate error to user.

## Edge cases

| Situation | Behavior |
|-----------|----------|
| No `BRAIN_PATH` set | Warn, default to normal mode (brain-load) |
| Vault doesn't exist | Warn, default to normal mode |
| No maintenance timestamp | Assume never run, check file count; if > 50, route to maintenance |
| Timestamp corrupted | Treat as missing; check file count; if > 50, route to maintenance |
| File count unreliable | Fall back to timestamp check |
| `--maintenance` flag set | Always route to maintenance (override all checks) |
| Script not found | Warn once, default to normal mode |

## Files

```
skills/brain-route/
├── SKILL.md
├── scripts/
│   ├── route.sh          ← decision logic + downstream call
│   └── _brain_env.sh     ← config loader (sourced by route.sh)
└── reference/
    └── brain.env.example ← copy as brain.env, set BRAIN_PATH
```
