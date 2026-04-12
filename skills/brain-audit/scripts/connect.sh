#!/bin/bash
# Phase 2: Orphan Detection & Connection Suggestions
# Finds isolated notes and suggests semantic connections

set -euo pipefail

# Source config
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

# Colors for logging
LOG_PREFIX="[phase-2]"

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
mkdir -p "$BRAIN_PATH/inbox/connections"

connections_dir="$BRAIN_PATH/inbox/connections"
suggestions_file="$connections_dir/suggested-connections.md"

# Find all markdown files (excluding special directories)
log_info "Scanning vault for markdown files..."
all_files=()
while IFS= read -r -d '' file; do
    all_files+=("$file")
done < <(find "$BRAIN_PATH" -name "*.md" -type f \
    ! -path "*/.git/*" \
    ! -path "*/inbox/*" \
    ! -path "*/archive/*" \
    ! -path "*/meta/*" \
    ! -path "*/.claude/*" \
    ! -path "*/.cursor/*" \
    -print0 2>/dev/null)

file_count=${#all_files[@]}
log_info "Found $file_count markdown file(s)"

if [[ $file_count -lt 2 ]]; then
    log_result "Not enough files for connection analysis"
    exit 0
fi

# Extract keywords from a file (simple heuristic: grep common words)
extract_keywords() {
    local file="$1"
    grep -io '\b[a-z][a-z-]*\b' "$file" 2>/dev/null | \
        tr '[:upper:]' '[:lower:]' | \
        grep -v '^\(the\|and\|or\|but\|for\|in\|of\|to\|a\|an\|is\|are\|be\|at\|by\|from\|it\|on\|as\)$' | \
        awk '!seen[$0]++ { if (n++ < 20) print }'
}

# Build suggestion file
log_info "Analyzing connections..."
{
    echo "# Suggested Connections"
    echo ""
    echo "Date: $(date -u +%Y-%m-%d)"
    echo ""
    echo "## Orphan Analysis"
    echo ""
    echo "The following files have weak connections and may benefit from linking or merging:"
    echo ""

    suggestion_count=0

    # For each file, count connections and suggest links
    for file_a in "${all_files[@]}"; do
        filename_a=$(basename "$file_a")
        rel_path_a="${file_a#$BRAIN_PATH/}"

        # Simple connection count: lines containing [[
        connection_count=$(grep -c '\[\[' "$file_a" 2>/dev/null) || true
        connection_count=${connection_count:-0}

        # If weakly connected, suggest links
        if [[ $connection_count -lt 2 ]]; then
            keywords_a=$(extract_keywords "$file_a")

            echo "### $rel_path_a"
            echo "**Current connections:** $connection_count (weakly connected)"
            echo "**Suggested connections:**"

            match_count=0
            for file_b in "${all_files[@]}"; do
                if [[ "$file_a" == "$file_b" ]]; then
                    continue
                fi

                keywords_b=$(extract_keywords "$file_b")

                # Count matching keywords (simple similarity)
                matches=$(comm -12 <(echo "$keywords_a") <(echo "$keywords_b") | wc -l | tr -d '[:space:]')

                if [[ $matches -gt 2 ]]; then
                    filename_b=$(basename "$file_b")
                    rel_path_b="${file_b#$BRAIN_PATH/}"
                    confidence=$((matches * 12))  # Simple scoring
                    [[ $confidence -gt 100 ]] && confidence=100

                    echo "- \`$rel_path_b\` (confidence: $confidence%)"
                    match_count=$((match_count + 1))
                    suggestion_count=$((suggestion_count + 1))

                    if [[ $match_count -ge 3 ]]; then
                        break
                    fi
                fi
            done

            if [[ $match_count -eq 0 ]]; then
                echo "- (No strong keyword matches found)"
            fi

            echo ""
        fi
    done

    echo "---"
    echo ""
    echo "**Next action:** Review suggestions above. For each suggestion:"
    echo "1. Read both files to verify connection quality"
    echo "2. If relevant, add wiki-link \`[[file]]\` to both files"
    echo "3. If files should merge, combine them into a single article"
    echo "4. If file is outdated, move to archive"

} > "$suggestions_file"

log_result "Phase 2 complete: suggestions saved to $suggestions_file"
exit 0
