#!/usr/bin/env bash
# link-pattern-rules.sh — link vault stack rules into a Claude Code rules dir.
# Usage: link-pattern-rules.sh BRAIN_PATH RULES_DIR
# Each resources/knowledge/patterns/*-patterns.md note with `paths:` in its frontmatter
# gets a symlink RULES_DIR/<name>.md. Claude Code loads it when Read/Edit/Write touches
# a matching file. Links whose target is gone or lost `paths:` are removed.
set -euo pipefail
brain=$1 rules=$2
mkdir -p "$rules"

has_paths() {
  awk '{ sub(/\r$/, "") }
       NR == 1 { if ($0 != "---") exit; next }
       $0 == "---" { exit }
       /^paths:/ { found = 1; exit }
       END { exit !found }' "$1"
}

for note in "$brain"/resources/knowledge/patterns/*-patterns.md; do
  [[ -f $note ]] && has_paths "$note" || continue
  ln -sfn "$note" "$rules/$(basename "$note")"
  echo "linked $(basename "$note")"
done

for link in "$rules"/*-patterns.md; do
  [[ -L $link ]] || continue
  [[ -f $link ]] && has_paths "$link" && continue
  rm "$link"
  echo "removed $(basename "$link")"
done
