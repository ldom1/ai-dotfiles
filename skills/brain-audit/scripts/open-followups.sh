#!/bin/bash
# brain-audit:insights — list open follow-ups from recent session logs.
# Reads BRAIN_PATH and BRAIN_AUDIT_LOOKBACK_DAYS (default 30).
# Prints "=== <vault-relative path>" then one item per line.
# Handles `**Follow-ups:** text` (inline), `**Follow-ups:**` + `- item` lines,
# and the older `## Follow-ups` heading. Items containing "none" are skipped.

set -euo pipefail

if [[ -z "${BRAIN_PATH:-}" ]]; then
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    # shellcheck source=_brain_env.sh
    source "$script_dir/_brain_env.sh"
fi

lookback="${BRAIN_AUDIT_LOOKBACK_DAYS:-30}"
cutoff=$(date -d "-${lookback} days" +%Y-%m-%d 2>/dev/null || date -v-"${lookback}"d +%Y-%m-%d)

find "$BRAIN_PATH/inbox/daily/implementation" -name '*.md' -newermt "$cutoff" 2>/dev/null | sort | while read -r f; do
    items=$(awk '
        /^(## |\*\*)Follow-ups/ {
            on = 1
            sub(/^(## |\*\*)Follow-ups[:*]*[ \t]*/, "")
            if ($0 != "" && $0 !~ /^[Nn]one/) print "- " $0
            next
        }
        on && /^(## |\*\*[A-Z])/ { on = 0 }
        on && /^- / && !/[Nn]one/
    ' "$f")
    if [[ -n "$items" ]]; then
        printf '=== %s\n%s\n' "${f#"$BRAIN_PATH"/}" "$items"
    fi
done
