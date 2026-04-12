#!/bin/bash
# Phase 4: Digest Generation & Clock Reset
# Synthesizes phases 1-3 into a weekly summary and resets audit clock

set -euo pipefail

# Source config
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

# Colors for logging
LOG_PREFIX="[phase-4]"

log_info() { echo "$LOG_PREFIX [INFO] $*"; }
log_error() { echo "$LOG_PREFIX [ERROR] $*" >&2; }
log_result() { echo "$LOG_PREFIX [RESULT] $*"; }

# Accept phase counts as parameters
phase1_count=${1:-0}
phase2_count=${2:-0}
phase3_count=${3:-0}

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
mkdir -p "$BRAIN_PATH/meta"
mkdir -p "$BRAIN_PATH/resources/queries/archive"

meta_dir="$BRAIN_PATH/meta"
archive_dir="$BRAIN_PATH/resources/queries/archive"

# Generate timestamp info
now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
now_epoch=$(date +%s)
week_num=$(date -u +%V)
year=$(date -u +%Y)
week_file="$archive_dir/weekly-digest-${year}-W${week_num}.md"

log_info "Generating digest for week $week_num..."

# Create digest file
{
    echo "# Weekly Digest — Week $week_num ($year)"
    echo ""
    echo "**Date:** $(date -u +%Y-%m-%d)"
    echo ""
    echo "## At a Glance"
    echo ""
    echo "✅ Phase 1 (Compile): $phase1_count draft article(s) created"
    echo "✅ Phase 2 (Connect): $phase2_count connection suggestion(s) generated"
    echo "✅ Phase 3 (Q&A): $phase3_count query result(s) created"
    echo ""
    echo "## Executive Summary"
    echo ""
    echo "This week's audit produced:"
    echo "- **$phase1_count new draft articles** requiring review and approval"
    echo "- **$phase2_count connection suggestions** to strengthen the vault"
    echo "- **$phase3_count Q&A queries** to validate knowledge coverage"
    echo ""
    echo "## Key Metrics"
    echo ""
    echo "| Metric | Count | Status |"
    echo "|--------|-------|--------|"
    echo "| Drafts to Review | $phase1_count | Pending |"
    echo "| Connection Suggestions | $phase2_count | Pending Review |"
    echo "| Q&A Results | $phase3_count | Pending Review |"
    echo ""
    echo "## Action Items"
    echo ""
    if [[ $phase1_count -gt 0 ]]; then
        echo "### Phase 1: Review & Publish Drafts"
        echo "- [ ] Review all drafts in \`inbox/drafts/\`"
        echo "- [ ] Approve or request revisions"
        echo "- [ ] Move approved articles to \`resources/articles/published/\`"
        echo "- [ ] Archive rejected or duplicate drafts"
        echo ""
    fi
    echo ""
    if [[ $phase2_count -gt 0 ]]; then
        echo "### Phase 2: Process Connection Suggestions"
        echo "- [ ] Review \`inbox/connections/suggested-connections.md\`"
        echo "- [ ] Add wiki-links between connected files"
        echo "- [ ] Decide: keep, merge, or archive isolated notes"
        echo "- [ ] Update vault structure as needed"
        echo ""
    fi
    echo ""
    if [[ $phase3_count -gt 0 ]]; then
        echo "### Phase 3: Extract Q&A Insights"
        echo "- [ ] Review \`inbox/qa/\` results"
        echo "- [ ] Identify actionable insights"
        echo "- [ ] Update relevant articles based on findings"
        echo "- [ ] File completed Q&A to \`resources/queries/archive/\`"
        echo ""
    fi
    echo ""
    echo "### General"
    echo "- [ ] Commit all audit outputs to git"
    echo "- [ ] Update project CAPs based on identified blockers"
    echo "- [ ] Plan next week's focus areas"
    echo "- [ ] Celebrate progress!"
    echo ""
    echo "---"
    echo ""
    echo "**Audit Timestamp:** $now"
    echo "**Next Maintenance:** $(date -u -d '+7 days' +%Y-%m-%d)T10:00:00Z"

} > "$week_file"

log_info "Digest written to: $(basename "$week_file")"

# Update last-maintenance.md (reset clock)
log_info "Resetting maintenance clock..."
maintenance_file="$meta_dir/last-maintenance.md"

cat > "$maintenance_file" << EOF
$(date -u +"%Y-%m-%d %H:%M:%S")
# Last Maintenance Timestamp

**Timestamp (ISO):** $now
**Epoch Seconds:** $now_epoch
**Week:** $week_num / $year

*Updated by phase-4-digest.sh*
EOF

log_info "Maintenance clock updated"

log_result "Phase 4 complete: digest written, maintenance clock reset"
exit 0
