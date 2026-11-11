# Budget rules shared by .claude/hooks/brain-session-start.sh and scripts/brain-context.sh. Source it.
# shellcheck shell=bash
# Claude Code swaps hook output over ~10,000 characters for a file path and a 2 KB preview.
# shellcheck disable=SC2034  # read by the scripts that source this file
BRAIN_CONTEXT_MAX_BYTES=9500

# brain_note_max_bytes <budget> <pitfalls-file> <bytes-printed-so-far>
# Rule: pitfalls outrank the project note. The note gets up to 3,000 B (whole lines), less when the
# pitfalls need the room: budget - pitfalls - printed - 900 B (what prints after the note: review line,
# vendored warnings, maintenance nudge, note frame and cut marker). Prints 0 when no room is left.
brain_note_max_bytes() {
  local size=0 cap
  [[ -f "$2" ]] && size=$(wc -c <"$2")
  cap=$(( $1 - size - $3 - 900 ))
  (( cap < 3000 )) || cap=3000
  (( cap > 0 )) || cap=0
  echo "$cap"
}

# brain_print_pitfalls <pitfalls-file> <budget> <bytes-printed-so-far>
# Whole `## ` sections only (scripts/fit-sections.py); head -c is the last resort.
brain_print_pitfalls() {
  [[ -f "$1" ]] || return 0
  local max=$(( $2 - $3 - 200 ))
  (( max > 0 )) || max=0
  echo "--- AI-AGENTS PITFALLS (constraints) ---"
  python3 "$(dirname "${BASH_SOURCE[0]}")/fit-sections.py" "$1" "$max" || head -c "$max" "$1"
  echo "--- END PITFALLS ---"
}
