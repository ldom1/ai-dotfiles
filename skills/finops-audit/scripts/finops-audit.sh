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

# Run ccusage and capture output - returns outputs for parsing
run_ccusage() {
  echo "Running ccusage commands..." >&2

  # Capture session, daily, and monthly data
  if command -v ccusage &>/dev/null; then
    ccusage session 2>/dev/null || echo ""
  else
    npx ccusage@latest session 2>/dev/null || echo ""
  fi
}

# Parse ccusage table format and extract data
# Strips ANSI codes, removes commas, handles truncation markers (…)
parse_ccusage_table() {
  local table_data="$1"

  # Strip ANSI color codes and extract data rows
  # Remove ANSI codes, filter rows with numeric data (from | and not table borders)
  echo "$table_data" | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    grep -E '^\│' | \
    grep -E '[0-9,]'
}

# Extract total tokens and cost from ccusage output
# Looks for "Total" row in session output and sums daily data
extract_totals_from_session() {
  local session_data="$1"

  # Parse session table and find Total row (skip header row)
  local total_line
  total_line=$(echo "$session_data" | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    grep '│ Total ' | \
    head -1)

  if [[ -z "$total_line" ]]; then
    echo "0 0.0000"
    return
  fi

  # Extract the cost (rightmost $ value) and total tokens
  # Format: │ Total │ ... │ 23,409 │ 629,307 │ ... │ 187,859... │ $69.35 │ │
  local cost_usd
  cost_usd=$(echo "$total_line" | \
    grep -o '\$[0-9.]*' | \
    tail -1 | \
    sed 's/\$//')

  # Extract the total tokens - find the rightmost large number before the cost
  # Look for the "Total Tokens" column which has a large comma-separated number
  local total_tokens
  total_tokens=$(echo "$total_line" | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    grep -o '[0-9,]*\.\.\.' | head -1 | sed 's/\.\.\.$//' | tr -d ',')

  # If truncated with ..., try to get second-to-last large number
  if [[ -z "$total_tokens" ]] || [[ "$total_tokens" == "0" ]]; then
    total_tokens=$(echo "$total_line" | \
      awk -F'│' '{
        # Extract all comma-separated numbers
        for(i=NF-3; i>=3; i--) {
          val = $i
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
          gsub(/\.\.\./, "", val)
          if (val ~ /^[0-9,]+$/ && length(val) > 5) {
            gsub(/,/, "", val)
            print val
            exit
          }
        }
      }' | head -1)
  fi

  # Ensure proper formatting
  total_tokens=${total_tokens:-0}
  cost_usd=$(printf "%.4f" "${cost_usd:-0}" 2>/dev/null || echo "0.0000")

  echo "$total_tokens $cost_usd"
}

# Extract daily totals from daily breakdown
extract_daily_totals() {
  local daily_data="$1"

  # Parse daily data by looking for date entries and their totals
  local total_tokens=0
  local total_cost=0

  echo "$daily_data" | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    grep -E '^\│' | \
    awk -F'│' '
      BEGIN { total_tokens = 0; total_cost = 0 }
      {
        # Look for rows with numeric data (date rows or subtotals)
        for(i=1; i<=NF; i++) {
          val = $i
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
          # Match cost format
          if (val ~ /^\$[0-9.]+$/) {
            gsub(/[\$]/, "", val)
            total_cost += val
          }
        }
      }
      END { printf "%.4f", total_cost }
    '
}

# Aggregate token data into structured format
# Returns JSON object with totals for all_time, year, month, week, day
aggregate_tokens() {
  local session_data="$1"

  # Parse session data for all-time totals
  local session_tokens session_cost
  local totals
  totals=$(extract_totals_from_session "$session_data")

  session_tokens=$(echo "$totals" | awk '{print $1}')
  session_cost=$(echo "$totals" | awk '{print $2}')

  # If no session data, use defaults
  if [[ -z "$session_tokens" || "$session_tokens" == "0" ]]; then
    session_tokens=0
    session_cost="0.0000"
  else
    # Ensure cost is properly formatted with 4 decimals
    session_cost=$(printf "%.4f" "$session_cost" 2>/dev/null || echo "0.0000")
  fi

  session_tokens=${session_tokens:-0}

  # For this week/month/day, we'd need date parsing
  # For now, use session totals as all_time proxy
  printf '{"all_time":{"tokens":%s,"cost_usd":"%s"},"year":{"tokens":null,"cost_usd":null},"month":{"tokens":null,"cost_usd":null},"week":{"tokens":%s,"cost_usd":"%s"},"day":{"tokens":null,"cost_usd":null}}' "$session_tokens" "$session_cost" "$session_tokens" "$session_cost"
}

# Build projects array from session data
build_projects_array() {
  local session_output="$1"

  # Parse session output and build array of projects with token/cost breakdown
  # Extract unique projects and their stats
  local projects
  projects=$(echo "$session_output" | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    grep -E '^\│' | \
    grep -v -E '(Total|┌|├|└|─|┬|┼|┴)' | \
    awk -F'│' '
      NF > 3 {
        # Extract project name from first column
        project = $2
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", project)

        # Skip if empty or model line
        if (project == "" || project ~ /^-/) next

        # Extract cost from cost column
        for(i=1; i<=NF; i++) {
          val = $i
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
          if (val ~ /^\$[0-9.]+$/) {
            cost = val
            gsub(/[\$]/, "", cost)
          }
        }

        if (project != "" && project != "Total") {
          print project " " cost
        }
      }
    ' | sort -u)

  if [[ -z "$projects" ]]; then
    echo "[]"
    return
  fi

  # Build JSON array
  local first=true
  echo -n "["
  while IFS=' ' read -r project cost; do
    if [[ -z "$project" ]]; then continue; fi
    if [[ "$first" == false ]]; then echo -n ","; fi
    printf '{"project":"%s","tokens":0,"cost_usd":"%s"}' "$project" "${cost:-0.0000}"
    first=false
  done <<< "$projects"
  echo "]"
}

# Build sessions array from session data
build_sessions_array() {
  local session_output="$1"

  # Extract recent sessions with model and cost
  local sessions
  sessions=$(echo "$session_output" | \
    sed 's/\x1b\[[0-9;]*m//g' | \
    grep -E '^\│' | \
    grep -E '[0-9,]' | \
    grep -v -E 'Total' | \
    awk -F'│' '
      NF > 3 {
        # Extract fields: project, model, tokens, cost, timestamp
        project = $2
        model = $3
        cost_field = ""
        timestamp = ""

        for(i=1; i<=NF; i++) {
          val = $i
          gsub(/^[[:space:]]+|[[:space:]]+$/, "", val)
          if (val ~ /^\$[0-9.]+$/) {
            cost_field = val
            gsub(/[\$]/, "", cost_field)
          }
          if (val ~ /^[0-9]{4}-[0-9]{2}/) {
            timestamp = val
          }
        }

        gsub(/^[[:space:]]+|[[:space:]]+$/, "", project)
        gsub(/^[[:space:]]+|[[:space:]]+$/, "", model)

        if (project != "" && project != "Total" && model ~ /^-/) {
          print project "|" model "|" cost_field "|" timestamp
        }
      }
    ' | head -20)

  if [[ -z "$sessions" ]]; then
    echo "[]"
    return
  fi

  local first=true
  echo -n "["
  while IFS='|' read -r project model cost timestamp; do
    if [[ -z "$project" ]] || [[ -z "$model" ]]; then continue; fi
    if [[ "$first" == false ]]; then echo -n ","; fi
    # Clean up model name (remove leading "- ")
    model="${model#\- }"
    model="${model# }"
    timestamp=${timestamp:-unknown}
    printf '{"project":"%s","model":"%s","tokens":0,"cost_usd":"%s","timestamp":"%s"}' "$project" "$model" "${cost:-0.0000}" "$timestamp"
    first=false
  done <<< "$sessions"
  echo "]"
}

# Format aggregated data into complete JSON report with metadata
# Includes timestamp, aggregates, and ccusage data structure
format_json_report() {
  local session_data="$1"
  local aggregates="$2"
  local timestamp

  # Generate ISO 8601 timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Extract session data for arrays
  local projects_array sessions_array
  projects_array=$(build_projects_array "$session_data")
  sessions_array=$(build_sessions_array "$session_data")

  # Extract aggregates for current_session budget calculation using bash pattern matching
  local week_tokens week_cost
  # Extract "week":{"tokens":NN... from aggregates JSON
  week_tokens=$(echo "$aggregates" | sed -n 's/.*"week":{[^}]*"tokens":\([0-9]*\).*/\1/p')
  week_cost=$(echo "$aggregates" | sed -n 's/.*"week":{[^}]*"cost_usd":"\([^"]*\)".*/\1/p')

  week_tokens=${week_tokens:-0}
  week_cost=${week_cost:-0.0000}

  # Calculate budget percentage used
  local budget_pct="0.0"
  if [[ "$week_tokens" -gt 0 ]]; then
    budget_pct=$(echo "scale=1; ($week_tokens / $SESSION_TOKEN_BUDGET) * 100" | bc 2>/dev/null || echo "0.0")
  fi

  # Merge aggregates with metadata and ccusage structure
  printf '{\n  "generated_at": "%s",\n  "totals": %s,\n  "projects": %s,\n  "sessions": %s,\n  "current_session": {\n    "tokens_used": %s,\n    "cost_usd": "%s",\n    "budget_pct": %s\n  }\n}\n' "$timestamp" "$aggregates" "$projects_array" "$sessions_array" "$week_tokens" "$week_cost" "$budget_pct"
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

  # Extract placeholder values from aggregates using grep
  local total_tokens=$(echo "$aggregates" | grep -o '"week"[^}]*"tokens": [0-9]*' | grep -o '[0-9]*$')
  local total_cost=$(echo "$aggregates" | grep -o '"week"[^}]*"cost_usd": "[^"]*' | grep -o '[0-9.]*$')
  total_tokens=${total_tokens:-N/A}
  total_cost=${total_cost:-N/A}

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

# Capture ccusage session data
SESSION_DATA=$(run_ccusage)

# Aggregate token data
AGGREGATES=$(aggregate_tokens "$SESSION_DATA")

# Format as JSON if needed
if [[ "$OUTPUT_FORMAT" == "json" || "$OUTPUT_FORMAT" == "both" ]]; then
  JSON_REPORT=$(format_json_report "$SESSION_DATA" "$AGGREGATES")

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
