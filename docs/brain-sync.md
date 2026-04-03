# brain-sync — Skill Documentation

Syncs the Local Brain vault (git repo) at the start and end of every Claude Code and Cursor session.

## How it works

| Event | Action |
|-------|--------|
| Session start | `git pull --rebase` |
| Session end | `git add -A && git commit && git push` |

- **Cursor:** `.cursor/rules/brain-sync.mdc` tells the agent to run `sync.sh` at session start/end.
- **Claude Code:** the **`brain-sync`** skill (`skills/brain-sync/`, symlinked as `~/.claude/skills/brain-sync`) documents the same workflow; invoke `/brain-sync` or rely on `CLAUDE.md` + your habits. See [skills.md](skills.md) for symlink layout.

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
├── SKILL.md    ← skill source (Claude Code + Vibe via symlinks)
└── sync.sh     ← bash helper (start / end subcommands)

.claude/skills/brain-sync  → ../../skills/brain-sync   (Claude Code)
.vibe/skills/brain-sync   → ../../skills/brain-sync   (Mistral Vibe)

config/
├── brain.env.example   ← template (tracked)
└── brain.env           ← your config (gitignored)
```

`scripts/install.sh` recreates the skill symlinks for every `skills/*/SKILL.md`.
