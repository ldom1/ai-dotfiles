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

  # Validate input
  if [[ -z "$json_data" || "$json_data" == "{}" ]]; then
    echo '{"all_time":{"tokens":0,"cost_usd":"0.0000"},"year":{"tokens":0,"cost_usd":"0.0000"},"month":{"tokens":0,"cost_usd":"0.0000"},"week":{"tokens":0,"cost_usd":"0.0000"},"day":{"tokens":0,"cost_usd":"0.0000"}}'
    return 0
  fi

  # Get current date and date ranges for calculations
  local today this_month this_year week_start
  today=$(date +%Y-%m-%d)
  this_month=$(date +%Y-%m)
  this_year=$(date +%Y)

  # Calculate week start (days back from today)
  if command -v date &>/dev/null; then
    week_start=$(date -d "$(date +%Y-%m-%d) - $(date +%w) days" +%Y-%m-%d 2>/dev/null || date -v-"$(date +%w)"d +%Y-%m-%d 2>/dev/null || echo "$today")
  else
    week_start="$today"
  fi

  # Try Python first, fall back to grep parsing
  local py_script="/tmp/finops_aggregate_$$.py"
  local result=""

  cat > "$py_script" << 'PYTHON_SCRIPT'
import json
import sys

try:
  data = json.load(sys.stdin)
  if not isinstance(data, dict) or 'daily' not in data:
    sys.exit(1)

  today = sys.argv[1] if len(sys.argv) > 1 else ""
  this_month = sys.argv[2] if len(sys.argv) > 2 else ""
  this_year = sys.argv[3] if len(sys.argv) > 3 else ""
  week_start = sys.argv[4] if len(sys.argv) > 4 else ""

  all_time_tokens = all_time_cost = 0
  year_tokens = year_cost = 0
  month_tokens = month_cost = 0
  week_tokens = week_cost = 0
  day_tokens = day_cost = 0

  for entry in data.get('daily', []):
    date_str = entry.get('date', '')
    tokens = entry.get('totalTokens', 0)
    cost = entry.get('totalCost', 0)

    if not isinstance(tokens, (int, float)) or not isinstance(cost, (int, float)):
      continue

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
    "all_time": {"tokens": int(all_time_tokens), "cost_usd": f"{all_time_cost:.4f}"},
    "year": {"tokens": int(year_tokens), "cost_usd": f"{year_cost:.4f}"},
    "month": {"tokens": int(month_tokens), "cost_usd": f"{month_cost:.4f}"},
    "week": {"tokens": int(week_tokens), "cost_usd": f"{week_cost:.4f}"},
    "day": {"tokens": int(day_tokens), "cost_usd": f"{day_cost:.4f}"}
  }
  print(json.dumps(result, separators=(',', ':')))
except Exception as e:
  sys.stderr.write(f"Error in aggregation: {e}\n")
  sys.exit(1)
PYTHON_SCRIPT

  if command -v python3 &>/dev/null; then
    result=$(echo "$json_data" | python3 "$py_script" "$today" "$this_month" "$this_year" "$week_start" 2>/dev/null)
  fi

  # Fall back to grep if Python failed
  if [[ -z "$result" ]]; then
    result=$(parse_json_with_grep "$json_data" "$today" "$this_month" "$this_year" "$week_start")
  fi

  echo "$result"
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

  [[ -z "$json_data" ]] && echo "[]" && return 0

  local py_script="/tmp/finops_projects_$$.py"
  cat > "$py_script" << 'PYTHON_SCRIPT'
import json
import sys

try:
  data = json.load(sys.stdin)
  if not isinstance(data, dict):
    print("[]")
    sys.exit(0)

  models = {}

  for entry in data.get('daily', []):
    if not isinstance(entry, dict):
      continue
    for model_breakdown in entry.get('modelBreakdowns', []):
      if not isinstance(model_breakdown, dict):
        continue
      model_name = model_breakdown.get('modelName', 'unknown')
      tokens = (model_breakdown.get('inputTokens', 0) or 0) + \
               (model_breakdown.get('outputTokens', 0) or 0) + \
               (model_breakdown.get('cacheCreationTokens', 0) or 0) + \
               (model_breakdown.get('cacheReadTokens', 0) or 0)
      cost = model_breakdown.get('cost', 0) or 0

      if model_name not in models:
        models[model_name] = {'tokens': 0, 'cost': 0}
      models[model_name]['tokens'] += tokens
      models[model_name]['cost'] += cost

  result = []
  for model, data in sorted(models.items()):
    result.append({
      "project": model,
      "tokens": int(data['tokens']),
      "cost_usd": f"{data['cost']:.4f}"
    })

  print(json.dumps(result) if result else "[]")
except Exception as e:
  print("[]")
PYTHON_SCRIPT

  if command -v python3 &>/dev/null; then
    echo "$json_data" | python3 "$py_script" 2>/dev/null || echo "[]"
  else
    echo "[]"
  fi
  rm -f "$py_script"
}

# Build sessions array from JSON daily breakdown
# Extracts recent model usage sessions (last N days)
build_sessions_array() {
  local json_data="$1"

  [[ -z "$json_data" ]] && echo "[]" && return 0

  local py_script="/tmp/finops_sessions_$$.py"
  cat > "$py_script" << 'PYTHON_SCRIPT'
import json
import sys

try:
  data = json.load(sys.stdin)
  if not isinstance(data, dict):
    print("[]")
    sys.exit(0)

  sessions = []
  daily_entries = data.get('daily', [])

  # Process last 10 days
  for entry in daily_entries[-10:]:
    if not isinstance(entry, dict):
      continue
    date = entry.get('date', 'unknown')
    for model_breakdown in entry.get('modelBreakdowns', []):
      if not isinstance(model_breakdown, dict):
        continue
      model_name = model_breakdown.get('modelName', 'unknown')
      tokens = (model_breakdown.get('inputTokens', 0) or 0) + \
               (model_breakdown.get('outputTokens', 0) or 0) + \
               (model_breakdown.get('cacheCreationTokens', 0) or 0) + \
               (model_breakdown.get('cacheReadTokens', 0) or 0)
      cost = model_breakdown.get('cost', 0) or 0
      sessions.append({
        "project": "session",
        "model": model_name,
        "tokens": int(tokens),
        "cost_usd": f"{cost:.4f}",
        "timestamp": date
      })

  # Limit to 20 most recent
  print(json.dumps(sessions[-20:]) if sessions else "[]")
except Exception as e:
  print("[]")
PYTHON_SCRIPT

  if command -v python3 &>/dev/null; then
    echo "$json_data" | python3 "$py_script" 2>/dev/null || echo "[]"
  else
    echo "[]"
  fi
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
  local json_data="$2"
  local timestamp
  local week_start

  # Generate timestamps
  timestamp=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
  week_start=$(date -d "$(date +%Y-%m-%d) - $(date +%w) days" +%Y-%m-%d 2>/dev/null || date -v-"$(date +%w)"d +%Y-%m-%d)

  # Extract actual values from aggregates JSON
  local week_tokens week_cost month_tokens month_cost
  week_tokens=$(echo "$aggregates" | sed -n 's/.*"week":{[^}]*"tokens":\([0-9]*\).*/\1/p')
  week_cost=$(echo "$aggregates" | sed -n 's/.*"week":{[^}]*"cost_usd":"\([^"]*\)".*/\1/p')
  month_tokens=$(echo "$aggregates" | sed -n 's/.*"month":{[^}]*"tokens":\([0-9]*\).*/\1/p')
  month_cost=$(echo "$aggregates" | sed -n 's/.*"month":{[^}]*"cost_usd":"\([^"]*\)".*/\1/p')

  week_tokens=${week_tokens:-0}
  week_cost=${week_cost:-0.00}
  month_tokens=${month_tokens:-0}
  month_cost=${month_cost:-0.00}

  # Format large numbers for readability (e.g., 203684131 -> 203.7M)
  local formatted_week_tokens formatted_month_tokens
  formatted_week_tokens=$(printf "%.1fM" "$(echo "scale=1; $week_tokens / 1000000" | bc 2>/dev/null || echo 0)")
  formatted_month_tokens=$(printf "%.1fM" "$(echo "scale=1; $month_tokens / 1000000" | bc 2>/dev/null || echo 0)")

  # Generate markdown report with actual values
  cat <<MARKDOWN
## Token Audit — Week of $week_start

**Generated:** $(date +%Y-%m-%d)

### Summary
- **Total tokens (week):** $formatted_week_tokens | **Monthly:** $formatted_month_tokens
- **Week cost:** \$$week_cost | **Monthly cost:** \$$month_cost
- **Recommendation:** $(get_recommendation "$week_cost" "$month_cost")

---
MARKDOWN
}

# Generate a recommendation based on spend patterns
get_recommendation() {
  local week_cost="$1"
  local month_cost="$2"

  # Simple heuristic: if costs are low, encourage current practice; if high, suggest optimization
  if (( $(echo "$month_cost > 100" | bc 2>/dev/null || echo 0) )); then
    echo "Review session patterns and consider batching queries for efficiency"
  elif (( $(echo "$week_cost > 20" | bc 2>/dev/null || echo 0) )); then
    echo "Strong activity this week - maintain current cache strategy"
  else
    echo "Low spend - current approach is sustainable"
  fi
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

# Validate we got data
if [[ -z "$SESSION_DATA" || "$SESSION_DATA" == "{}" ]]; then
  echo "Error: No token usage data available. Run a Claude Code session first." >&2
  exit 1
fi

# Aggregate token data
AGGREGATES=$(aggregate_tokens "$SESSION_DATA")

# Validate aggregation
if [[ -z "$AGGREGATES" ]]; then
  echo "Error: Failed to aggregate token data" >&2
  exit 1
fi

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
  MARKDOWN_REPORT=$(format_markdown_report "$AGGREGATES" "$SESSION_DATA")

  if [[ "$QUIET" == "false" ]]; then
    echo "$MARKDOWN_REPORT"
  fi

  append_markdown_to_vault "$MARKDOWN_REPORT"
fi
