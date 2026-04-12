#!/usr/bin/env bash
# Configuration helper for finops-audit

# Resolve BRAIN_PATH
if [[ -f ~/ai-dotfiles/config/brain.env ]]; then
  BRAIN_PATH=$(grep BRAIN_PATH ~/ai-dotfiles/config/brain.env | cut -d= -f2)
else
  echo "Error: ~/ai-dotfiles/config/brain.env not found" >&2
  exit 1
fi

# Load .claude/settings.json if it exists
JSON_REPORT_PATH="${HOME}/.claude/reports"
JSON_FILENAME_PATTERN="token-report-{date}.json"
SESSION_TOKEN_BUDGET=44000
INCLUDE_ALL_TIME_TOTALS=true

if [[ -f ~/.claude/settings.json ]]; then
  JSON_REPORT_PATH=$(jq -r '.finops.json_report_path // empty' ~/.claude/settings.json 2>/dev/null || echo "$JSON_REPORT_PATH")
  JSON_FILENAME_PATTERN=$(jq -r '.finops.json_report_filename_pattern // empty' ~/.claude/settings.json 2>/dev/null || echo "$JSON_FILENAME_PATTERN")
  SESSION_TOKEN_BUDGET=$(jq -r '.finops.session_token_budget // empty' ~/.claude/settings.json 2>/dev/null || echo "$SESSION_TOKEN_BUDGET")
  INCLUDE_ALL_TIME_TOTALS=$(jq -r '.finops.include_all_time_totals // empty' ~/.claude/settings.json 2>/dev/null || echo "$INCLUDE_ALL_TIME_TOTALS")
fi

# Expand ~ in paths
JSON_REPORT_PATH="${JSON_REPORT_PATH/\~/$HOME}"

# Export for use in main script
export BRAIN_PATH JSON_REPORT_PATH JSON_FILENAME_PATTERN SESSION_TOKEN_BUDGET INCLUDE_ALL_TIME_TOTALS
