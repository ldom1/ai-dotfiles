# Claude — Global Configuration

@RTK.md
@LocalBrain.md

## Session lifecycle

Hooks are configured in `~/ai-dotfiles/.claude/settings.json`.

| Event | Hook | Effect |
|---|---|---|
| `SessionStart` | `brain-session-start.sh` | git pull (startup/resume only) + brain-load every start (incl. post-`/clear`, compaction) |
| `SessionEnd` | `brain-session-end.sh` | brain commit + push via `sync.sh end` |

Stdout from SessionStart becomes context. `BRAIN_PATH` is exported to Bash tool processes via `CLAUDE_ENV_FILE` by the SessionStart hook.

**SessionEnd timeout:** defaults to ~1.5s global cap. Set `CLAUDE_CODE_SESSIONEND_HOOKS_TIMEOUT_MS` (e.g. `120000`) in the shell **before** launching Claude Code so `sync.sh end` can finish. The per-hook `timeout` in settings cannot exceed that ceiling. Ref: [SessionEnd docs](https://code.claude.com/docs/en/hooks#sessionend).

**Manual fallback** (if hooks are off):

```bash
# start
bash ~/ai-dotfiles/skills/brain-sync/sync.sh start
bash ~/ai-dotfiles/skills/brain-load/load.sh
# end
bash ~/ai-dotfiles/skills/brain-sync/sync.sh end
```

Note: /brain-sync and /brain-load slash commands only load the SKILL text — they do not replace the hooks.

## Memory

Persistent memory = Local Brain vault at $BRAIN_PATH.

- Source of truth for path: ~/ai-dotfiles/config/brain.env (variable BRAIN_PATH)
- If Bash has not run yet, resolve with: grep BRAIN_PATH ~/ai-dotfiles/config/brain.env
- After SessionStart, BRAIN_PATH is available in Bash tool processes via CLAUDE_ENV_FILE — it is not a model variable for prose interpolation
- Short index: LocalBrain.md (in ~/.claude/)
- Deep knowledge: $BRAIN_PATH/resources/knowledge/

Adjust paths if your clone is not at ~/ai-dotfiles.

## Pitfall registry

`$BRAIN_PATH/resources/knowledge/operational/claude-pitfalls.md` — read before substantive implementation or debugging; treat entries as hard constraints. When the user corrects a mistake, append a short bullet (newest first): context → what was wrong → what to do instead. (Cursor: rule `claude-pitfall.mdc`.)

## Development

Occam’s razor (lex parsimoniae): When several approaches are plausible, prefer the one with fewer assumptions and smaller surface area. Favor structured, simple, human-readable code; avoid spaghetti.

## Bash tool hooks

PreToolUse → Bash (in settings.json.tpl):

- RTK rewrite (if installed) — rewrites commands for safety/efficiency
- tail-cap — truncates noisy install/build output

Details and opt-out: ~/ai-dotfiles/.claude/RTK.md.

## Skills

Plugins may add more slash commands; this list covers ai-dotfiles only.

| Command | Purpose | Notes |
|---|---|---|
| /brain-sync | Vault sync procedure | git work = sync.sh |
| /brain-load | Project note + CAP flow | note text = load.sh |
| /create-pr | GitHub PR with branch + commit conventions | Mainly user-invoked |

## Context discipline

/clear on context switches

In long sessions, when you change theme, topic, or implementation block (new feature area, unrelated refactor, different goal):

- /rename first if you may --resume later
- /clear — prior exploration and tool output should not carry into the next block

## Compaction — earlier than default

Manual: Run /compact before the window feels tight — do not wait for automatic compaction near the limit. When compacting, keep:

- Files changed or in scope
- Open decisions
- Commands to verify (tests/build)
- Failing errors
- Explicit user constraints

Automatic (shell): Set before starting Claude Code:

```bash
export CLAUDE_AUTOCOMPACT_PCT_OVERRIDE=60  # lower % = trigger sooner (range 55–80)
# Optional:
export CLAUDE_CODE_AUTO_COMPACT_WINDOW=...  # cap effective window
```

Too low wastes compaction cycles. Ref: $BRAIN_PATH/resources/knowledge/operational/claude-finops.md.

## FinOps

Precise prompts. Minimal MCP surface. Full reference: $BRAIN_PATH/resources/knowledge/operational/claude-finops.md.
