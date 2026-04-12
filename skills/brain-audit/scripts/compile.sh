#!/bin/bash
# Phase 1: Raw Data → Draft Articles
# Scans /raw/ for markdown fragments and converts to draft articles with metadata

set -euo pipefail

# Source config
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

# Colors for logging
LOG_PREFIX="[phase-1]"

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
mkdir -p "$BRAIN_PATH/raw"
mkdir -p "$BRAIN_PATH/inbox/drafts"
mkdir -p "$BRAIN_PATH/archive/processed"

raw_dir="$BRAIN_PATH/raw"
drafts_dir="$BRAIN_PATH/inbox/drafts"
archive_dir="$BRAIN_PATH/archive/processed"

# Count raw files
raw_count=$(find "$raw_dir" -maxdepth 1 -type f 2>/dev/null | wc -l)
log_info "Found $raw_count raw file(s) in $raw_dir"

if [[ $raw_count -eq 0 ]]; then
    log_result "No raw files to process"
    exit 0
fi

# Process each raw file
processed=0
created=0

for raw_file in "$raw_dir"/*; do
    if [[ ! -f "$raw_file" ]]; then
        continue
    fi

    filename=$(basename "$raw_file")
    [[ "$filename" == "index.md" || "$filename" == "README.md" ]] && continue
    # Extract slug from filename (remove extension)
    slug="${filename%.*}"
    # Convert to lowercase and replace spaces/special chars with hyphens
    slug=$(echo "$slug" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9-]/-/g' | sed 's/-+/-/g' | sed 's/^-\|-$//g')

    # Read file content
    file_content=$(cat "$raw_file")

    # Generate draft with frontmatter
    created_date=$(date -u +%Y-%m-%d)
    created_time=$(date -u +%Y-%m-%dT%H:%M:%SZ)

    draft_file="$drafts_dir/${created_date}-${slug}.md"

    cat > "$draft_file" << EOF
---
created: $created_time
source: raw/$filename
status: draft
requires-review: true
---

# ${slug^}

## Content

$file_content

---

*This draft was auto-generated from raw input. Please review for accuracy and structure before publishing.*
EOF

    created=$((created + 1))
    log_info "Created draft: $(basename "$draft_file")"

    # Move source to archive
    mv "$raw_file" "$archive_dir/$filename"
    processed=$((processed + 1))
    log_info "Archived: $filename"
done

log_result "Phase 1 complete: $processed files processed, $created drafts created"
exit 0
