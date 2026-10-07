#!/usr/bin/env python3
"""Run a Claude Code hook as a Mistral Vibe hook (pre_tool, post_agent).

Usage: vibe-claude-hook.py <claude-hook>   (Vibe event JSON on stdin)

Only exact refusal shapes become {"decision": "deny"}. Claude "ask" becomes a deny: Vibe has no ask.
Any other output, or a hook exit code other than 0 and 2, is an adapter error: details on stderr,
exit 1. Vibe then denies the call when the hook is strict, or warns.
"""
import json
import re
import subprocess
import sys

TAG = re.compile(r"^\[[\w-]+\]\s*")  # Vibe names the hook itself: drop "[stop-check] "
HSO_KEYS = {"hookEventName", "permissionDecision", "permissionDecisionReason"}


def deny(reason: str) -> dict:
    return {"decision": "deny", "reason": TAG.sub("", reason)}


def translate(out: object) -> dict | None:
    """Map one Claude hook output to Vibe output. None means the shape is unknown."""
    if not isinstance(out, dict):
        return None
    if out.keys() == {"decision", "reason"} and out["decision"] == "block" and isinstance(out["reason"], str):
        return deny(out["reason"])
    if out.keys() == {"systemMessage"} and isinstance(out["systemMessage"], str):
        return {"system_message": out["systemMessage"]}
    hso = out.get("hookSpecificOutput")
    if out.keys() != {"hookSpecificOutput"} or not isinstance(hso, dict) or not hso.keys() <= HSO_KEYS:
        return None
    decision, reason = hso.get("permissionDecision"), str(hso.get("permissionDecisionReason", ""))
    if decision == "allow":
        return {}
    if decision == "deny":
        return deny(reason)
    if decision == "ask":
        return deny(f"needs confirmation: {reason.rstrip('.')}. Ask the user to run it.")
    return None


def fail(msg: str) -> None:
    sys.stderr.write(f"vibe-claude-hook: {msg}\n")
    sys.exit(1)


def main() -> None:
    if len(sys.argv) != 2:
        fail("usage: vibe-claude-hook.py <claude-hook>")
    hook = sys.argv[1]
    event = json.load(sys.stdin)
    event["stop_hook_active"] = False
    if event.get("tool_name") == "bash":
        event["tool_name"] = "Bash"
    try:
        r = subprocess.run([hook], input=json.dumps(event), capture_output=True, text=True)
    except OSError as e:
        fail(f"cannot run {hook}: {e}")
    if r.returncode == 2:
        result = deny(r.stderr.strip() or f"{hook} exited 2")
    elif r.returncode != 0:
        fail(f"{hook} exited {r.returncode}: {r.stderr.strip() or r.stdout.strip()}")
    elif not r.stdout.strip():
        return
    else:
        try:
            result = translate(json.loads(r.stdout))
        except json.JSONDecodeError:
            result = None
        if result is None:
            fail(f"{hook} printed an unknown output: {r.stdout.strip()[:500]}")
    if result:
        print(json.dumps(result))


if __name__ == "__main__":
    main()
