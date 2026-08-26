#!/bin/bash
# brain-audit:digest — Digest Generation & Clock Reset
# Synthesizes the compile/connect/insights subskill outputs into a weekly
# summary and resets the maintenance clock.

set -euo pipefail

# Source config
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

# Colors for logging
LOG_PREFIX="[digest]"

log_info() { echo "$LOG_PREFIX [INFO] $*"; }
log_error() { echo "$LOG_PREFIX [ERROR] $*" >&2; }
log_result() { echo "$LOG_PREFIX [RESULT] $*"; }

# Accept subskill counts as parameters (matches brain-audit:digest SKILL.md's
# COMPILE_COUNT / CONNECT_COUNT / INSIGHTS_COUNT)
compile_count=${1:-0}
connect_count=${2:-0}
insights_count=${3:-0}

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

next_maintenance=$(date -u -d '+7 days' +%Y-%m-%d 2>/dev/null || date -u -v+7d +%Y-%m-%d)

# Create digest file
{
    echo "# Weekly Digest — Week $week_num ($year)"
    echo ""
    echo "**Date:** $(date -u +%Y-%m-%d)"
    echo ""
    echo "## At a Glance"
    echo ""
    echo "✅ Compile: $compile_count pitfall/lesson promotion(s) to [[pitfalls]] / [[lessons-learned]]"
    echo "✅ Connect: $connect_count knowledge file(s) created/updated in resources/knowledge/"
    echo "✅ Insights: $insights_count insight quer(y/ies) synthesized to inbox/insights/"
    echo ""
    echo "## Executive Summary"
    echo ""
    echo "This audit run produced:"
    echo "- **$compile_count cross-project pitfall/lesson promotion(s)** from inbox/daily/ into resources/operational/ai-agents/"
    echo "- **$connect_count knowledge file update(s)** synthesizing recurring patterns across projects"
    echo "- **$insights_count insight synthes(is/es)** written to inbox/insights/"
    echo ""
    echo "## Key Metrics"
    echo ""
    echo "| Metric | Count | Status |"
    echo "|--------|-------|--------|"
    echo "| Pitfalls/lessons promoted | $compile_count | Committed |"
    echo "| Knowledge files created/updated | $connect_count | Pending review |"
    echo "| Insight queries synthesized | $insights_count | Written |"
    echo ""
    echo "## Action Items"
    echo ""
    if [[ $compile_count -gt 0 ]]; then
        echo "### Compile: Review Promoted Entries"
        echo "- [ ] Skim new entries in \`resources/operational/ai-agents/pitfalls.md\` and \`lessons-learned.md\` for accuracy"
        echo "- [ ] Confirm nothing project-specific leaked into a cross-project entry"
        echo ""
    fi
    echo ""
    if [[ $connect_count -gt 0 ]]; then
        echo "### Connect: Review Knowledge Files"
        echo "- [ ] Review the diff in \`resources/knowledge/\` and \`projects/*.md\` (\`## See also\` additions)"
        echo "- [ ] Approve or edit before committing (brain-audit:connect stops for confirmation before its own commit)"
        echo ""
    fi
    echo ""
    if [[ $insights_count -gt 0 ]]; then
        echo "### Insights: Act on Findings"
        echo "- [ ] Read \`inbox/insights/$(date -u +%Y-%m-%d).md\`"
        echo "- [ ] Work through its \`## Action Items\` checklist"
        echo ""
    fi
    echo ""
    echo "### General"
    echo "- [ ] Commit all audit outputs to the vault git repo (\`brain-sync end\` or manual commit)"
    echo "- [ ] Check \`resources/queries/archive/\` for this run's knowledge-gaps/roadmap results, if \`brain-audit:queries\` was also run"
    echo "- [ ] Plan next week's focus areas"
    echo ""
    echo "---"
    echo ""
    echo "**Audit Timestamp:** $now"
    echo "**Next Maintenance:** ${next_maintenance}T10:00:00Z"

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

*Updated by digest.sh (brain-audit:digest)*
EOF

log_info "Maintenance clock updated"

log_result "Digest complete: digest written, maintenance clock reset"
exit 0
