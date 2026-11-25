#!/usr/bin/env python3
"""PreToolUse (Write): a vault spec must open with `## TL;DR` before any other `## ` section.

AGENTS.md (Local Brain): every spec starts with a TL;DR the owner reads instead of the whole spec.
Scope: Write of `*/inbox/daily/specs/**/*.md`. Edit is not checked, so older specs stay editable.
Bad input fails open: this hook guards a convention, not safety.
"""
import json
import re
import sys

FENCE = re.compile(r"^```.*?^```", re.M | re.S)
SECTION = re.compile(r"^## (.+?)\s*$", re.M)
REASON = (
    "Spec without a TL;DR first. Add `## TL;DR` (5 to 8 bullets: problem, decision, what changes, "
    "what is out, open choice) before `## Context`, then write the file again."
)


def main() -> int:
    try:
        tool_input = json.load(sys.stdin)["tool_input"]
        path, content = tool_input["file_path"], tool_input["content"]
    except (ValueError, KeyError, TypeError):
        return 0
    if "/inbox/daily/specs/" not in path or not path.endswith(".md"):
        return 0
    first = SECTION.search(FENCE.sub("", content))
    if first and first.group(1) == "TL;DR":
        return 0
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "PreToolUse", "permissionDecision": "deny", "permissionDecisionReason": REASON}}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
