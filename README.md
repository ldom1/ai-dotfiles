# ai-dotfiles

[![CI](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml/badge.svg)](https://github.com/ldom1/ai-dotfiles/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/ldom1/ai-dotfiles?sort=semver)](https://github.com/ldom1/ai-dotfiles/releases)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Wiki](https://img.shields.io/badge/docs-wiki-blue)](https://github.com/ldom1/ai-dotfiles/wiki)

AI skills for Claude Code, Cursor, and Mistral Vibe — plus personal config synced across machines via symlinks.

---

## Install a skill

```
/plugin install brain-sync@ldom1/ai-dotfiles
/plugin install brain-load@ldom1/ai-dotfiles
/plugin install create-pr@ldom1/ai-dotfiles
```

| Skill | Purpose |
|-------|---------|
| [brain-sync](https://github.com/ldom1/ai-dotfiles/wiki/Brain-Sync) | Sync Local Brain Obsidian vault at session start/end |
| [brain-load](https://github.com/ldom1/ai-dotfiles/wiki/Brain-Load) | Load / instantiate project notes from vault |
| [create-pr](https://github.com/ldom1/ai-dotfiles/wiki/Create-PR) | GitHub PR with branch + commit conventions |

**Full documentation → [Wiki](https://github.com/ldom1/ai-dotfiles/wiki)**

---

## Personal setup (quick start)

```bash
git clone git@github.com:<you>/ai-dotfiles.git ~/ai-dotfiles
bash ~/ai-dotfiles/scripts/install.sh
```

`install.sh` symlinks `~/.claude` and `~/.cursor` to this repo, generates `settings.json` from the template, and creates `settings.local.json` if missing. Skills are wired automatically — no plugin install needed for your own machine.

## Design principle

**The AI tools never know about ai-dotfiles.** Files inside `.claude/`, `.cursor/`, `.vibe/` are written as if they are the native config directories (`~/.claude`, `~/.cursor`, etc.). They contain no references to the repo structure, no "ai-dotfiles" framing, no awareness of the versioning layer. Skills invoke scripts via `~/ai-dotfiles/skills/…` because that's the real filesystem path — but config files never explain *why* things are at that path.

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
│       └── rtk-rewrite.sh           # PreToolUse: rtk rewrite + tail cap on noisy output
├── .cursor/
│   └── rules/                       # brain-sync, brain-load, finops-claude (.mdc)
├── .vibe/
│   ├── AGENTS.md                    # Mistral Vibe bootstrap (canonical)
│   ├── README.md                    # Vibe skill discovery and trust
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
├── .github/
│   └── workflows/
│       ├── ci.yml                   # Shellcheck, JSON validation, skill structure
│       └── release.yml              # GitHub Release on v* tags
├── LICENSE
├── CONTRIBUTING.md
├── prompts/
└── scripts/
    └── install.sh                   # Setup script (symlinks, settings, hooks)
```

> **Note — nested `skills/<name>/skills/<name>/SKILL.md`**
>
> Inside each skill folder there is a nested symlink:
> `skills/brain-load/skills/brain-load/SKILL.md → ../../SKILL.md`
>
> This is intentional. The Claude Code marketplace targets the declared source folder
> (`./skills/brain-load`) and looks for a `skills/<name>/SKILL.md` pattern *inside* it.
> The symlink redirects to the real `SKILL.md` — no content is duplicated. **Do not delete it.**

## Sync workflow

```bash
cd ~/ai-dotfiles && git add . && git commit -m "feat(core): short summary" && git push

# On another machine:
git pull && bash scripts/install.sh
```

## Not tracked (machine-specific)

| File | Reason |
|------|--------|
| `.claude/settings.json` | Generated — contains absolute `$HOME` path |
| `.claude/settings.local.json` | Machine-specific permissions |
| `config/brain.env` | Machine-specific vault path |
| `.claude/projects/`, `sessions/`… | Runtime state |

## Dependencies

- [rtk](https://github.com/rtk-ai/rtk) — token-saving proxy (`cargo install rtk`)
- [jq](https://jqlang.github.io/jq/) — required by the rtk hook
- [Obsidian](https://obsidian.md) — for browsing the Local Brain vault

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

[MIT](LICENSE) © Louis Giron
