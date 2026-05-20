#!/usr/bin/env bash
# lib-mcp.sh — shared helper for per-project MCP setup
# Source this file, then call: setup_project_mcp <project-path>

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

setup_project_mcp() {
  local project_path="$1"
  local ai_dotfiles
  ai_dotfiles="$(cd "$_LIB_MCP_DIR/.." && pwd)"
  local tpl="$ai_dotfiles/config/brain-templates/mcp-settings.json.tpl"
  local env_file="$ai_dotfiles/config/brain.env"
  local claude_dir="$project_path/.claude"
  local settings="$claude_dir/settings.json"

  if [[ ! -f "$tpl" ]]; then
    echo "[mcp-setup] ERROR: template not found at $tpl" >&2
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
    echo "[mcp-setup] WARN: jq not found — skipping MCP settings merge. Install jq to enable." >&2
    return 0
  fi

  mkdir -p "$claude_dir"

  local mcp_block
  mcp_block=$(sed \
    "s|__PROJECT_PATH__|${project_path}|g; s|__QMD_INDEX_PATH__|${qmd_index_path}|g" \
    "$tpl")

  if [[ -f "$settings" ]]; then
    local merged
    merged=$("$jq_bin" \
      --argjson mcp "$(echo "$mcp_block" | "$jq_bin" '.mcpServers')" \
      '.mcpServers = ((.mcpServers // {}) + $mcp)' \
      "$settings") || { echo "[mcp-setup] ERROR: jq merge failed" >&2; return 1; }
    echo "$merged" > "$settings"
    echo "[mcp-setup] Merged mcpServers into $settings"
  else
    echo "$mcp_block" > "$settings"
    echo "[mcp-setup] Created $settings with mcpServers"
  fi

  echo "[mcp-setup] QMD DB: $qmd_index_path"
  echo "[mcp-setup] code-index-mcp project: $project_path"
  if ! command -v qmd &>/dev/null; then
    echo "[mcp-setup] WARN: qmd CLI not found — run 'npm install -g @tobilu/qmd' then:"
    echo "[mcp-setup]   INDEX_PATH=\"$qmd_index_path\" qmd collection add \"\$BRAIN_PATH\" --name brain"
    echo "[mcp-setup]   INDEX_PATH=\"$qmd_index_path\" qmd embed --collection brain"
  fi
}
