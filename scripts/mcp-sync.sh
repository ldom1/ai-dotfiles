#!/usr/bin/env bash
# mcp-sync.sh — (re)apply the centrally-managed MCP servers (qmd, code-index,
# graphify) to the user's global Claude Code (~/.claude.json) and Cursor
# (~/.cursor/mcp.json) configs. Safe to re-run any time.
# Usage: mcp-sync.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-mcp.sh
source "$SCRIPT_DIR/lib-mcp.sh"

setup_central_mcp
