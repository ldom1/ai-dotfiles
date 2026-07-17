#!/usr/bin/env bash
# lib-mcp.sh — shared helper for centrally-managed MCP servers
# Source this file, then call: setup_central_mcp

# Capture directory at source time so it's correct when the function is called later
_LIB_MCP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

_find_jq() {
  # Prefer a jq that actually works (nvm-installed node-jq may shadow /usr/bin/jq)
  for candidate in /usr/bin/jq /usr/local/bin/jq /bin/jq jq; do
    if "$candidate" --version &>/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

# Merge a template's .mcpServers block into $target, fully replacing only the keys
# the template defines; other mcpServers entries and all other top-level keys are
# left untouched. Backs up $target to $target.bak before writing (rolling, not
# accumulating). Creates $target as '{}' first if it doesn't exist yet.
_merge_central_mcp_file() {
  local target="$1" block="$2" jq_bin="$3"

  mkdir -p "$(dirname "$target")"
  if [[ ! -f "$target" ]]; then
    echo '{}' > "$target"
  fi
  cp "$target" "$target.bak"

  local merged
  merged=$("$jq_bin" \
    --argjson mcp "$(echo "$block" | "$jq_bin" '.mcpServers')" \
    '.mcpServers = ((.mcpServers // {}) + $mcp)' \
    "$target") || { echo "[mcp-sync] ERROR: jq merge failed for $target" >&2; return 1; }
  echo "$merged" > "$target"
  echo "[mcp-sync] Synced central MCP servers into $target (backup: $target.bak)"
}

# Idempotently sync the centrally-managed MCP servers (qmd, code-index, graphify for
# Claude Code; qmd for Cursor) into the user's global config files. Safe to call
# repeatedly — each run fully replaces its managed keys with the template's current
# values, leaving any other mcpServers entries untouched.
setup_central_mcp() {
  local ai_dotfiles
  ai_dotfiles="$(cd "$_LIB_MCP_DIR/.." && pwd)"
  local claude_tpl="$ai_dotfiles/config/memory-templates/mcp-central-claude.json.tpl"
  local cursor_tpl="$ai_dotfiles/config/memory-templates/mcp-central-cursor.json.tpl"
  local env_file="$ai_dotfiles/config/brain.env"

  if [[ ! -f "$claude_tpl" ]]; then
    echo "[mcp-sync] ERROR: template not found at $claude_tpl" >&2
    return 1
  fi
  if [[ ! -f "$cursor_tpl" ]]; then
    echo "[mcp-sync] ERROR: template not found at $cursor_tpl" >&2
    return 1
  fi

  # Load QMD_INDEX_PATH from brain.env if not already set
  if [[ -z "${QMD_INDEX_PATH:-}" && -f "$env_file" ]]; then
    # shellcheck source=/dev/null
    source "$env_file"
  fi
  local qmd_index_path="${QMD_INDEX_PATH:-${HOME}/vault-qmd/index.sqlite}"

  local jq_bin
  if ! jq_bin="$(_find_jq)"; then
    echo "[mcp-sync] WARN: jq not found — skipping central MCP sync. Install jq to enable." >&2
    return 0
  fi

  local claude_block cursor_block
  claude_block=$(sed "s|__QMD_INDEX_PATH__|${qmd_index_path}|g" "$claude_tpl")
  cursor_block=$(sed "s|__QMD_INDEX_PATH__|${qmd_index_path}|g" "$cursor_tpl")

  _merge_central_mcp_file "${HOME}/.claude.json" "$claude_block" "$jq_bin"
  _merge_central_mcp_file "${HOME}/.cursor/mcp.json" "$cursor_block" "$jq_bin"

  echo "[mcp-sync] QMD DB: $qmd_index_path"
  if ! command -v qmd &>/dev/null; then
    echo "[mcp-sync] WARN: qmd CLI not found — run 'npm install -g @tobilu/qmd' then:"
    echo "[mcp-sync]   INDEX_PATH=\"$qmd_index_path\" qmd collection add \"\$BRAIN_PATH\" --name brain"
    echo "[mcp-sync]   INDEX_PATH=\"$qmd_index_path\" qmd embed --collection brain"
  fi
  echo "[mcp-sync] Cursor: restart Cursor, open any project, and confirm 'qmd' appears under MCP settings — global mcp.json support is unconfirmed on some versions."
}
