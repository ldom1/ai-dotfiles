#!/usr/bin/env bash
# install.sh — Set up ai-dotfiles on a new machine
# Usage: bash ~/ai-dotfiles/scripts/install.sh [--dry-run-settings]
#   --dry-run-settings  print the planned settings.json changes and conflicts, change nothing, exit
set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MERGE_SETTINGS=(python3 "$DOTFILES/scripts/merge-settings.py" "$DOTFILES/.claude/settings.json.tpl" "$DOTFILES/.claude/settings.json")

if [[ "${1:-}" == "--dry-run-settings" ]]; then
  exec "${MERGE_SETTINGS[@]}" --dry-run
fi
BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RESET='\033[0m'

log()    { echo -e "${GREEN}✓${RESET} $*"; }
warn()   { echo -e "${YELLOW}!${RESET} $*"; }
header() { echo -e "\n${BOLD}$*${RESET}"; }

# ── 1. Symlinks ────────────────────────────────────────────────────────────────
header "Creating symlinks"

link() {
  local rel="$1"
  local src="$DOTFILES/$rel"
  local dst="$HOME/$rel"

  if [[ -e "$dst" && ! -L "$dst" ]]; then
    # Preserve sensitive files from existing dir before backing it up
    if [[ "$rel" == ".claude" ]]; then
      for f in .credentials.json settings.local.json; do
        if [[ -f "$dst/$f" && ! -f "$src/$f" ]]; then
          cp "$dst/$f" "$src/$f"
          log "Preserved $f → $src/$f"
        fi
      done
    fi
    warn "Backing up $dst → $dst.bak"
    mv "$dst" "$dst.bak"
  fi

  mkdir -p "$(dirname "$dst")"
  ln -sfn "$src" "$dst"
  log "$HOME/$rel → $src"
}

link ".claude"
link ".cursor"

header "Cursor brain hooks"
HOOKS_JSON="$DOTFILES/.cursor/hooks.json"
if [[ -f "$HOOKS_JSON" ]]; then
  chmod +x "$DOTFILES/.cursor/hooks/"*.sh 2>/dev/null || true
  if [[ "$(readlink -f "$HOME/.cursor")" != "$(readlink -f "$DOTFILES/.cursor")" ]]; then
    warn "$HOME/.cursor is not the expected symlink to ai-dotfiles/.cursor"
  else
    log "$HOME/.cursor → ai-dotfiles/.cursor"
  fi
  [[ -x "$DOTFILES/.cursor/hooks/session-start.sh" ]] && log "session-start.sh executable" || warn "session-start.sh not executable"
  [[ -x "$DOTFILES/.cursor/hooks/session-end.sh" ]] && log "session-end.sh executable" || warn "session-end.sh not executable"
  log "hooks.json present"
else
  warn "No .cursor/hooks.json — Cursor brain hooks not installed"
fi

# ── 1b. skills/ → .claude/skills/, .vibe/skills/, .cursor/skills/ (per-skill; coe-* excluded) ─
header "Linking skills (Claude Code + Vibe + Cursor)"

mkdir -p "$DOTFILES/.claude/skills" "$DOTFILES/.vibe/skills" "$DOTFILES/.cursor/skills"
for skill_dir in "$DOTFILES/skills"/*; do
  [[ -d "$skill_dir" ]] || continue
  name=$(basename "$skill_dir")
  [[ "$name" == coe-* ]] && continue
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  ln -sfn "../../skills/$name" "$DOTFILES/.claude/skills/$name"
  ln -sfn "../../skills/$name" "$DOTFILES/.vibe/skills/$name"
  ln -sfn "../../skills/$name" "$DOTFILES/.cursor/skills/$name"
  log "skills/$name → .claude/skills/ + .vibe/skills/ + .cursor/skills/"
done

# ── 1c. AGENTS.md → Cursor rule + Vibe user instructions ─────────────────────
header "Building shared agent rules from AGENTS.md"

bash "$DOTFILES/scripts/build-agent-rules.sh"
mkdir -p "$HOME/.vibe"
ln -sfn "$DOTFILES/.vibe/AGENTS.md" "$HOME/.vibe/AGENTS.md"
log "$HOME/.vibe/AGENTS.md → ai-dotfiles/.vibe/AGENTS.md (Vibe user-level instructions)"

# ── 2. Generate settings.json from template ────────────────────────────────────
header "Generating settings.json"

# merge-settings.py adds the template's owned keys (plugins, marketplaces,
# permissions.deny/ask, env, hooks) to settings.json and keeps local-only
# entries. On a change it keeps settings.json.bak. A semantic conflict
# writes nothing and exits 3.
"${MERGE_SETTINGS[@]}" || {
  rc=$?
  echo "ERROR: settings.json not changed. Resolve the CONFLICT lines above, then run install.sh again." >&2
  exit "$rc"
}
log "settings.json up to date with the template (HOME=$HOME)"

# ── 3. Bootstrap settings.local.json if missing ───────────────────────────────
header "Checking settings.local.json"

LOCAL="$DOTFILES/.claude/settings.local.json"
EXAMPLE="$DOTFILES/.claude/settings.local.json.example"

if [[ ! -f "$LOCAL" ]]; then
  cp "$EXAMPLE" "$LOCAL"
  warn "settings.local.json created from example — edit to add your permissions"
else
  log "settings.local.json already exists, skipping"
fi

# ── 4. Bootstrap config/brain.env if missing ──────────────────────────────────
header "Checking config/brain.env"

BRAIN_ENV="$DOTFILES/config/brain.env"
BRAIN_ENV_EXAMPLE="$DOTFILES/config/brain.env.example"

if [[ ! -f "$BRAIN_ENV" ]]; then
  cp "$BRAIN_ENV_EXAMPLE" "$BRAIN_ENV"
  warn "config/brain.env created from example — edit BRAIN_PATH to your vault path before using Claude Code"
else
  log "config/brain.env already exists, skipping"
fi

# ── 4a. Vault stack rules → .claude/rules/ (load when a matching file is read or edited) ─
header "Linking vault stack rules"

VAULT=$(grep '^BRAIN_PATH=' "$BRAIN_ENV" | head -1 | cut -d= -f2-) || true
if [[ -d "$VAULT/resources/knowledge/patterns" ]]; then
  bash "$DOTFILES/scripts/link-pattern-rules.sh" "$VAULT" "$DOTFILES/.claude/rules"
  log "pattern notes with paths: → .claude/rules/"
else
  warn "BRAIN_PATH has no resources/knowledge/patterns — stack rules not linked"
fi

# ── 4b. Bootstrap config/graphify.env if missing (optional — local uv graphify clone) ─
header "Checking config/graphify.env"

GRAPHIFY_ENV="$DOTFILES/config/graphify.env"
GRAPHIFY_ENV_EXAMPLE="$DOTFILES/config/graphify.env.example"

if [[ ! -f "$GRAPHIFY_ENV" ]]; then
  cp "$GRAPHIFY_ENV_EXAMPLE" "$GRAPHIFY_ENV"
  warn "config/graphify.env created from example — set GRAPHIFY_PROJECT if you use a local graphify checkout + uv"
else
  log "config/graphify.env already exists, skipping"
fi

# ── 5. ai-dotfiles CLI ────────────────────────────────────────────────────────
header "Installing ai-dotfiles CLI"

CLI_SRC="$DOTFILES/bin/ai-dotfiles"
CLI_DST="$HOME/.local/bin/ai-dotfiles"

mkdir -p "$HOME/.local/bin"
chmod +x "$CLI_SRC"
ln -sfn "$CLI_SRC" "$CLI_DST"
log "ai-dotfiles CLI → $CLI_DST (ensure ~/.local/bin is on PATH)"

# ── 6. Hook permissions ────────────────────────────────────────────────────────
header "Setting hook and script permissions"

chmod +x \
  "$DOTFILES/.claude/hooks/rtk-rewrite.sh" \
  "$DOTFILES/.claude/hooks/brain-session-start.sh" \
  "$DOTFILES/.claude/hooks/brain-session-end.sh" \
  "$DOTFILES/.claude/hooks/log-skill-usage.sh" \
  "$DOTFILES/.claude/hooks/git-commit-check.sh" \
  "$DOTFILES/.claude/hooks/stop-check.sh" \
  "$DOTFILES/.claude/hooks/compact-nudge.sh" \
  "$DOTFILES/.claude/hooks/precompact-checkpoint.sh" \
  "$DOTFILES/scripts/build-agent-rules.sh" \
  "$DOTFILES/git-hooks/pre-commit" \
  "$DOTFILES/scripts/init-project.sh" \
  "$DOTFILES/scripts/upgrade-project.sh" \
  "$DOTFILES/scripts/sync-project.sh"
log "hook scripts are executable"

if git -C "$DOTFILES" rev-parse --git-dir >/dev/null 2>&1; then
  git -C "$DOTFILES" config core.hooksPath git-hooks
  log "git core.hooksPath → git-hooks (pre-commit: secrets + Cursor runtime dirs)"
fi

# ── Done ───────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}Done.${RESET} Reload your shell or restart Claude Code.\n"

echo "  Next steps:"
echo "  1. Edit config/brain.env — set BRAIN_PATH to your Obsidian vault (absolute path)"
echo "  2. Optional: edit config/graphify.env — GRAPHIFY_PROJECT if you use a local uv graphify clone"
echo "  3. Install rtk if not present: cargo install rtk"
echo "  4. Edit ~/.claude/settings.local.json to add your machine permissions"
echo "  5. Install Claude Code plugins: claude plugins install superpowers"
