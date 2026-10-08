#!/usr/bin/env bash
# PreCompact: append a resume note to $BRAIN_PATH/inbox/daily/checkpoints/<slug>/YYYY-MM-DD.md
# before the context is compacted: trigger, context size, branch, recent and unpushed commits,
# changed and edited files, running background agents, a recent tool error, the last requests
# with the assistant text they answer, user decisions, and the last assistant message.
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
COMMITS=$(git -C "$ROOT" log --oneline -8 2>/dev/null || true)
UNPUSHED=$(git -C "$ROOT" rev-list --count '@{u}..HEAD' 2>/dev/null || echo "no upstream")

OUT_DIR="$BRAIN_PATH/inbox/daily/checkpoints/$SLUG"
mkdir -p "$OUT_DIR"

python3 - "$INPUT" "$BRANCH" "$CHANGES" "$COMMITS" "$UNPUSHED" "$OUT_DIR/$(date +%F).md" <<'EOF' 2>/dev/null || true
import json, os, re, sys, time

event, (branch, changes, commits, unpushed, out) = json.loads(sys.argv[1]), sys.argv[2:7]
path = event.get("transcript_path") or ""
SECRET = re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,}|github_pat_\w{20,}|sk-[\w-]{20,})")
STATUS = re.compile(r"<task-id>(\w+)</task-id>.*?<status>(\w+)</status>", re.S)


def flat(text, limit):
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + " …"


def texts(content):
    if isinstance(content, str):
        return content
    return " ".join(c.get("text", "") for c in content or [] if isinstance(c, dict) and c.get("type") == "text")


context, turns, decisions, edited, agents, tools = 0, [], [], {}, {}, {}
results, error, last_assistant, assistant_id = 0, None, "", None
if os.path.isfile(path):
    with open(path, "rb") as f:
        f.seek(max(0, os.path.getsize(path) - 4_000_000))
        lines = f.read().decode("utf-8", "ignore").splitlines()
    for line in lines:
        try:
            rec = json.loads(line)
        except ValueError:
            continue
        msg = rec.get("message") or {}
        content = msg.get("content")
        blocks = [b for b in content if isinstance(b, dict)] if isinstance(content, list) else []
        result = rec.get("toolUseResult") if isinstance(rec.get("toolUseResult"), dict) else {}
        if msg.get("usage"):
            context = sum(msg["usage"].get(k) or 0 for k in
                          ("input_tokens", "cache_creation_input_tokens", "cache_read_input_tokens"))
        if msg.get("role") == "assistant":
            text = texts(content).strip()
            if text:  # one transcript line per streamed block: join blocks of the same message
                last_assistant = last_assistant + "\n" + text if msg.get("id") == assistant_id else text
                assistant_id = msg.get("id")
            for b in blocks:
                if b.get("type") == "tool_use":
                    tools[b.get("id")] = b.get("name")
                    file = (b.get("input") or {}).get("file_path")
                    if b.get("name") in ("Edit", "Write", "NotebookEdit") and file:
                        edited.pop(file, None)
                        edited[file] = True
            continue
        origin = (rec.get("origin") or {"kind": "human"}).get("kind")
        if rec.get("type") in ("queue-operation", "attachment") or origin == "task-notification":
            for task, status in STATUS.findall(line):  # notifications land as queued commands
                if task in agents and status != "running":
                    agents[task]["done"] = True
            continue
        if msg.get("role") != "user" or rec.get("isCompactSummary"):
            continue
        if result.get("agentId") and result.get("description"):
            agents[result["agentId"]] = {"desc": result["description"], "done": result.get("status") == "completed"}
        if result.get("resumedAgentId") in agents:
            agents[result["resumedAgentId"]]["done"] = False
        for question, answer in (result.get("answers") or {}).items():
            decisions.append(f"{flat(question, 200)} → **{flat(answer, 200)}**")
        tool_results = [b for b in blocks if b.get("type") == "tool_result"]
        for b in tool_results:
            results += 1
            if b.get("is_error"):
                error = (results, tools.get(b.get("tool_use_id"), "?"), flat(texts(b.get("content")), 400))
        text = texts(content)
        if not tool_results and not rec.get("isMeta") and origin == "human" and text.strip() \
                and not text.startswith("<"):
            turns.append((flat(last_assistant[-300:], 300), flat(text, 600)))

entry = [f"## {time.strftime('%H:%M')} compaction ({event.get('trigger') or '?'}) "
         f"— session {(event.get('session_id') or '?')[:8]}, context {context // 1000}k",
         f"- Branch: `{branch or '-'}` — unpushed commits: {unpushed}"]
if commits.strip():
    entry += ["- Recent commits:", "```", commits, "```"]
if changes.strip():
    entry += ["- Changed files:", "```", changes, "```"]
if edited:
    entry += ["- Files edited this session:"] + [f"  - `{p}`" for p in list(edited)[-15:]]
running = [f"  - {a['desc']} (`{i}`)" for i, a in agents.items() if not a["done"]]
if running:
    entry += ["- Background agents still running:"] + running
if error and results - error[0] < 20:
    entry += [f"- Recent tool error ({error[1]}): {error[2]}"]
if decisions:
    entry += ["- User decisions (AskUserQuestion):"] + [f"  - {d}" for d in decisions[-5:]]
if turns:
    entry += ["- Last requests, each after the assistant text it answers:"]
    for before, prompt in turns[-5:]:
        entry += [f"  - after “{before}”" if before else "  - (no assistant text before)", f"    → **{prompt}**"]
if last_assistant:
    entry += ["- Last assistant message:", "", "> " + flat(last_assistant, 1500)]
with open(out, "a") as f:
    f.write(SECRET.sub("***", "\n".join(entry)) + "\n\n")
EOF
exit 0
