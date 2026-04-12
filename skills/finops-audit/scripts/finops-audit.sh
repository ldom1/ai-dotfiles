#!/usr/bin/env bash
# shellcheck shell=bash
set -euo pipefail

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_config.sh"

# Validate configuration
if [[ -z "$BRAIN_PATH" || -z "$JSON_REPORT_PATH" ]]; then
  echo "Error: Configuration incomplete" >&2
  exit 1
fi

# Default flags
OUTPUT_FORMAT="markdown"  # markdown, json, both
QUIET=false

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      OUTPUT_FORMAT="json"
      shift
      ;;
    --both)
      OUTPUT_FORMAT="both"
      shift
      ;;
    --quiet)
      QUIET=true
      shift
      ;;
    *)
      echo "Unknown flag: $1" >&2
      exit 1
      ;;
  esac
done

# Check if ccusage is installed
check_ccusage() {
  if ! command -v ccusage &>/dev/null && ! command -v npx &>/dev/null; then
    echo "Error: ccusage not found" >&2
    echo "" >&2
    echo "Install it with:" >&2
    echo "  npm install -g ccusage" >&2
    echo "" >&2
    echo "Or run via npx (no installation needed):" >&2
    echo "  npx ccusage@latest blocks --live" >&2
    exit 1
  fi
}

# Run ccusage and capture output
run_ccusage() {
  local monthly_out daily_out session_out

  echo "Running ccusage commands..." >&2

  # Monthly breakdown
  if command -v ccusage &>/dev/null; then
    monthly_out=$(ccusage monthly --breakdown 2>/dev/null || echo "")
    daily_out=$(ccusage daily --breakdown 2>/dev/null || echo "")
    session_out=$(ccusage session 2>/dev/null || echo "")
  else
    monthly_out=$(npx ccusage@latest monthly --breakdown 2>/dev/null || echo "")
    daily_out=$(npx ccusage@latest daily --breakdown 2>/dev/null || echo "")
    session_out=$(npx ccusage@latest session 2>/dev/null || echo "")
  fi

  # Return as JSON object for easier parsing
  cat <<JSON
{
  "monthly": $(echo "$monthly_out" | jq -s 'add' 2>/dev/null || echo 'null'),
  "daily": $(echo "$daily_out" | jq -s 'add' 2>/dev/null || echo 'null'),
  "session": $(echo "$session_out" | jq -s 'add' 2>/dev/null || echo 'null')
}
JSON
}

# Main execution
check_ccusage

# Capture ccusage data
CCUSAGE_DATA=$(run_ccusage)
