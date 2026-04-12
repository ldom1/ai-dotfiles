#!/bin/bash
# Brain-Audit Main Orchestrator
# Coordinates all 4 phases of the audit pipeline

set -euo pipefail

# Source config
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

# Colors for logging
LOG_PREFIX="[audit]"

log_info() { echo "$LOG_PREFIX [INFO] $*"; }
log_error() { echo "$LOG_PREFIX [ERROR] $*" >&2; }
log_banner() { echo ""; echo "================================"; echo "$LOG_PREFIX $*"; echo "================================"; echo ""; }
log_section() { echo ""; echo "$LOG_PREFIX === $* ==="; echo ""; }
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

log_banner "Starting Brain-Audit Pipeline"
audit_start=$(date +%s)
audit_start_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)

log_info "BRAIN_PATH: $BRAIN_PATH"
log_info "Start time: $audit_start_time"

# Create required directories
log_section "Creating Required Directories"
mkdir -p "$BRAIN_PATH/raw"
mkdir -p "$BRAIN_PATH/inbox/drafts"
mkdir -p "$BRAIN_PATH/inbox/connections"
mkdir -p "$BRAIN_PATH/inbox/qa"
mkdir -p "$BRAIN_PATH/meta/queries"
mkdir -p "$BRAIN_PATH/archive/processed"
mkdir -p "$BRAIN_PATH/resources/queries/archive"

log_info "All required directories verified"

# Run Phase 1: Raw Data → Drafts
log_section "Phase 1: Compile (Raw Data → Drafts)"
if bash "$script_dir/compile.sh"; then
    # Count created drafts
    draft_count=$(find "$BRAIN_PATH/inbox/drafts" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d '[:space:]')
    log_result "Phase 1 successful: $draft_count draft(s) created"
else
    log_error "Phase 1 failed"
    exit 1
fi

# Run Phase 2: Connection Detection
log_section "Phase 2: Connect (Orphan Detection & Suggestions)"
if bash "$script_dir/connect.sh"; then
    # Count connection suggestions
    connections_file="$BRAIN_PATH/inbox/connections/suggested-connections.md"
    if [[ -f "$connections_file" ]]; then
        suggestion_count=$(grep -c '^- \`' "$connections_file" 2>/dev/null) || true
        suggestion_count=${suggestion_count:-0}
        log_result "Phase 2 successful: ~$suggestion_count connection suggestion(s) generated"
    else
        suggestion_count=0
        log_result "Phase 2 successful: no connections file generated"
    fi
else
    log_error "Phase 2 failed"
    exit 1
fi

# Run Phase 3: Q&A Queries
log_section "Phase 3: Query (Templated Q&A)"
if bash "$script_dir/qa.sh"; then
    # Count created Q&A files
    qa_count=$(find "$BRAIN_PATH/inbox/qa" -maxdepth 1 -type f 2>/dev/null | wc -l | tr -d '[:space:]')
    log_result "Phase 3 successful: $qa_count Q&A result(s) created"
else
    log_error "Phase 3 failed"
    exit 1
fi

# Run Phase 4: Digest Generation & Clock Reset
log_section "Phase 4: Digest (Synthesis & Clock Reset)"
if bash "$script_dir/digest.sh" "$draft_count" "$suggestion_count" "$qa_count"; then
    log_result "Phase 4 successful: digest generated and maintenance clock reset"
else
    log_error "Phase 4 failed"
    exit 1
fi

# Calculate total duration
audit_end=$(date +%s)
duration=$((audit_end - audit_start))
minutes=$((duration / 60))
seconds=$((duration % 60))

# Print summary
log_banner "Brain-Audit Complete"
echo ""
echo "Summary:"
echo "  Phase 1 (Compile):  $draft_count draft article(s)"
echo "  Phase 2 (Connect):  ~$suggestion_count connection suggestion(s)"
echo "  Phase 3 (Query):    $qa_count Q&A result(s)"
echo "  Phase 4 (Digest):   Digest generated and clock reset"
echo ""
echo "Duration: ${minutes}m ${seconds}s"
echo ""
echo "Next action:"
echo "  1. Review drafts in: $BRAIN_PATH/inbox/drafts/"
echo "  2. Review connections in: $BRAIN_PATH/inbox/connections/"
echo "  3. Review Q&A in: $BRAIN_PATH/inbox/qa/"
echo "  4. Review digest in: $BRAIN_PATH/resources/queries/archive/"
echo "  5. Commit changes to git"
echo ""

log_result "Audit pipeline completed successfully"
exit 0
