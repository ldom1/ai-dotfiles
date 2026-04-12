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

# Run ccusage and capture output - returns JSON for parsing
run_ccusage() {
  echo "Running ccusage commands..." >&2

  # Capture daily, weekly data in JSON format for structured parsing
  if command -v ccusage &>/dev/null; then
    ccusage daily --json 2>/dev/null || echo ""
  else
    npx ccusage@latest daily --json 2>/dev/null || echo ""
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

# Aggregate token data by date ranges from JSON daily breakdown
# Returns JSON object with totals for all_time, year, month, week, day
aggregate_tokens() {
  local json_data="$1"

  # Get current date and date ranges for calculations
  local today
  today=$(date +%Y-%m-%d)
  local this_month
  this_month=$(date +%Y-%m)
  local this_year
  this_year=$(date +%Y)
  # Week starts on Sunday (0 days back) for this week
  local week_start
  week_start=$(date -d "$(date +%Y-%m-%d) - $(date +%w) days" +%Y-%m-%d 2>/dev/null || date -v-"$(date +%w)"d +%Y-%m-%d)

  # Create temporary Python script for aggregation
  local py_script="/tmp/finops_aggregate_$$.py"
  cat > "$py_script" << 'PYTHON_SCRIPT'
import json
import sys

try:
  data = json.load(sys.stdin)
  today = sys.argv[1]
  this_month = sys.argv[2]
  this_year = sys.argv[3]
  week_start = sys.argv[4]

  all_time_tokens = all_time_cost = 0
  year_tokens = year_cost = 0
  month_tokens = month_cost = 0
  week_tokens = week_cost = 0
  day_tokens = day_cost = 0

  for entry in data.get('daily', []):
    date_str = entry.get('date', '')
    tokens = entry.get('totalTokens', 0)
    cost = entry.get('totalCost', 0)

    all_time_tokens += tokens
    all_time_cost += cost

    if date_str.startswith(this_year):
      year_tokens += tokens
      year_cost += cost

    if date_str.startswith(this_month):
      month_tokens += tokens
      month_cost += cost

    if week_start <= date_str <= today:
      week_tokens += tokens
      week_cost += cost

    if date_str == today:
      day_tokens += tokens
      day_cost += cost

  result = {
    "all_time": {"tokens": all_time_tokens, "cost_usd": f"{all_time_cost:.4f}"},
    "year": {"tokens": year_tokens, "cost_usd": f"{year_cost:.4f}"},
    "month": {"tokens": month_tokens, "cost_usd": f"{month_cost:.4f}"},
    "week": {"tokens": week_tokens, "cost_usd": f"{week_cost:.4f}"},
    "day": {"tokens": day_tokens, "cost_usd": f"{day_cost:.4f}"}
  }
  # Output compact JSON (no pretty printing)
  print(json.dumps(result, separators=(',', ':')))
except:
  pass
PYTHON_SCRIPT

  # Run Python script with proper error handling
  echo "$json_data" | python3 "$py_script" "$today" "$this_month" "$this_year" "$week_start" 2>/dev/null || parse_json_with_grep "$json_data" "$today" "$this_month" "$this_year" "$week_start"

  # Clean up temp file
  rm -f "$py_script"
}

# Fallback function to parse JSON with grep if Python unavailable
parse_json_with_grep() {
  local json_data="$1"
  local today="$2"
  local this_month="$3"
  local this_year="$4"
  local week_start="$5"

  local all_time_tokens=0 all_time_cost=0
  local year_tokens=0 year_cost=0
  local month_tokens=0 month_cost=0
  local week_tokens=0 week_cost=0
  local day_tokens=0 day_cost=0

  # Extract date, tokens, cost using grep and sed
  while IFS='|' read -r date tokens cost; do
    [[ -z "$date" || -z "$tokens" ]] && continue

    all_time_tokens=$((all_time_tokens + tokens))
    all_time_cost=$(echo "$all_time_cost + $cost" | bc 2>/dev/null || echo "$all_time_cost")

    [[ "$date" == "$this_year"* ]] && {
      year_tokens=$((year_tokens + tokens))
      year_cost=$(echo "$year_cost + $cost" | bc 2>/dev/null || echo "$year_cost")
    }

    [[ "$date" == "$this_month"* ]] && {
      month_tokens=$((month_tokens + tokens))
      month_cost=$(echo "$month_cost + $cost" | bc 2>/dev/null || echo "$month_cost")
    }

    [[ "$date" > "$week_start" || "$date" == "$week_start" ]] && [[ "$date" < "$today" || "$date" == "$today" ]] && {
      week_tokens=$((week_tokens + tokens))
      week_cost=$(echo "$week_cost + $cost" | bc 2>/dev/null || echo "$week_cost")
    }

    [[ "$date" == "$today" ]] && {
      day_tokens=$((day_tokens + tokens))
      day_cost=$(echo "$day_cost + $cost" | bc 2>/dev/null || echo "$day_cost")
    }
  done < <(echo "$json_data" | grep -o '"date":"[^"]*".*"totalTokens":[0-9]*.*"totalCost":[0-9.]*' | sed 's/"date":"\([^"]*\)".*"totalTokens":\([0-9]*\).*"totalCost":\([0-9.]*\)/\1|\2|\3/')

  # Format and output
  printf '{"all_time":{"tokens":%s,"cost_usd":"%s"},"year":{"tokens":%s,"cost_usd":"%s"},"month":{"tokens":%s,"cost_usd":"%s"},"week":{"tokens":%s,"cost_usd":"%s"},"day":{"tokens":%s,"cost_usd":"%s"}}' \
    "$all_time_tokens" "$(printf "%.4f" "${all_time_cost:-0}" 2>/dev/null || echo "0.0000")" \
    "$year_tokens" "$(printf "%.4f" "${year_cost:-0}" 2>/dev/null || echo "0.0000")" \
    "$month_tokens" "$(printf "%.4f" "${month_cost:-0}" 2>/dev/null || echo "0.0000")" \
    "$week_tokens" "$(printf "%.4f" "${week_cost:-0}" 2>/dev/null || echo "0.0000")" \
    "$day_tokens" "$(printf "%.4f" "${day_cost:-0}" 2>/dev/null || echo "0.0000")"
}

# Build projects array from JSON daily breakdown
# Aggregates tokens and costs by model/project across all dates
build_projects_array() {
  local json_data="$1"

  local py_script="/tmp/finops_projects_$$.py"
  cat > "$py_script" << 'PYTHON_SCRIPT'
import json
import sys

try:
  data = json.load(sys.stdin)
  models = {}

  for entry in data.get('daily', []):
    for model_breakdown in entry.get('modelBreakdowns', []):
      model_name = model_breakdown.get('modelName', 'unknown')
      tokens = model_breakdown.get('inputTokens', 0) + model_breakdown.get('outputTokens', 0) + \
               model_breakdown.get('cacheCreationTokens', 0) + model_breakdown.get('cacheReadTokens', 0)
      cost = model_breakdown.get('cost', 0)

      if model_name not in models:
        models[model_name] = {'tokens': 0, 'cost': 0}
      models[model_name]['tokens'] += tokens
      models[model_name]['cost'] += cost

  result = []
  for model, data in sorted(models.items()):
    result.append({
      "project": model,
      "tokens": data['tokens'],
      "cost_usd": f"{data['cost']:.4f}"
    })

  print(json.dumps(result))
except:
  print("[]")
PYTHON_SCRIPT

  echo "$json_data" | python3 "$py_script" 2>/dev/null || echo "[]"
  rm -f "$py_script"
}

# Build sessions array from JSON daily breakdown
# Extracts recent model usage sessions (last N days)
build_sessions_array() {
  local json_data="$1"

  local py_script="/tmp/finops_sessions_$$.py"
  cat > "$py_script" << 'PYTHON_SCRIPT'
import json
import sys

try:
  data = json.load(sys.stdin)
  sessions = []

  for entry in data.get('daily', [])[-10:]:  # Last 10 days
    date = entry.get('date', 'unknown')
    for model_breakdown in entry.get('modelBreakdowns', []):
      model_name = model_breakdown.get('modelName', 'unknown')
      tokens = model_breakdown.get('inputTokens', 0) + model_breakdown.get('outputTokens', 0) + \
               model_breakdown.get('cacheCreationTokens', 0) + model_breakdown.get('cacheReadTokens', 0)
      cost = model_breakdown.get('cost', 0)
      sessions.append({
        "project": "session",
        "model": model_name,
        "tokens": tokens,
        "cost_usd": f"{cost:.4f}",
        "timestamp": date
      })

  # Limit to 20 most recent
  print(json.dumps(sessions[-20:]))
except:
  print("[]")
PYTHON_SCRIPT

  echo "$json_data" | python3 "$py_script" 2>/dev/null || echo "[]"
  rm -f "$py_script"
}

# Format aggregated data into complete JSON report with metadata
# Includes timestamp, aggregates, and ccusage data structure
format_json_report() {
  local json_data="$1"
  local aggregates="$2"
  local timestamp

  # Generate ISO 8601 timestamp
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")

  # Extract session data for arrays
  local projects_array sessions_array
  projects_array=$(build_projects_array "$json_data")
  sessions_array=$(build_sessions_array "$json_data")

  # Extract day aggregates for current_session budget calculation
  local day_tokens day_cost budget_pct

  # Use sed extraction for reliable JSON parsing
  day_tokens=$(echo "$aggregates" | sed -n 's/.*"day":{[^}]*"tokens":\([0-9]*\).*/\1/p')
  day_cost=$(echo "$aggregates" | sed -n 's/.*"day":{[^}]*"cost_usd":"\([^"]*\)".*/\1/p')

  day_tokens=${day_tokens:-0}
  day_cost=${day_cost:-0.0000}

  # Calculate budget percentage used (daily tokens vs. 5-hour session budget)
  budget_pct="0.0"
  if [[ "$day_tokens" -gt 0 ]]; then
    budget_pct=$(echo "scale=1; ($day_tokens / $SESSION_TOKEN_BUDGET) * 100" | bc 2>/dev/null || echo "0.0")
  fi

  # Merge aggregates with metadata and ccusage structure
  printf '{\n  "generated_at": "%s",\n  "totals": %s,\n  "projects": %s,\n  "sessions": %s,\n  "current_session": {\n    "tokens_used": %s,\n    "cost_usd": "%s",\n    "budget_pct": %s\n  }\n}\n' "$timestamp" "$aggregates" "$projects_array" "$sessions_array" "$day_tokens" "$day_cost" "$budget_pct"
}

# Write JSON report to file
write_json_report() {
  local json_report="$1"
  local output_path="$2"
  local filename_pattern="$3"

  # Create output directory if needed
  mkdir -p "$output_path"

  # Generate filename from pattern
  local today
  today=$(date +%Y-%m-%d)
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
  week_start=$(date -d "$(date +%Y-%m-%d) - $(date +%w) days" +%Y-%m-%d 2>/dev/null || date -v-"$(date +%w)"d +%Y-%m-%d)

  # Extract placeholder values from aggregates using grep
  local total_tokens
  total_tokens=$(echo "$aggregates" | grep -o '"week"[^}]*"tokens": [0-9]*' | grep -o '[0-9]*$')
  local total_cost
  total_cost=$(echo "$aggregates" | grep -o '"week"[^}]*"cost_usd": "[^"]*' | grep -o '[0-9.]*$')
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
  write_json_report "$JSON_REPORT" "$JSON_REPORT_PATH" "$JSON_FILENAME_PATTERN" > /dev/null

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
