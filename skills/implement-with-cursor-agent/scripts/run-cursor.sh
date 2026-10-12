#!/usr/bin/env bash
# run-cursor.sh <run_dir> <prompt_file> [resume]
# Run Cursor headless on <run_dir>/project, with <run_dir>/vault as an extra directory for the note.
# Pins CURSOR_MODEL (default gpt-5.3-codex). A credit or usage-limit error stops the run with exit 75:
# there is no silent fallback, because `auto` can route to a Claude model and remove the second-model property.
# BRAIN_AGENT_HOOKS=0: Cursor's brain-sync hooks stay off, because the main agent owns vault sync.
# CURSOR_TIMEOUT (default 1800 s) guards against `agent -p` hangs (exit 124). Output: <run_dir>/result-<n>.json.
set -uo pipefail
run=$1 prompt=$2 mode=${3:-new}
model=${CURSOR_MODEL:-gpt-5.3-codex}
n=$(find "$run" -maxdepth 1 -name 'result-*.json' | wc -l)
out="$run/result-$n.json"
resume=()
if [ "$mode" = resume ]; then
  sid=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["session_id"])' "$run/result-$((n - 1)).json") || exit 3
  resume=(--resume "$sid")
fi

start=$(date +%s)
BRAIN_AGENT_HOOKS=0 timeout "${CURSOR_TIMEOUT:-1800}" agent -p "$(cat "$prompt")" "${resume[@]}" \
  --model "$model" --force --trust --workspace "$run/project" --add-dir "$run/vault" \
  --output-format json >"$out" 2>"$out.err"
rc=$?
# ponytail: heuristic match on Cursor's limit wording; widen the pattern when a new message appears.
if [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ] \
  && grep -qiE 'credit|usage limit|quota|spend limit|out of (requests|usage)|upgrade (your )?plan' "$out" "$out.err"; then
  echo "usage limit on $model: stop. Rerun with another CURSOR_MODEL only after the user approves it." >&2
  rc=75
fi
printf 'rc=%s model=%s wall_s=%s out=%s\n' "$rc" "$model" "$(($(date +%s) - start))" "$out" | tee -a "$run/runs.log"
exit "$rc"
