# brain-sync — Skill Documentation

Syncs the Local Brain vault (git repo) at the start and end of every Claude Code and Cursor session.

## How it works

| Event | Action |
|-------|--------|
| Session start | `git pull --rebase` |
| Session end | `git add -A && git commit && git push` |

Both Claude Code and Cursor trigger this automatically via their respective config files.

## Setup

```bash
cp config/brain.env.example config/brain.env
# Set BRAIN_PATH to your vault's absolute path
```

## Manual use

```bash
bash ~/ai-dotfiles/skills/brain-sync/sync.sh start   # pull only
bash ~/ai-dotfiles/skills/brain-sync/sync.sh end     # commit + push
```

## Edge cases

| Situation | Behavior |
|-----------|----------|
| Dirty tree before pull | Stash → pull → pop stash |
| Rebase conflict | Abort rebase, warn user, continue session |
| No remote configured | Skip network ops silently |
| Nothing to commit | Skip commit, attempt push for unpushed commits |
| Push failure | Warn user, leave commit local |

## Files

```
skills/brain-sync/
├── SKILL.md    ← Claude Code skill definition
└── sync.sh     ← bash helper (start / end subcommands)

config/
├── brain.env.example   ← template (tracked)
└── brain.env           ← your config (gitignored)
```
