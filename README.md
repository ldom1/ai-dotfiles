# ai-dotfiles

Personal AI config for Claude Code, Cursor, and Mistral Vibe — synced across machines via symlinks. Repository docs are in **English**.

## Skills

**Canonical source:** `skills/<name>/SKILL.md`. **Claude Code** and **Mistral Vibe** see each skill via **symlinks** from `.claude/skills/` and `.vibe/skills/` (created by `scripts/install.sh` for every folder under `skills/` that has a `SKILL.md`). Full layout: [docs/skills.md](docs/skills.md).

**Cursor** does not use `SKILL.md` discovery. Local Brain automation lives in `.cursor/rules/` (e.g. `brain-sync.mdc`, `brain-load.mdc`) — those are rules, not symlinks into `skills/`.

### Claude Code (optional marketplace)

If you use `install.sh`, skills are already on disk under `~/.claude/skills/` — you normally **do not** need plugin installs for `brain-sync` / `brain-load` / `create-pr`.

Optional — same skills from the registry elsewhere:

```
/plugin marketplace add ldom1/ai-dotfiles
/plugin install brain-sync@ldom1/ai-dotfiles
/plugin install brain-load@ldom1/ai-dotfiles
```

### Mistral Vibe

Skills are discovered from `.vibe/skills/` (and other [standard paths](https://docs.mistral.ai/mistral-vibe/agents-skills)). Vibe lists them as **`available_skills`**; the **`skill`** tool injects a chosen `SKILL.md`. This repo symlinks every skill from `skills/` into `.vibe/skills/`. See [.vibe/README.md](.vibe/README.md) and [docs/mistral-vibe.md](docs/mistral-vibe.md).

**Session start:** Vibe does not auto-run shell. Instructions live in [`.vibe/AGENTS.md`](.vibe/AGENTS.md); root [`AGENTS.md`](AGENTS.md) is a **symlink** so Vibe’s loader (which only looks for `AGENTS.md` on cwd → trust root, not under `.vibe/` alone) still finds them. Details: [docs/mistral-vibe.md](docs/mistral-vibe.md) (*Brain-sync / brain-load at session start*).

## Quick start

```bash
git clone git@github.com:<you>/ai-dotfiles.git ~/ai-dotfiles
bash ~/ai-dotfiles/scripts/install.sh
```

`install.sh` symlinks `~/.claude` and `~/.cursor` to this repo, generates `settings.json` from the template, and creates `settings.local.json` if missing.

## Design principle

**The AI tools never know about ai-dotfiles.** Files inside `.claude/`, `.cursor/`, `.vibe/` are written as if they are the native config directories (`~/.claude`, `~/.cursor`, etc.). They contain no references to the repo structure, no "ai-dotfiles" framing, no awareness of the versioning layer. The only things that know about ai-dotfiles are:

- **This README** and the repo-level docs (`docs/`, `scripts/`)
- **The Local Brain** vault notes (`projects/ai-dotfiles.md`, `resources/knowledge/operational/claude-setup.md`)
- **`install.sh`** which creates the symlinks

Skills invoke scripts via `~/ai-dotfiles/skills/…` because that's the real filesystem path — but config files never explain *why* things are at that path.

## Structure

```
ai-dotfiles/
├── AGENTS.md                        # symlink → .vibe/AGENTS.md (Vibe discovery)
├── .claude/
│   ├── CLAUDE.md                    # Global instructions (tool-native, no ai-dotfiles refs)
│   ├── LocalBrain.md                # Vault layout pointer
│   ├── RTK.md                       # RTK reference
│   ├── skills/                      # symlinks → ../../skills/<name> (Claude Code)
│   ├── settings.json.tpl            # Settings template (HOME placeholder)
│   ├── settings.local.json.example  # Machine-specific permissions template
│   └── hooks/
│       └── rtk-rewrite.sh           # PreToolUse Bash: rtk rewrite + FinOps tail on noisy cmds
├── .cursor/
│   └── rules/                       # brain-sync, brain-load, finops-claude (.mdc)
├── .vibe/
│   ├── AGENTS.md                    # Mistral Vibe + agent bootstrap (canonical)
│   ├── README.md                    # Vibe: skill tool, available_skills, trust
│   └── skills/                      # Symlinks → skills/* (Mistral Vibe discovery)
├── skills/
│   ├── brain-sync/                  # Sync Local Brain at session start/end
│   ├── brain-load/                  # Load / instantiate Local Brain project notes
│   └── create-pr/                   # /create-pr — gh + git conventions (ai-dotfiles)
├── config/
│   ├── brain.env.example            # Local Brain path template
│   └── brain.env                    # Your config (gitignored)
├── docs/
│   ├── local-brain.md               # Local Brain full setup guide
│   ├── skills.md                    # skills/ layout, symlinks, Cursor vs Claude/Vibe
│   ├── brain-sync.md               # brain-sync skill documentation
│   ├── mistral-vibe.md              # Mistral Vibe skills and config
│   └── git-commits.md               # Commit message conventions
├── prompts/                         # Reusable prompts
└── scripts/
    └── install.sh                   # Setup script
```

## Sync workflow

Because `~/.claude` and `~/.cursor` are symlinks into this repo, all changes are tracked automatically. The AI tools see their standard config paths; ai-dotfiles is invisible to them.

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
| Skills — `skills/`, symlinks, Claude / Vibe / Cursor | [docs/skills.md](docs/skills.md) |
| Local Brain — Obsidian vault as persistent memory | [docs/local-brain.md](docs/local-brain.md) |
| brain-sync — auto-sync vault at session start/end | [docs/brain-sync.md](docs/brain-sync.md) |
| Mistral Vibe — skills, `skill` tool, `.vibe/skills/` | [docs/mistral-vibe.md](docs/mistral-vibe.md), [.vibe/README.md](.vibe/README.md) |
| Git — commit message conventions | [docs/git-commits.md](docs/git-commits.md) |

## Dependencies

- [rtk](https://github.com/rtk-ai/rtk) — token-saving proxy (`cargo install rtk`)
- [jq](https://jqlang.github.io/jq/) — required by the rtk hook
- [Obsidian](https://obsidian.md) — for browsing the Local Brain vault
- Claude Code plugins: `superpowers`, `frontend-design`, `code-simplifier`
