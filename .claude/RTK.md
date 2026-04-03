# RTK — token proxy

**rtk** rewrites common dev commands so outputs stay small. The PreToolUse hook calls `rtk rewrite` then applies tail caps on noisy installs/builds.

## How it works

1. **RTK rewrite** — intercepts the command and rewrites it (e.g. adds `--quiet`, pipes through filters, caps output)
2. **Tail-cap** — hard truncation on noisy installs/builds if rewrite is not enough

Hook is defined in `~/ai-dotfiles/.claude/settings.json` (template: `settings.json.tpl`).
RTK must be installed and on PATH — if missing, the hook is a no-op.

## Diagnostic commands

```bash
rtk gain              # savings summary
rtk gain --history
rtk discover          # missed opportunities in Claude history
rtk proxy '<cmd>'     # run without rewrite
rtk --version
```

**Collision:** if `rtk gain` fails, you may have the wrong `rtk` on PATH.

## Full doc

`$BRAIN_PATH/resources/knowledge/operational/rtk.md`
