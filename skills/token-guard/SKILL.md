---
name: token-guard
description: Model routing heuristic + /model-check command to track current model and recent session costs
user-invocable: true
---

# token-guard

**Before starting any multi-step or agentic task**, emit:

> [token-guard] Model: `<current>`. Task type: `<inferred>`. Suggested: `<sonnet|haiku|opus>`

## Model routing heuristic

| Task type | Model |
|-----------|-------|
| Architecture, multi-file refactor, complex/gnarly debug | **Opus** |
| Feature implementation, tests, PRs, most code, code review | **Sonnet** (default) |
| Grep, rename, format, quick lookup, README edits, single-file fixes | **Haiku** |

## /model-check

Run this to see the current model and last 3 session costs:

```bash
# Current model is shown in the Claude Code status bar or /status
# Last 3 session costs:
npx ccusage@latest session | head -4
```

## Upgrade trigger (→ Opus)
Switch to Opus when: designing system architecture, debugging across 5+ files, performance profiling, security audit, or any task where wrong decisions have large rework cost.

## Downgrade trigger (→ Haiku)
Switch to Haiku when: single-file edits, text search/replace, generating boilerplate from a clear pattern, formatting/linting.

## Token-guard reminder format

At task start (multi-step only), Claude should output one line:
```
[token-guard] Model: sonnet. Task: feature implementation. ✓ correct model.
```
or
```
[token-guard] Model: opus. Task: README edit. Consider switching to haiku.
```
