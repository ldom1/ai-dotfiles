---
name: brain-sync
description: Sync the Local Brain Obsidian vault (git repo) at the start and end of every Claude Code session. Pulls at session start, commits and pushes at session end.
---

# brain-sync

## Purpose

The Local Brain is a git-backed Obsidian vault that serves as Claude's persistent memory and knowledge base. This skill ensures it is always up-to-date by pulling remote changes at session start and pushing local changes at session end.

## Configuration

`BRAIN_PATH` must be an **absolute path** to a **git** repository (your Obsidian vault). The script loads it from the **first match** in this order:

1. **`BRAIN_ENV_FILE`** — path to a file containing `BRAIN_PATH=...`
2. **`brain.env` beside `sync.sh`** — standalone (copy from `brain.env.example` in this folder)
3. **`config/brain.env`** — full ai-dotfiles layout (`skills/brain-sync/sync.sh` → repo root `config/brain.env`)

```bash
BRAIN_PATH=/path/to/your/vault
```

The helper script is `sync.sh` in this directory.

## Standalone usage

You can use **only** the **`brain-sync/`** folder without the rest of ai-dotfiles.

1. Copy the directory (must include `sync.sh`).
2. Add **`brain.env`** next to `sync.sh` with **`BRAIN_PATH`** set to your vault (must contain `.git`).
3. Run:

   ```bash
   bash /path/to/brain-sync/sync.sh start   # pull / rebase
   bash /path/to/brain-sync/sync.sh end     # commit + push
   ```

Or set **`BRAIN_ENV_FILE`** to your env file instead of using a local `brain.env`.

## Autonomous execution rules

Claude Code **must** execute these steps automatically, without prompting the user each time.

### Session start (PreSession)

Run immediately after loading context, before any other work:

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh start
```

**What it does:**
- Stashes any dirty working tree in the vault
- Runs `git pull --rebase` to pull remote changes
- Re-applies the stash

**If it fails:**
- Rebase conflict → rebase is aborted, brain stays at last clean state. Warn the user with: "brain-sync: pull conflict — brain is at its last clean commit. Please resolve manually in $BRAIN_PATH."
- No remote → skip pull silently, log a warning, continue session normally.
- Script not found → warn the user once, then continue session.

### Session end (PostSession)

Run after completing the user's last request, before closing:

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh end
```

**What it does:**
- `git add -A` + `git commit -m "brain: session sync <ISO timestamp>"`
- `git push`

**If it fails:**
- Nothing to commit → skip commit silently, attempt push for any unpushed commits.
- Push rejected / no network → warn the user: "brain-sync: push failed — your changes are committed locally. Run 'git push' in $BRAIN_PATH when back online."
- No remote → skip push silently.

## Edge case summary

| Situation | Behavior |
|---|---|
| Dirty tree at pull | Stash → pull → pop |
| Rebase conflict | Abort rebase, warn user, continue |
| No remote | Skip network ops, log warning |
| Nothing to commit | Skip commit, attempt push |
| Push failure | Warn user, leave commit local |
| Script not found | Warn once, continue session |
| No config file | Script exits with hint: `BRAIN_ENV_FILE`, local `brain.env`, or ai-dotfiles `config/brain.env` |

## Manual trigger

You can also call the skill explicitly:

```
/brain-sync start   # pull only
/brain-sync end     # commit + push only
```

Or call the script directly:

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh start
bash ~/ai-dotfiles/skills/brain-sync/sync.sh end
```
