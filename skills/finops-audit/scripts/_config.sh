#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail
# Configuration helper for finops-audit

# Resolve BRAIN_PATH
if [[ -f ~/ai-dotfiles/config/brain.env ]]; then
  BRAIN_PATH=$(grep BRAIN_PATH ~/ai-dotfiles/config/brain.env | cut -d= -f2)
else
  echo "Error: ~/ai-dotfiles/config/brain.env not found" >&2
  exit 1
fi

# Load ~/.claude/finops.json if it exists (separate from Claude Code settings.json)
JSON_REPORT_PATH="${HOME}/.claude/reports"
JSON_FILENAME_PATTERN="token-report-{date}.json"
# Claude Code Pro has ~44,000 tokens per 5-hour window
SESSION_TOKEN_BUDGET=44000
INCLUDE_ALL_TIME_TOTALS=true

if [[ -f ~/.claude/finops.json ]] && jq empty ~/.claude/finops.json 2>/dev/null; then
  # Safely load config with proper defaults
  JSON_REPORT_PATH=$(jq -r '.finops.json_report_path // empty' ~/.claude/finops.json 2>/dev/null) || true
  [[ -z "$JSON_REPORT_PATH" ]] && JSON_REPORT_PATH="${HOME}/.claude/reports"

  JSON_FILENAME_PATTERN=$(jq -r '.finops.json_report_filename_pattern // empty' ~/.claude/finops.json 2>/dev/null) || true
  [[ -z "$JSON_FILENAME_PATTERN" ]] && JSON_FILENAME_PATTERN="token-report-{date}.json"

  SESSION_TOKEN_BUDGET=$(jq -r '.finops.session_token_budget // empty' ~/.claude/finops.json 2>/dev/null) || true
  [[ -z "$SESSION_TOKEN_BUDGET" ]] && SESSION_TOKEN_BUDGET=44000

  INCLUDE_ALL_TIME_TOTALS=$(jq -r '.finops.include_all_time_totals // empty' ~/.claude/finops.json 2>/dev/null) || true
  [[ -z "$INCLUDE_ALL_TIME_TOTALS" ]] && INCLUDE_ALL_TIME_TOTALS=true
fi

# Expand ~ in paths
JSON_REPORT_PATH="${JSON_REPORT_PATH/\~/$HOME}"

# Validate required config
if [[ -z "$BRAIN_PATH" ]]; then
  echo "Error: BRAIN_PATH is empty" >&2
  exit 1
fi

# Validate filename pattern
if [[ ! "$JSON_FILENAME_PATTERN" == *"{date}"* ]]; then
  echo "Error: JSON_FILENAME_PATTERN must contain {date}" >&2
  exit 1
fi

# Add environment variable override chain
JSON_REPORT_PATH="${FINOPS_JSON_REPORT_PATH:-${JSON_REPORT_PATH}}"

# Export for use in main script
export BRAIN_PATH JSON_REPORT_PATH JSON_FILENAME_PATTERN SESSION_TOKEN_BUDGET INCLUDE_ALL_TIME_TOTALS
