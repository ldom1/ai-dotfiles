#!/usr/bin/env bash
# install.sh — Set up ai-dotfiles on a new machine
# Usage: bash ~/ai-dotfiles/scripts/install.sh
set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
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

# ── 1b. skills/ → .claude/skills/ and .vibe/skills/ (Claude + Vibe discovery) ─
header "Linking skills (Claude Code + Vibe)"

mkdir -p "$DOTFILES/.claude/skills" "$DOTFILES/.vibe/skills"
for skill_dir in "$DOTFILES/skills"/*; do
  [[ -d "$skill_dir" ]] || continue
  name=$(basename "$skill_dir")
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  ln -sfn "../../skills/$name" "$DOTFILES/.claude/skills/$name"
  ln -sfn "../../skills/$name" "$DOTFILES/.vibe/skills/$name"
  log "skills/$name → .claude/skills/ + .vibe/skills/"
done

# ── 2. Generate settings.json from template ────────────────────────────────────
header "Generating settings.json"

TPL="$DOTFILES/.claude/settings.json.tpl"
OUT="$DOTFILES/.claude/settings.json"

sed "s|__HOME__|$HOME|g" "$TPL" > "$OUT"
log "settings.json generated (HOME=$HOME)"

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

# ── 5. Hook permissions ────────────────────────────────────────────────────────
header "Setting hook permissions"

chmod +x \
  "$DOTFILES/.claude/hooks/rtk-rewrite.sh" \
  "$DOTFILES/.claude/hooks/brain-session-start.sh" \
  "$DOTFILES/.claude/hooks/brain-session-end.sh"
log "hook scripts are executable"

# ── Done ───────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}Done.${RESET} Reload your shell or restart Claude Code.\n"

echo "  Next steps:"
echo "  1. Edit config/brain.env — set BRAIN_PATH to your Obsidian vault (absolute path)"
echo "  2. Optional: edit config/graphify.env — GRAPHIFY_PROJECT if you use a local uv graphify clone"
echo "  3. Install rtk if not present: cargo install rtk"
echo "  4. Edit ~/.claude/settings.local.json to add your machine permissions"
echo "  5. Install Claude Code plugins: claude plugins install superpowers"
