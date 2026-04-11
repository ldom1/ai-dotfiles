#!/bin/bash
# brain-route — session entry point that routes to brain-audit or brain-load

set -euo pipefail

# Colors for output
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly BLUE='\033[0;34m'
readonly NC='\033[0m' # No Color

# Load config loader
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

# Verify BRAIN_PATH is valid
if [[ ! -d "$BRAIN_PATH" ]]; then
    echo "[brain-route] ERROR: BRAIN_PATH is not a directory: $BRAIN_PATH" >&2
    exit 1
fi

if [[ ! -d "$BRAIN_PATH/.git" ]]; then
    echo "[brain-route] ERROR: BRAIN_PATH is not a git repository: $BRAIN_PATH" >&2
    exit 1
fi

# Export BRAIN_PATH for child processes
export BRAIN_PATH

# Helper function: check if maintenance was done recently
_check_maintenance_age() {
    local meta_file="$BRAIN_PATH/meta/last-maintenance.md"

    if [[ ! -f "$meta_file" ]]; then
        # No maintenance record found
        return 1
    fi

    # Extract timestamp from first line (format: YYYY-MM-DD HH:MM:SS)
    local last_timestamp
    last_timestamp=$(head -n 1 "$meta_file" | grep -oE "[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}" || echo "")

    if [[ -z "$last_timestamp" ]]; then
        return 1
    fi

    # Convert to epoch
    local last_epoch
    last_epoch=$(date -d "$last_timestamp" +%s 2>/dev/null || echo "0")

    if [[ "$last_epoch" == "0" ]]; then
        return 1
    fi

    # Get current epoch
    local current_epoch
    current_epoch=$(date +%s)

    # Calculate days since maintenance
    local days_since=$(( (current_epoch - last_epoch) / 86400 ))

    # Return 0 if more than 7 days, 1 if less
    if (( days_since > 7 )); then
        return 0
    else
        return 1
    fi
}

# Helper function: count unprocessed files in /raw/
_count_unprocessed_files() {
    local raw_dir="$BRAIN_PATH/raw"

    if [[ ! -d "$raw_dir" ]]; then
        echo 0
        return 0
    fi

    # Count all files recursively (excluding directories)
    local count
    count=$(find "$raw_dir" -type f 2>/dev/null | wc -l)
    echo "$count"
}

# Evaluate decision rules
session_mode="NORMAL"
decision_reason=""

# Rule 1: Check maintenance age (>7 days since last maintenance)
if _check_maintenance_age; then
    session_mode="MAINTENANCE"
    decision_reason="Last maintenance was >7 days ago"
fi

# Rule 2: Check unprocessed files (>50 in /raw/)
if [[ "$session_mode" == "NORMAL" ]]; then
    local unprocessed_count
    unprocessed_count=$(_count_unprocessed_files)
    if (( unprocessed_count > 50 )); then
        session_mode="MAINTENANCE"
        decision_reason="Found $unprocessed_count unprocessed files (threshold: 50)"
    fi
fi

# Rule 3: Check for --maintenance flag
if [[ "$session_mode" == "NORMAL" ]]; then
    for arg in "$@"; do
        if [[ "$arg" == "--maintenance" ]]; then
            session_mode="MAINTENANCE"
            decision_reason="User specified --maintenance flag"
            break
        fi
    done
fi

# Set default reason if still NORMAL
if [[ "$session_mode" == "NORMAL" && -z "$decision_reason" ]]; then
    decision_reason="Standard session load"
fi

# Export session variables
export session_mode
export decision_reason

# Log output with timestamp
timestamp=$(date '+%Y-%m-%d %H:%M:%S')
echo -e "${BLUE}[brain-route]${NC} Session routing at $timestamp"
echo -e "${BLUE}[brain-route]${NC} Mode: ${GREEN}$session_mode${NC}"
echo -e "${BLUE}[brain-route]${NC} Reason: $decision_reason"
echo ""

# Route to appropriate script
if [[ "$session_mode" == "MAINTENANCE" ]]; then
    echo -e "${YELLOW}[brain-route]${NC} Routing to brain-audit..."
    # Execute brain-audit
    if command -v brain-audit &> /dev/null; then
        exec brain-audit
    else
        # Fallback to script path
        exec "$script_dir/../../../skills/brain-audit/scripts/audit.sh" "$@"
    fi
else
    echo -e "${YELLOW}[brain-route]${NC} Routing to brain-load..."
    # Execute brain-load
    if command -v brain-load &> /dev/null; then
        exec brain-load
    else
        # Fallback to script path
        exec "$script_dir/../../../skills/brain-load/scripts/load.sh" "$@"
    fi
fi

exit 0
