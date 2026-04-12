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

# Aggregate token data into structured format
# Returns JSON object with totals for all_time, year, month, week, day
aggregate_tokens() {
  local ccusage_data="$1"

  # Parse ccusage data and aggregate by time period
  # For now, return structure with null placeholders for Task 8 parsing
  cat <<JSON
{
  "all_time": {
    "tokens": null,
    "cost_usd": null
  },
  "year": {
    "tokens": null,
    "cost_usd": null
  },
  "month": {
    "tokens": null,
    "cost_usd": null
  },
  "week": {
    "tokens": null,
    "cost_usd": null
  },
  "day": {
    "tokens": null,
    "cost_usd": null
  }
}
JSON
}

# Format aggregated data into complete JSON report with metadata
# Includes timestamp, aggregates, and ccusage data structure
format_json_report() {
  local ccusage_data="$1"
  local aggregates="$2"
  local timestamp

  # Generate ISO 8601 timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Merge aggregates with metadata and ccusage structure
  cat <<JSON
{
  "generated_at": "$timestamp",
  "totals": $aggregates,
  "raw_ccusage": $ccusage_data
}
JSON
}

# Write JSON report to file
write_json_report() {
  local json_report="$1"
  local output_path="$2"
  local filename_pattern="$3"

  # Create output directory if needed
  mkdir -p "$output_path"

  # Generate filename from pattern
  local today=$(date +%Y-%m-%d)
  local filename="${filename_pattern/\{date\}/$today}"
  local filepath="$output_path/$filename"

  # Write JSON to file
  echo "$json_report" > "$filepath"

  if [[ "$QUIET" == "false" ]]; then
    echo "JSON report written to: $filepath" >&2
  fi

  echo "$filepath"  # Return filepath for stdout output if needed
}

# Format aggregated data into markdown report
# Generates markdown with week summary, totals, and recommendations
format_markdown_report() {
  local aggregates="$1"
  local timestamp
  local week_start

  # Generate timestamps
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  week_start=$(date -d "$(date +%Y-%m-%d) - $(date +%w) days" +%Y-%m-%d 2>/dev/null || date -v-$(date +%w)d +%Y-%m-%d)

  # Extract placeholder values from aggregates
  local total_tokens=$(echo "$aggregates" | jq -r '.week.tokens // "N/A"')
  local total_cost=$(echo "$aggregates" | jq -r '.week.cost_usd // "N/A"')

  # Generate markdown report with placeholder values
  cat <<'MARKDOWN'
## Token Audit — Week of YYYY-MM-DD

Total tokens: N/A | Sessions: N/A
Top model: claude-3.5-sonnet (N/A% of tokens)
Longest session: N/A — N/A tokens
Hotspot day: N/A (N/A tokens)
Recommendation: Review session patterns and optimize prompt caching for frequently accessed documents.

---
Generated: TIMESTAMP
MARKDOWN
}

# Append markdown report to vault finops history file
# Creates file if it doesn't exist, appends report with section separator
append_markdown_to_vault() {
  local markdown_report="$1"
  local vault_path="$BRAIN_PATH/resources/knowledge/operational/finops-history.md"

  # Create parent directories if needed
  mkdir -p "$(dirname "$vault_path")"

  # Initialize file with header if it doesn't exist
  if [[ ! -f "$vault_path" ]]; then
    cat > "$vault_path" <<'HEADER'
# FinOps Token Spend History

Automated weekly token audits generated by finops-audit skill.

---

HEADER
  fi

  # Append report with separator
  echo "$markdown_report" >> "$vault_path"
  echo "" >> "$vault_path"

  if [[ "$QUIET" == "false" ]]; then
    echo "Markdown report appended to: $vault_path" >&2
  fi
}

# Main execution
check_ccusage

# Capture ccusage data
CCUSAGE_DATA=$(run_ccusage)

# Aggregate token data
AGGREGATES=$(aggregate_tokens "$CCUSAGE_DATA")

# Format as JSON if needed
if [[ "$OUTPUT_FORMAT" == "json" || "$OUTPUT_FORMAT" == "both" ]]; then
  JSON_REPORT=$(format_json_report "$CCUSAGE_DATA" "$AGGREGATES")

  # Write JSON to file if requested
  JSON_FILE=$(write_json_report "$JSON_REPORT" "$JSON_REPORT_PATH" "$JSON_FILENAME_PATTERN")

  if [[ "$OUTPUT_FORMAT" == "json" && "$QUIET" == "false" ]]; then
    echo "$JSON_REPORT"
  fi
fi

# Generate and output markdown if requested
if [[ "$OUTPUT_FORMAT" == "markdown" || "$OUTPUT_FORMAT" == "both" ]]; then
  MARKDOWN_REPORT=$(format_markdown_report "$AGGREGATES")

  if [[ "$QUIET" == "false" ]]; then
    echo "$MARKDOWN_REPORT"
  fi

  append_markdown_to_vault "$MARKDOWN_REPORT"
fi
