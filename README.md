# ai-dotfiles

Personal AI config for Claude Code, Cursor, and Mistral Vibe — synced across machines via symlinks. Repository docs are in **English**.

## Try the skills

You can install the skills from this repo directly in Claude Code, claude.ai, or via the API.

### Claude Code

Register this repo as a plugin marketplace:

```
/plugin marketplace add ldom1/ai-dotfiles
```

Then install individual skills:

```
/plugin install brain-sync@ldom1/ai-dotfiles
/plugin install brain-load@ldom1/ai-dotfiles
```

Or browse and install interactively:

1. `/plugin marketplace add ldom1/ai-dotfiles`
2. Select **Browse and install plugins**
3. Select **ldom1/ai-dotfiles**
4. Select the skill you want
5. Select **Install now**

### Mistral Vibe

Skills are discovered from `.vibe/skills/` (and other [standard paths](https://docs.mistral.ai/mistral-vibe/agents-skills)). Vibe lists them as **`available_skills`**; the built-in **`skill`** tool loads a chosen skill’s `SKILL.md` into the conversation when the task matches.

This repo wires `brain-sync` and `brain-load` into `.vibe/skills/` via symlinks to `skills/`. See [.vibe/README.md](.vibe/README.md) (how `skill` / `available_skills` work) and [docs/mistral-vibe.md](docs/mistral-vibe.md) (setup and config pitfalls).

## Quick start

```bash
git clone git@github.com:<you>/ai-dotfiles.git ~/ai-dotfiles
bash ~/ai-dotfiles/scripts/install.sh
```

`install.sh` symlinks `~/.claude` and `~/.cursor` to this repo, generates `settings.json` from the template, and creates `settings.local.json` if missing.

## Structure

```
ai-dotfiles/
├── .claude/
│   ├── CLAUDE.md                    # Global instructions (@-includes RTK, LocalBrain, skills)
│   ├── LocalBrain.md                # Local Brain vault instructions
│   ├── RTK.md                       # RTK token-saving proxy instructions
│   ├── settings.json.tpl            # Settings template (HOME placeholder)
│   ├── settings.local.json.example  # Machine-specific permissions template
│   └── hooks/
│       └── rtk-rewrite.sh           # Pre-tool hook: rewrites commands through rtk
├── .cursor/
│   └── rules/                       # Cursor rules (.mdc files)
├── .vibe/
│   ├── README.md                    # Vibe: skill tool, available_skills, trust
│   └── skills/                      # Symlinks → skills/* (Mistral Vibe discovery)
├── skills/
│   ├── brain-sync/                  # Sync Local Brain at session start/end
│   └── brain-load/                  # Load / instantiate Local Brain project notes
├── config/
│   ├── brain.env.example            # Local Brain path template
│   └── brain.env                    # Your config (gitignored)
├── docs/
│   ├── local-brain.md               # Local Brain full setup guide
│   ├── brain-sync.md                # brain-sync skill documentation
│   ├── mistral-vibe.md              # Mistral Vibe skills and config
│   └── git-commits.md               # Commit message conventions
├── prompts/                         # Reusable prompts
└── scripts/
    └── install.sh                   # Setup script
```

## Sync workflow

Because `~/.claude` and `~/.cursor` are symlinks into this repo, all changes are tracked automatically.

```bash
cd ~/ai-dotfiles && git add . && git commit -m "feat(core): short imperative summary" && git push

# On another machine:
git pull && bash scripts/install.sh   # re-run only if settings.json.tpl changed
```

Commit format: [docs/git-commits.md](docs/git-commits.md).

## Not tracked (machine-specific)

| File | Reason |
|------|--------|
| `.claude/settings.json` | Generated — contains absolute `$HOME` path |
| `.claude/settings.local.json` | Machine-specific permissions |
| `config/brain.env` | Machine-specific vault path |
| `.claude/projects/`, `sessions/`… | Runtime state |

## Components

| Component | Docs |
|-----------|------|
| Local Brain — Obsidian vault as persistent memory | [docs/local-brain.md](docs/local-brain.md) |
| brain-sync — auto-sync vault at session start/end | [docs/brain-sync.md](docs/brain-sync.md) |
| Mistral Vibe — skills, `skill` tool, `.vibe/skills/` | [docs/mistral-vibe.md](docs/mistral-vibe.md), [.vibe/README.md](.vibe/README.md) |
| Git — commit message conventions | [docs/git-commits.md](docs/git-commits.md) |

## Dependencies

- [rtk](https://github.com/rtk-ai/rtk) — token-saving proxy (`cargo install rtk`)
- [jq](https://jqlang.github.io/jq/) — required by the rtk hook
- [Obsidian](https://obsidian.md) — for browsing the Local Brain vault
- Claude Code plugins: `superpowers`, `frontend-design`, `code-simplifier`
