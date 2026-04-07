---
name: brain-sync
description: Sync the Local Brain Obsidian vault (git repo) at the start and end of every Claude Code session. Pulls at session start, commits and pushes at session end.
user-invocable: true
---

# brain-sync

Keep the Local Brain vault (a git-backed Obsidian vault) in sync across every session. On session start, pull the latest remote changes. On session end, commit all new notes and push.

## Quick start

```bash
cp reference/brain.env.example brain.env   # standalone
# — or —
cp config/brain.env.example config/brain.env   # full ai-dotfiles install
# Set BRAIN_PATH to the absolute path of your vault
```

Run manually:

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start   # pull
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end     # commit + push
```

## What it does

| Event | Steps |
|---|---|
| **start** | Stash dirty tree → `git pull --rebase` → pop stash |
| **end** | `git add -A` → `git commit -m "brain: session sync <timestamp>"` → `git push` |

## Configuration

`BRAIN_PATH` must be the **absolute path** to a **git repository** (your Obsidian vault). The script loads it from the **first match**:

1. `BRAIN_ENV_FILE` — environment variable pointing to an env file with `BRAIN_PATH=…`
2. `brain.env` beside `scripts/sync.sh` — for standalone usage
3. `config/brain.env` at the ai-dotfiles root — default when using the full install

See `reference/brain.env.example` for the template.

## Autonomous execution rules

Claude Code executes these automatically, without prompting the user.

### Session start (PreSession / SessionStart hook)

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh start
```

**On failure:**
- Rebase conflict → abort rebase, warn user to resolve in `$BRAIN_PATH`, continue session.
- Other pull failure (network, permissions) → restore stash if any, warn user — do **not** label as a rebase conflict.
- No remote → skip pull, log warning, continue.
- Script not found → warn once, continue session.

### Session end (SessionEnd hook)

```bash
bash ~/ai-dotfiles/skills/brain-sync/scripts/sync.sh end
```

**On failure:**
- Nothing to commit → skip commit silently, attempt push for unpushed commits.
- Push rejected / no network → warn: _"brain-sync: push failed — changes are committed locally. Run `git push` in `$BRAIN_PATH` when back online."_
- No remote → skip push silently.

## Edge cases

| Situation | Behavior |
|---|---|
| Dirty tree at pull | Stash → pull → pop |
| Rebase conflict | Abort rebase, warn user, continue |
| Pull failed (no rebase state) | Restore stash if any, warn (permissions/network) |
| No remote | Skip network ops, log warning |
| Nothing to commit | Skip commit, attempt push |
| Push failure | Warn user, leave commit local |
| Script not found | Warn once, continue session |
| No config file | Script exits with hint about BRAIN_ENV_FILE, local brain.env, or ai-dotfiles config/brain.env |

Full edge case detail: `reference/EDGE-CASES.md`.

## Standalone usage

Use **only** the `brain-sync/` folder without the rest of ai-dotfiles:

1. Copy the directory.
2. Place `brain.env` beside `scripts/sync.sh` (copy from `reference/brain.env.example`).
3. Set `BRAIN_PATH` to your vault path (must contain `.git`).
4. Run `bash /path/to/brain-sync/scripts/sync.sh start|end`.

Or set `BRAIN_ENV_FILE` to an existing env file.

## Manual trigger (Mistral Vibe)

Type **`/brain-sync`** to load this skill into the thread. Optionally add `start` or `end` as context for the model. **Running `sync.sh` still requires a bash step** — the slash command does not execute the script.

## Files

```
skills/brain-sync/
├── SKILL.md
├── scripts/
│   └── sync.sh          ← git pull / commit / push logic
└── reference/
    ├── brain.env.example ← copy as brain.env, set BRAIN_PATH
    └── EDGE-CASES.md    ← detailed failure scenarios
```
