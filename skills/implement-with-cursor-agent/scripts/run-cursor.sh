#!/usr/bin/env bash
# run-cursor.sh <run_dir> <prompt_file> [resume]
# Run Cursor headless inside a container that sees only <run_dir>, mounted at /work:
#   /work/project and /work/vault (task clones, not worktrees) and /work/home (Cursor state, kept for resume).
# The Cursor CLI and uv come from the host, mounted read-only. The container gets no GitHub credentials:
# Cursor commits locally, and the main agent pushes and opens the PRs after the gate.
# Cursor's own --sandbox does not confine anything in headless mode (canary test, 2026-10-12), hence the container.
# Pins CURSOR_MODEL (default gpt-5.3-codex). A credit or usage-limit error stops the run with exit 75:
# there is no silent fallback, because `auto` can route to a Claude model and remove the second-model property.
# CURSOR_TIMEOUT (default 1800 s) guards against `agent -p` hangs (exit 124). Output: <run_dir>/result-<n>.json.
# The API key comes from CURSOR_API_KEY or CURSOR_API_KEY_FILE (default ~/.config/cursor-agent/api-key);
# it is passed by name (-e CURSOR_API_KEY), never on the command line.
set -uo pipefail
run=$(cd "$1" && pwd) prompt=$2 mode=${3:-new}
model=${CURSOR_MODEL:-gpt-5.3-codex}
image=${CURSOR_IMAGE:-local-ci-runner:24.04}
key_file=${CURSOR_API_KEY_FILE:-$HOME/.config/cursor-agent/api-key}
if [ -z "${CURSOR_API_KEY:-}" ]; then
  CURSOR_API_KEY=$(cat "$key_file" 2>/dev/null)
  if [ -z "$CURSOR_API_KEY" ]; then
    echo "no Cursor API key: set CURSOR_API_KEY or write it to $key_file (mode 600)" >&2; exit 4
  fi
fi
export CURSOR_API_KEY
cursor_dir=$(dirname "$(readlink -f "$(command -v agent)")") || exit 4
uv_bin=$(readlink -f "$(command -v uv)") || exit 4
n=$(find "$run" -maxdepth 1 -name 'result-*.json' | wc -l)
out="$run/result-$n.json"
resume=()
if [ "$mode" = resume ]; then
  sid=$(python3 -c 'import json, sys; print(json.load(open(sys.argv[1]))["session_id"])' "$run/result-$((n - 1)).json") || exit 3
  resume=(--resume "$sid")
fi
mkdir -p "$run/home"
# Cursor installs the account's marketplace plugins (superpowers, ...) into $HOME/.cursor/plugins. An empty read-only
# dir makes each install fail, so the delegated agent runs without them; the user's own Cursor keeps them.
mkdir -p "$run/home/.cursor/plugins" && chmod 555 "$run/home/.cursor/plugins"
name="cursor-$(basename "$run")-$n-$$"

start=$(date +%s)
timeout "${CURSOR_TIMEOUT:-1800}" docker run --rm --init --name "$name" \
  --user "$(id -u):$(id -g)" -e CURSOR_API_KEY -e BRAIN_AGENT_HOOKS=0 -e HOME=/work/home \
  -e GIT_AUTHOR_NAME="Cursor agent" -e GIT_AUTHOR_EMAIL=cursoragent@cursor.com \
  -e GIT_COMMITTER_NAME="Cursor agent" -e GIT_COMMITTER_EMAIL=cursoragent@cursor.com \
  -v "$run:/work" -v "$cursor_dir:/opt/cursor:ro" -v "$uv_bin:/usr/local/bin/uv:ro" \
  --entrypoint /opt/cursor/cursor-agent "$image" \
  -p "$(cat "$prompt")" "${resume[@]}" --model "$model" --force --trust \
  --workspace /work/project --add-dir /work/vault --output-format json >"$out" 2>"$out.err"
rc=$?
[ "$rc" -eq 124 ] && docker rm -f "$name" >/dev/null 2>&1
# ponytail: heuristic match on Cursor's limit wording; widen the pattern when a new message appears.
if [ "$rc" -ne 0 ] && [ "$rc" -ne 124 ] \
  && grep -qiE 'credit|usage limit|quota|spend limit|out of (requests|usage)|upgrade (your )?plan' "$out" "$out.err"; then
  echo "usage limit on $model: stop. Rerun with another CURSOR_MODEL only after the user approves it." >&2
  rc=75
fi
printf 'rc=%s model=%s wall_s=%s out=%s\n' "$rc" "$model" "$(($(date +%s) - start))" "$out" | tee -a "$run/runs.log"
exit "$rc"
