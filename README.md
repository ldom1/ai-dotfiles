# ai-dotfiles

Personal AI config for Claude Code and Cursor — synced across machines via symlinks.

## Structure

```
ai-dotfiles/
├── .claude/
│   ├── CLAUDE.md                   # Global Claude instructions (with @-includes)
│   ├── LocalBrain.md               # Local Brain vault instructions
│   ├── RTK.md                      # RTK token-saving proxy instructions
│   ├── settings.json.tpl           # Claude Code settings (HOME placeholder)
│   ├── settings.local.json.example # Machine-specific permissions template
│   └── hooks/
│       └── rtk-rewrite.sh          # Pre-tool hook: rewrites commands through rtk
├── .cursor/
│   └── rules/                      # Cursor rules (.mdc files)
├── skills/                         # Private Claude Code skills
├── prompts/                        # Reusable prompts
├── scripts/
│   └── install.sh                  # Setup script
└── .gitignore
```

## Setup on a new machine

```bash
git clone git@github.com:<you>/ai-dotfiles.git ~/ai-dotfiles
bash ~/ai-dotfiles/scripts/install.sh
```

What `install.sh` does:
1. Symlinks `~/.claude` → `~/ai-dotfiles/.claude`
2. Symlinks `~/.cursor` → `~/ai-dotfiles/.cursor`
3. Generates `~/.claude/settings.json` from `settings.json.tpl` (injects `$HOME`)
4. Creates `~/.claude/settings.local.json` from example if not present

## Sync workflow

Changes to `~/.claude/` and `~/.cursor/` **are** changes to `~/ai-dotfiles/` (symlinks).

```bash
# Push changes
cd ~/ai-dotfiles
git add .
git commit -m "update config"
git push

# Pull on another machine
cd ~/ai-dotfiles
git pull
# Re-run install if settings.json.tpl changed:
bash scripts/install.sh
```

## Machine-specific files (not tracked)

| File | Why not tracked |
|------|----------------|
| `.claude/settings.json` | Generated from `.tpl` — contains absolute `$HOME` path |
| `.claude/settings.local.json` | Machine-specific permissions |
| `.claude/projects/`, `sessions/`, etc. | Runtime state |

## Dependencies

- [rtk](https://github.com/rtk-ai/rtk) — token-saving proxy (`cargo install rtk`)
- [jq](https://jqlang.github.io/jq/) — required by the rtk hook
- Claude Code plugins: `superpowers`, `frontend-design`, `code-simplifier`
