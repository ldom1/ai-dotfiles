# Claude Module Audit — Design Spec

**Date:** 2026-04-04  
**Status:** approved  
**Scope:** ai-dotfiles `.claude/` module, skills marketplace, install portability

---

## Problem

Three categories of issues identified in the Claude module:

1. **Marketplace blocker** — `create-pr` skill is not published to marketplace (missing `plugin.json`, nested skill symlink, `marketplace.json` entry)
2. **Portability gap** — new machine setup fails silently: `install.sh` never creates `config/brain.env`, hooks never get `BRAIN_PATH`
3. **Quality** — stray "Copy table" artifact in `CLAUDE.md`; `settings.local.json.example` missing common permissions

---

## Changes (approach B — minimal targeted)

### 1. `create-pr` → marketplace

**New files:**

- `skills/create-pr/.claude-plugin/plugin.json`

```json
{
  "name": "create-pr",
  "version": "1.0.0",
  "description": "Open a GitHub PR using gh and ai-dotfiles git conventions (branch prefix, conventional commits)",
  "author": { "name": "Louis Giron", "github": "ldom1" },
  "homepage": "https://github.com/ldom1/ai-dotfiles"
}
```

- `skills/create-pr/skills/create-pr/SKILL.md` → symlink to `../../SKILL.md`
  (mirrors brain-sync and brain-load structure for marketplace loader discovery)

**Modified:**

- `.claude-plugin/marketplace.json` — add `create-pr` entry with `source: "./skills/create-pr"`

### 2. `install.sh` — brain.env bootstrap

**Add step** after "Checking settings.local.json":

```bash
# ── 4. Bootstrap config/brain.env if missing ──────────────────────────────────
BRAIN_ENV="$DOTFILES/config/brain.env"
BRAIN_ENV_EXAMPLE="$DOTFILES/config/brain.env.example"
if [[ ! -f "$BRAIN_ENV" ]]; then
  cp "$BRAIN_ENV_EXAMPLE" "$BRAIN_ENV"
  warn "config/brain.env created — set BRAIN_PATH to your vault path"
else
  log "config/brain.env already exists, skipping"
fi
```

**Update Next steps** — BRAIN_PATH first, then rtk, then permissions, then plugins.

### 3. Quality fixes

- `CLAUDE.md` — remove stray `Copy table` line under Skills section
- `settings.local.json.example` — add `Bash(gh:*)`, `Bash(bash:*)` to allow list
- `docs/create-pr.md` — new short doc matching style of `docs/brain-sync.md`

---

## Files changed

| File | Action |
|------|--------|
| `skills/create-pr/.claude-plugin/plugin.json` | create |
| `skills/create-pr/skills/create-pr/SKILL.md` | create (symlink) |
| `.claude-plugin/marketplace.json` | modify |
| `scripts/install.sh` | modify |
| `.claude/CLAUDE.md` | modify |
| `.claude/settings.local.json.example` | modify |
| `docs/create-pr.md` | create |

---

## Out of scope

- No refactor of existing skills content
- No `AI_DOTFILES` env var documentation (deferred)
- No changes to hooks, RTK, LocalBrain, or Cursor rules
