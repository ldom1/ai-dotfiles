#!/usr/bin/env bash
# install.sh — Set up ai-dotfiles on a new machine
# Usage: bash ~/ai-dotfiles/scripts/install.sh [--dry-run-settings]  (main checkout only, not a worktree)
#   --dry-run-settings  print the planned settings.json changes and conflicts, change nothing, exit
set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MERGE_SETTINGS=(python3 "$DOTFILES/scripts/merge-settings.py" "$DOTFILES/.claude/settings.json.tpl" "$DOTFILES/.claude/settings.json")

case "${1:-}" in
  "") ;;
  --dry-run-settings) exec "${MERGE_SETTINGS[@]}" --dry-run ;;
  *) echo "install.sh: unknown argument: $1 (usage: install.sh [--dry-run-settings])" >&2; exit 2 ;;
esac

# Links point at $DOTFILES: from a linked worktree they would follow it and break when it is removed.
if GIT_DIRS=$(git -C "$DOTFILES" rev-parse --absolute-git-dir --git-common-dir 2>/dev/null); then
  { read -r GIT_DIR; read -r COMMON_DIR; } <<<"$GIT_DIRS"
  COMMON_DIR=$(cd "$DOTFILES" && cd "$COMMON_DIR" && pwd)
  if [[ "$GIT_DIR" != "$COMMON_DIR" ]]; then
    echo "install.sh: $DOTFILES is a linked git worktree. Run install.sh from the main checkout: $(dirname "$COMMON_DIR")" >&2
    exit 2
  fi
fi
BOLD='\033[1m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; RESET='\033[0m'

log()    { echo -e "${GREEN}✓${RESET} $*"; }
warn()   { echo -e "${YELLOW}!${RESET} $*"; }
header() { echo -e "\n${BOLD}$*${RESET}"; }
# Warnings repeated at the end, so they stay visible after a long run
END_WARNINGS=()
warn_end() { warn "$*"; END_WARNINGS+=("$*"); }

# ── 1. Symlinks ────────────────────────────────────────────────────────────────
header "Creating symlinks"

link() {
  local rel="$1"
  local src="$DOTFILES/$rel"
  local dst="$HOME/$rel"

  # WSL: ~/.claude can be a bind mount of $src (scripts/wsl-claude-mount.sh); keep it.
  if [[ -d "$dst" && ! -L "$dst" && "$dst" -ef "$src" ]]; then
    log "$dst is a bind mount of $src"
    return
  fi
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

# Private skills: a separate private repo cloned into private/ (gitignored). Each <tool>/skills/
# gets an untracked, self-ignoring .gitignore listing their links, so the public repo never
# tracks or names them (a nested .gitignore also beats .cursor/.gitignore's `!skills/**`).
for skill_dir in "$DOTFILES/private/skills"/*; do
  [[ -f "$skill_dir/SKILL.md" ]] || continue
  name=$(basename "$skill_dir")
  [[ -e "$DOTFILES/skills/$name" ]] && { warn "private/skills/$name skipped: skills/$name exists"; continue; }
  for tool in .claude .vibe .cursor; do
    ln -sfn "../../private/skills/$name" "$DOTFILES/$tool/skills/$name"
    ignore="$DOTFILES/$tool/skills/.gitignore"
    for entry in /.gitignore "/$name"; do
      grep -qxF "$entry" "$ignore" 2>/dev/null || echo "$entry" >> "$ignore"
    done
  done
  log "private/skills/$name → .claude/skills/ + .vibe/skills/ + .cursor/skills/ (private)"
done

# ── 1c. AGENTS.md → Cursor rule + Vibe user instructions ─────────────────────
header "Building shared agent rules from AGENTS.md"

bash "$DOTFILES/scripts/build-agent-rules.sh"
mkdir -p "$HOME/.vibe"
ln -sfn "$DOTFILES/.vibe/AGENTS.md" "$HOME/.vibe/AGENTS.md"
log "$HOME/.vibe/AGENTS.md → ai-dotfiles/.vibe/AGENTS.md (Vibe user-level instructions)"
ln -sfn "$DOTFILES/.vibe/user-hooks.toml" "$HOME/.vibe/hooks.toml"
log "$HOME/.vibe/hooks.toml → ai-dotfiles/.vibe/user-hooks.toml (Vibe hooks: hardline, commit-scope, stop-check)"

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

# statusLine: drop the aif-statusline wrapper of the removed ai-dotdeck (it chained the real
# command). merge-settings.py does not own statusLine.
SETTINGS="$DOTFILES/.claude/settings.json"
if [[ "$(jq -r '.statusLine.command // ""' "$SETTINGS")" =~ (^|/)aif-statusline( |$) ]]; then
  sl_tmp=$(mktemp "$SETTINGS.XXXXXX")
  jq '.statusLine.command |= sub("^\\S*aif-statusline ?"; "") | if .statusLine.command == "" then del(.statusLine) else . end' \
    "$SETTINGS" > "$sl_tmp" && cp "$SETTINGS" "$SETTINGS.bak" && mv "$sl_tmp" "$SETTINGS"
  log "statusLine: aif-statusline wrapper removed"
fi

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

VAULT=$(grep '^BRAIN_PATH=' "$BRAIN_ENV" | head -1 | cut -d= -f2- | tr -d '"') || true
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

mkdir -p "$HOME/.local/bin"
for cli in ai-dotfiles stop-check-trust local-ci aif-agent-hook vibe-brain; do
  chmod +x "$DOTFILES/bin/$cli"
  ln -sfn "$DOTFILES/bin/$cli" "$HOME/.local/bin/$cli"
  log "$cli → $HOME/.local/bin/$cli (ensure ~/.local/bin is on PATH)"
done

# Terminal init: ~/.zshenv (non-interactive login zsh: Orca starts agents through it), ~/.zshrc and
# ~/.bashrc source config/shell-init.sh (PATH). Without either rc file, create the login shell's one.
init_line="[ -f \"$DOTFILES/config/shell-init.sh\" ] && . \"$DOTFILES/config/shell-init.sh\"  # ai-dotfiles terminal init"
rcs=()
{ command -v zsh >/dev/null 2>&1 || [[ -f $HOME/.zshenv ]]; } && rcs+=("$HOME/.zshenv")
for rc in "$HOME/.zshrc" "$HOME/.bashrc"; do [[ -f $rc ]] && rcs+=("$rc"); done
[[ -f $HOME/.zshrc || -f $HOME/.bashrc ]] || rcs+=("$HOME/.$(basename "${SHELL:-bash}")rc")
for rc in "${rcs[@]}"; do
  if grep -qF 'config/shell-init.sh' "$rc" 2>/dev/null; then
    log "$rc already sources config/shell-init.sh"
  else
    printf '\n%s\n' "$init_line" >> "$rc"
    log "$rc sources config/shell-init.sh (~/.local/bin on PATH)"
  fi
done

# Platform layer: bin/aif-platform holds every WSL / native Linux difference (AIF_PLATFORM forces it).
chmod +x "$DOTFILES/bin/aif-platform"
ln -sfn "$DOTFILES/bin/aif-platform" "$HOME/.local/bin/aif-platform"
AIF_OS=$("$DOTFILES/bin/aif-platform" name)
log "platform: $AIF_OS"
if [[ "$AIF_OS" == wsl && -L "$HOME/.claude" ]]; then
  warn_end "$HOME/.claude is a symlink: Windows apps (Orca's agent session history) cannot read it. Close Claude sessions, then run: bash $DOTFILES/scripts/wsl-claude-mount.sh"
fi

# Obsidian CLI (WSL): the obsidian-cli skill calls `obsidian`; on WSL it is the Windows Obsidian.com.
# Linked into ~/.local/bin; a real file there is kept. Native Linux: Obsidian's own package provides it.
obsidian_exe=$(compgen -G "${AIF_WIN_USERS:-/mnt/c/Users}/*/AppData/Local/Programs/Obsidian/Obsidian.com" | head -n 1 || true)
if [[ "$AIF_OS" == wsl && -n "$obsidian_exe" && ( -L "$HOME/.local/bin/obsidian" || ! -e "$HOME/.local/bin/obsidian" ) ]]; then
  ln -sfn "$obsidian_exe" "$HOME/.local/bin/obsidian"
  log "obsidian → $obsidian_exe"
fi

need_cmds() {  # need_cmds "<apt packages>" cmd...: warn once with the apt line for missing commands
  local pkgs=$1 missing=(); shift
  for c in "$@"; do command -v "$c" >/dev/null 2>&1 || missing+=("$c"); done
  (( ${#missing[@]} == 0 )) || warn_end "missing ${missing[*]}. Run: sudo apt install $pkgs"
}
need_cmds "jq curl" jq curl

# Orca, the agent cockpit: scripts/orca-install.sh installs it on native Ubuntu (.deb, never when
# already installed), applies config/orca/settings.json, checks its CLI and skills. Each stdout
# line is a step to do by hand (the sudo apt line included): repeated in the end warnings.
header "Orca"
while IFS= read -r line; do
  [[ -n $line ]] && warn_end "$line"
done < <(bash "$DOTFILES/scripts/orca-install.sh")

# Statusline: pinned user-prefix install; npx resolves the package on every repaint (~1 s).
CCSTATUSLINE_VERSION=2.2.30
if command -v npm >/dev/null 2>&1; then
  npm i -g --prefix "$HOME/.local" "ccstatusline@$CCSTATUSLINE_VERSION" >/dev/null \
    && log "ccstatusline@$CCSTATUSLINE_VERSION → $HOME/.local/bin/ccstatusline" \
    || warn "ccstatusline install failed — statusline will be empty"
else
  warn "npm not found — install Node, then re-run for the ccstatusline statusline"
fi

# Approve this repo's own Stop check once, so the trust gate stays quiet here.
"$DOTFILES/bin/stop-check-trust" "$DOTFILES" >/dev/null

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
  "$DOTFILES/.claude/statusline-health.sh" \
  "$DOTFILES/.claude/statusline-counts.sh" \
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

if (( ${#END_WARNINGS[@]} )); then
  echo -e "\n${BOLD}${YELLOW}Warnings:${RESET}"
  for w in "${END_WARNINGS[@]}"; do warn "$w"; done
fi
