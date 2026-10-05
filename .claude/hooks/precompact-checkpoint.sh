#!/usr/bin/env bash
# PreCompact: append a breadcrumb to $BRAIN_PATH/inbox/daily/checkpoints/<slug>/YYYY-MM-DD.md
# before the context is compacted: trigger, context size, branch, changed files, last prompts.
# /capture folds it into the session log. A session that compacts, then crashes, still
# leaves a trace. Never writes implementation logs (SessionEnd's missing-log warning stays honest).
set -uo pipefail

AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
ENV_FILE="${BRAIN_ENV_FILE:-$AI_DOTFILES/config/brain.env}"
# shellcheck source=/dev/null
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"
[[ -n "${BRAIN_PATH:-}" && -d "$BRAIN_PATH" ]] || exit 0

INPUT=$(cat)
CWD=$(python3 -c 'import json,sys; print(json.loads(sys.argv[1]).get("cwd") or ".")' "$INPUT" 2>/dev/null) || exit 0
ROOT=$(git -C "$CWD" rev-parse --show-toplevel 2>/dev/null || echo "$CWD")

SLUG=""
[[ -f "$ROOT/.brain-project" ]] && SLUG=$(head -1 "$ROOT/.brain-project" | tr -d '[:space:]')
[[ -n "$SLUG" ]] || SLUG=$(basename "$ROOT")
BRANCH=$(git -C "$ROOT" branch --show-current 2>/dev/null || true)
CHANGES=$(git -C "$ROOT" status --short 2>/dev/null | head -30)

OUT_DIR="$BRAIN_PATH/inbox/daily/checkpoints/$SLUG"
mkdir -p "$OUT_DIR"

python3 - "$INPUT" "$BRANCH" "$CHANGES" "$OUT_DIR/$(date +%F).md" <<'EOF' 2>/dev/null || true
import json, os, sys, time

event, branch, changes, out = json.loads(sys.argv[1]), sys.argv[2], sys.argv[3], sys.argv[4]
path = event.get("transcript_path") or ""
prompts, context = [], 0
if os.path.isfile(path):
    with open(path, "rb") as f:
        f.seek(max(0, os.path.getsize(path) - 2_000_000))
        lines = f.read().decode("utf-8", "ignore").splitlines()
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") or {}
        usage = msg.get("usage")
        if usage:
            context = sum(usage.get(k) or 0 for k in
                          ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        human = not rec.get("isMeta") and (rec.get("origin") or {"kind": "human"}).get("kind") == "human"
        if msg.get("role") == "user" and human:
            content = msg.get("content")
            if isinstance(content, list):
                content = " ".join(c.get("text", "") for c in content if c.get("type") == "text")
            if isinstance(content, str) and content.strip() and not content.startswith("<"):
                prompts.append(" ".join(content.split())[:300])

entry = [f"## {time.strftime('%H:%M')} compaction ({event.get('trigger') or '?'}) "
         f"— session {(event.get('session_id') or '?')[:8]}, context {context // 1000}k",
         f"- Branch: `{branch or '-'}`"]
if changes.strip():
    entry += ["- Changed files:", "```", changes, "```"]
if prompts:
    entry += ["- Last requests:"] + [f"  - {p}" for p in prompts[-3:]]
with open(out, "a") as f:
    f.write("\n".join(entry) + "\n\n")
EOF
exit 0
