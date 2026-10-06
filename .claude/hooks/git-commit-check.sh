#!/usr/bin/env bash
# PreToolUse (Bash): validate git commit message convention.
# Format: type(scope): description
# Types: feat | fix | enh | doc | ci
# Scopes: finite list per project type, defined in scopes.json

set -euo pipefail

SCOPES_FILE="$HOME/ai-dotfiles/skills/git-commit/scopes.json"

if ! command -v jq &>/dev/null || ! command -v python3 &>/dev/null; then
  exit 0
fi

INPUT=$(cat)
CMD=$(echo "$INPUT" | jq -r '.tool_input.command // empty')

if [ -z "$CMD" ]; then
  exit 0
fi

# Parse the command. It is a commit only when a simple command (split on
# `&& || ; |` and newlines outside quotes and heredoc bodies) is
# `git [-C dir | -c k=v | --no-pager ...] commit`. Commit-like text inside a
# heredoc body, a quoted string or the arguments of another command is data.
# The one heredoc kept is the message form -m "$(cat <<'EOF' ... EOF)".
# Prints one JSON object: {commit, msg, dir}. If parsing fails, PARSED stays
# empty and the hook fails open: it guards a convention, not safety.
PARSED=$(HOOK_CMD="$CMD" python3 - <<'PY' 2>/dev/null || true
import json, os, re

cmd = os.environ["HOOK_CMD"]
MSG_HEREDOC = re.compile(r"\$\(\s*cat\s*<<-?\s*(['\"]?)(\w+)\1[ \t]*\n(.*?)\n[ \t]*\2[ \t]*\n?\s*\)", re.S)
HEREDOC = re.compile(r"<<(-?)[ \t]*(['\"]?)([\w.-]+)\2")


def split(cmd):
    """Return the simple commands of cmd as lists of unquoted words."""
    cmds, words, cur, have, pending = [], [], [], False, []
    n = len(cmd)

    def end_word():
        nonlocal cur, have
        if have:
            words.append("".join(cur))
        cur, have = [], False

    def end_cmd():
        nonlocal words
        end_word()
        if words:
            cmds.append(words)
        words = []

    def is_redirect_amp(i):  # 2>&1, &>file
        return cmd[i - 1:i] in ("<", ">") or cmd[i + 1:i + 2] in ("<", ">")

    i = 0
    while i < n:
        c = cmd[i]
        if c == "\\" and i + 1 < n:
            cur.append(cmd[i + 1]); have = True; i += 2
        elif c == "'":
            j = cmd.index("'", i + 1)
            cur.append(cmd[i + 1:j]); have = True; i = j + 1
        elif c == '"':
            have = True; i += 1
            while cmd[i] != '"':
                m = MSG_HEREDOC.match(cmd, i) if cmd.startswith("$(", i) else None
                if m:
                    cur.append(m.group(3)); i = m.end()
                elif cmd[i] == "\\" and cmd[i + 1] in '"\\$`':
                    cur.append(cmd[i + 1]); i += 2
                else:
                    cur.append(cmd[i]); i += 1
            i += 1
        elif c == "#" and not have:
            while i < n and cmd[i] != "\n":
                i += 1
        elif cmd.startswith("<<", i) and not cmd.startswith("<<<", i) and HEREDOC.match(cmd, i):
            m = HEREDOC.match(cmd, i)
            pending.append((m.group(3), bool(m.group(1)))); i = m.end()
        elif c == "\n":
            end_cmd(); i += 1
            for term, tabs in pending:  # skip heredoc bodies up to the terminator
                while i < n:
                    j = cmd.find("\n", i)
                    j = n if j < 0 else j
                    line = cmd[i:j]
                    i = min(j + 1, n)
                    if (line.lstrip("\t") if tabs else line) == term:
                        break
            pending = []
        elif c in ";|" or (c == "&" and (cmd.startswith("&&", i) or not is_redirect_amp(i))):
            end_cmd(); i += 2 if cmd.startswith(("&&", "||"), i) else 1
        elif c in " \t":
            end_word(); i += 1
        else:
            cur.append(c); have = True; i += 1
    end_cmd()
    return cmds


def git_commit(words):
    """Return (-C dir, args after commit) when words is `git [opts] commit ...`."""
    while words and re.fullmatch(r"\w+=.*", words[0]):  # VAR=x git commit
        words = words[1:]
    if not words or os.path.basename(words[0]) != "git":
        return None
    i, target = 1, ""
    while i < len(words) and words[i].startswith("-"):
        if words[i] in ("-C", "-c") and i + 1 < len(words):
            if words[i] == "-C":
                target = words[i + 1]
            i += 1
        i += 1
    if i < len(words) and words[i] == "commit":
        return target, words[i + 1:]


result, cd = {"commit": False}, ""
for words in split(cmd):
    if words[0] == "cd" and len(words) > 1:
        cd = words[1]
    found = git_commit(words)
    if found:
        target, args = found
        msg = ""
        for k, a in enumerate(args):
            if re.fullmatch(r"-[a-zA-Z]*m", a) and k + 1 < len(args):
                msg = args[k + 1]; break
            if a.startswith("--message="):
                msg = a[len("--message="):]; break
        result = {"commit": True, "msg": msg.strip(), "dir": os.path.expanduser(target or cd)}
        break
print(json.dumps(result))
PY
)

if [ -z "$PARSED" ] || [ "$(echo "$PARSED" | jq -r '.commit')" != "true" ]; then
  exit 0
fi
MSG=$(echo "$PARSED" | jq -r '.msg')
TARGET_DIR=$(echo "$PARSED" | jq -r '.dir')

if [ -z "$MSG" ]; then
  # Heredoc or EOF form — inject skill reminder and allow
  jq -n '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "allow",
      "permissionDecisionReason": "git-commit skill reminder: validate type(scope): description before committing"
    }
  }'
  exit 0
fi

# The subject (first line) carries the convention; the body is free text.
MSG=${MSG%%$'\n'*}

# Merge commits (two parents) record a merge of two histories, not authored
# work — git's standard "Merge branch/pull request/remote-tracking branch"
# messages are exempt from the type(scope) convention.
if echo "$MSG" | grep -qE "^Merge (branch|pull request|remote-tracking branch) "; then
  exit 0
fi

# Validate format: type(scope): description  OR  type: description
if ! echo "$MSG" | grep -qE '^(feat|fix|enh|doc|ci)(\([^)]+\))?: .+'; then
  jq -n --arg msg "$MSG" '{
    "hookSpecificOutput": {
      "hookEventName": "PreToolUse",
      "permissionDecision": "deny",
      "permissionDecisionReason": ("Commit message format invalid: \"" + $msg + "\"\n\nRequired: type(scope): imperative description\nTypes:    feat · fix · enh · doc · ci\nExample:  feat(core): add silver delta injection\n\nRun /git-commit skill before committing.")
    }
  }'
  exit 0
fi

# Extract scope (may be absent)
SCOPE=$(echo "$MSG" | python3 -c "
import re, sys
m = re.match(r'^[a-z]+\(([^)]+)\):', sys.stdin.read().strip())
print(m.group(1) if m else '')
" 2>/dev/null || true)

if [ -z "$SCOPE" ]; then
  # No scope — allowed (e.g. 'ci: ...')
  exit 0
fi

# Detect project type from the repo the commit targets (`git -C <dir>`, else the
# last `cd <dir>` before it, else the hook's cwd), not the session cwd.
REPO_ROOT=$(git -C "${TARGET_DIR:-.}" rev-parse --show-toplevel 2>/dev/null || echo "")

if [ -z "$REPO_ROOT" ] || [ ! -f "$SCOPES_FILE" ]; then
  exit 0
fi

RESULT=$(python3 - <<PYEOF
import json, os, sys

root = "$REPO_ROOT"
scope = "$SCOPE"

with open("$SCOPES_FILE") as f:
    data = json.load(f)

project_type = None
for ptype, info in data["project_types"].items():
    for marker in info.get("detect", []):
        if os.path.exists(os.path.join(root, marker)):
            project_type = ptype
            break
    if project_type:
        break

if project_type is None:
    print("UNKNOWN_PROJECT")
elif scope not in data["project_types"][project_type]["scopes"]:
    valid = ", ".join(data["project_types"][project_type]["scopes"])
    print(f"INVALID_SCOPE:{project_type}:{valid}")
else:
    print("OK")
PYEOF
)

case "$RESULT" in
  OK)
    exit 0
    ;;
  UNKNOWN_PROJECT)
    jq -n --arg scope "$SCOPE" '{
      "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": "Unknown project type — run /git-commit skill to define the scope list for this repo before committing."
      }
    }'
    exit 0
    ;;
  INVALID_SCOPE:*)
    PROJECT_TYPE=$(echo "$RESULT" | cut -d: -f2)
    VALID_SCOPES=$(echo "$RESULT" | cut -d: -f3)
    jq -n --arg scope "$SCOPE" --arg ptype "$PROJECT_TYPE" --arg valid "$VALID_SCOPES" '{
      "hookSpecificOutput": {
        "hookEventName": "PreToolUse",
        "permissionDecision": "deny",
        "permissionDecisionReason": ("Scope \"" + $scope + "\" is not in the locked list for project type \"" + $ptype + "\".\n\nValid scopes: " + $valid + "\n\nRun /git-commit skill to propose a new scope and get user validation before committing.")
      }
    }'
    exit 0
    ;;
esac
