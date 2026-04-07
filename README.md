# ai-dotfiles

Personal AI config for Claude Code, Cursor, and Mistral Vibe — synced across machines via symlinks. Repository docs are in **English**.

## Skills (installable)

| Skill | Purpose | Install |
|-------|---------|---------|
| brain-sync | Sync Local Brain vault at session start/end | `/plugin install brain-sync@ldom1/ai-dotfiles` |
| brain-load | Load / instantiate project notes from vault | `/plugin install brain-load@ldom1/ai-dotfiles` |
| create-pr | GitHub PR with branch + commit conventions | `/plugin install create-pr@ldom1/ai-dotfiles` |

Full documentation: **[Wiki](https://github.com/ldom1/ai-dotfiles/wiki)**

> **Note — nested `skills/<name>/skills/<name>/SKILL.md`**
>
> Inside each skill folder you will notice a nested structure like:
>
> ```
> skills/brain-load/
> └── skills/
>     └── brain-load/
>         └── SKILL.md → ../../SKILL.md   (symlink)
> ```
>
> This is intentional and required for the Claude Code marketplace. When you run
> `/plugin install brain-load@ldom1/ai-dotfiles`, the marketplace targets the declared
> source folder (`./skills/brain-load`). It then looks for a `skills/<name>/SKILL.md`
> pattern *inside* that folder to locate the skill definition. The symlink is 14 bytes
> and contains no duplicated content — it redirects to the actual `SKILL.md` one level up.
>
> **Do not delete these symlinks.** They are the marketplace discovery mechanism.

---

## Quick start

```bash
git clone git@github.com:<you>/ai-dotfiles.git ~/ai-dotfiles
bash ~/ai-dotfiles/scripts/install.sh
```

`install.sh` symlinks `~/.claude` and `~/.cursor` to this repo, generates `settings.json` from the template, and creates `settings.local.json` if missing.

If you use `install.sh`, skills are already wired under `~/.claude/skills/` — you normally **do not** need the marketplace installs above for your own machine.

## Design principle

**The AI tools never know about ai-dotfiles.** Files inside `.claude/`, `.cursor/`, `.vibe/` are written as if they are the native config directories (`~/.claude`, `~/.cursor`, etc.). They contain no references to the repo structure, no "ai-dotfiles" framing, no awareness of the versioning layer. The only things that know about ai-dotfiles are:

- **This README** and the wiki
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
│   └── skills/                      # symlinks → skills/* (Mistral Vibe discovery)
├── skills/
│   ├── brain-sync/                  # Sync Local Brain at session start/end
│   │   ├── SKILL.md
│   │   ├── scripts/sync.sh
│   │   └── reference/
│   ├── brain-load/                  # Load / instantiate Local Brain project notes
│   │   ├── SKILL.md
│   │   ├── scripts/
│   │   └── reference/
│   └── create-pr/                   # /create-pr — gh + git conventions
│       ├── SKILL.md
│       └── reference/GIT-COMMITS.md
├── config/
│   ├── brain.env.example            # Local Brain path template
│   └── brain.env                    # Your config (gitignored)
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

Commit format: [Git Commit Conventions](https://github.com/ldom1/ai-dotfiles/wiki/Git-Commit-Conventions).

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
| Skills — layout, symlinks, Claude / Vibe / Cursor | [Wiki: Skill Architecture](https://github.com/ldom1/ai-dotfiles/wiki/Skill-Architecture) |
| Local Brain — Obsidian vault as persistent memory | [Wiki: Local Brain Setup](https://github.com/ldom1/ai-dotfiles/wiki/Local-Brain-Setup) |
| brain-sync — auto-sync vault at session start/end | [Wiki: Brain Sync](https://github.com/ldom1/ai-dotfiles/wiki/Brain-Sync) |
| Mistral Vibe — skills, `skill` tool, `.vibe/skills/` | [Wiki: Mistral Vibe](https://github.com/ldom1/ai-dotfiles/wiki/Mistral-Vibe), [.vibe/README.md](.vibe/README.md) |
| Git — commit message conventions | [Wiki: Git Commit Conventions](https://github.com/ldom1/ai-dotfiles/wiki/Git-Commit-Conventions) |

## Dependencies

- [rtk](https://github.com/rtk-ai/rtk) — token-saving proxy (`cargo install rtk`)
- [jq](https://jqlang.github.io/jq/) — required by the rtk hook
- [Obsidian](https://obsidian.md) — for browsing the Local Brain vault
- Claude Code plugins: `superpowers`, `frontend-design`, `code-simplifier`
