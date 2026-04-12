#!/bin/bash
# Phase 3: Templated Q&A Queries
# Runs query templates to extract insights from the vault

set -euo pipefail

# Source config
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

# Colors for logging
LOG_PREFIX="[phase-3]"

log_info() { echo "$LOG_PREFIX [INFO] $*"; }
log_error() { echo "$LOG_PREFIX [ERROR] $*" >&2; }
log_result() { echo "$LOG_PREFIX [RESULT] $*"; }

# Verify BRAIN_PATH is valid
if [[ ! -d "$BRAIN_PATH" ]]; then
    log_error "BRAIN_PATH does not exist: $BRAIN_PATH"
    exit 1
fi

if [[ ! -d "$BRAIN_PATH/.git" ]]; then
    log_error "BRAIN_PATH is not a git repository: $BRAIN_PATH"
    exit 1
fi

# Create required directories
log_info "Setting up directories..."
mkdir -p "$BRAIN_PATH/meta/queries"
mkdir -p "$BRAIN_PATH/inbox/qa"

queries_dir="$BRAIN_PATH/meta/queries"
qa_dir="$BRAIN_PATH/inbox/qa"

# Check if queries directory exists and has files
if [[ ! -d "$queries_dir" || $(find "$queries_dir" -maxdepth 1 -type f | wc -l) -eq 0 ]]; then
    log_result "No query templates found in $queries_dir"
    exit 0
fi

query_count=$(find "$queries_dir" -maxdepth 1 -type f | wc -l)
log_info "Found $query_count query template(s)"

# Process each query template
processed=0
created=0
today=$(date -u +%Y-%m-%d)

for query_template in "$queries_dir"/*; do
    if [[ ! -f "$query_template" ]]; then
        continue
    fi

    template_name=$(basename "$query_template")
    query_slug="${template_name%.*}"

    # Read template content
    template_content=$(cat "$query_template")

    # Create result file with timestamp
    result_file="$qa_dir/${query_slug}-${today}.md"

    cat > "$result_file" << EOF
# Q&A Results: $query_slug

**Date:** $today
**Template:** $template_name

## Query Template

$template_content

## Results

[Claude: Please review the query above and provide thoughtful answers based on the current vault state. Consider reviewing the entire vault structure and recent changes to inform your response.]

---

**Next action:** Have Claude complete this Q&A response, then extract insights for action items.
EOF

    created=$((created + 1))
    log_info "Created query result: $(basename "$result_file")"

    processed=$((processed + 1))
done

log_result "Phase 3 complete: $processed query template(s) processed, $created result file(s) created"
exit 0
