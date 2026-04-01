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
    warn "Backing up $dst → $dst.bak"
    mv "$dst" "$dst.bak"
  fi

  mkdir -p "$(dirname "$dst")"
  ln -sfn "$src" "$dst"
  log "~/$rel → $src"
}

link ".claude"
link ".cursor"

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

# ── 4. Hook permissions ────────────────────────────────────────────────────────
header "Setting hook permissions"

chmod +x "$DOTFILES/.claude/hooks/rtk-rewrite.sh"
log "rtk-rewrite.sh is executable"

# ── Done ───────────────────────────────────────────────────────────────────────
echo -e "\n${BOLD}Done.${RESET} Reload your shell or restart Claude Code.\n"

echo "  Next steps:"
echo "  1. Install rtk if not present: cargo install rtk"
echo "  2. Edit ~/.claude/settings.local.json to add your machine permissions"
echo "  3. Install Claude Code plugins: claude plugins install superpowers"
