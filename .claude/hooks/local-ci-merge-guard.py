#!/usr/bin/env python3
"""PreToolUse (Bash): deny `gh pr merge` unless the PR head has a fresh `local-ci/pull_request` success.

Active only in repos with `git config local-ci.guard true`. Any error, gap or mismatch denies (fail closed).
Scope: this guards merges that Claude Code runs through Bash. The GitHub web UI, a human `gh` and other tools are
not guarded, and GitHub Free private repos enforce nothing. Spec: vault [[2026-10-07-local-ci-replication-design]] §5, §7.
"""
import json
import os
import re
import shlex
import subprocess
import sys

GH = os.environ.get("LOCAL_CI_GH", "gh")
IMAGE = "local-ci-runner:24.04"
CONTEXT = "local-ci/pull_request"
DESC = re.compile(r"^full base=([0-9a-f]{40}) img=([0-9a-f]{12}) \S+$")
SEPARATORS = {";", "&&", "||", "|", "&", "\n"}
VALUE_OPTS = {"-R", "--repo", "-t", "--subject", "-b", "--body", "-F", "--body-file", "-A", "--author-email",
              "--match-head-commit"}


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": f"local-ci merge guard: {reason}"}}))
    sys.exit(0)


def merge_calls(command: str) -> list[list[str]]:
    """Argument lists that follow `gh pr merge` in each simple command."""
    lex = shlex.shlex(command, posix=True, punctuation_chars=";&|")
    lex.whitespace_split = True
    calls, cur = [], []
    for tok in list(lex) + [";"]:
        if tok in SEPARATORS:
            words = [w for w in cur if not re.match(r"^\w+=", w)]
            if words[:3] == ["gh", "pr", "merge"]:
                calls.append(words[3:])
            cur = []
        else:
            cur.append(tok)
    return calls


def gh(cwd, *args) -> str:
    return subprocess.run([GH, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def check(cwd: str, args: list[str]) -> None:
    selector, repo_flag, i = None, None, 0
    while i < len(args):
        a = args[i]
        if a in VALUE_OPTS:
            if a in ("-R", "--repo") and i + 1 < len(args):
                repo_flag = args[i + 1]
            i += 2
            continue
        if a.startswith("--repo="):
            repo_flag = a[len("--repo="):]
        elif not a.startswith("-") and selector is None:
            selector = a
        i += 1
    url = subprocess.run(["git", "-C", cwd, "remote", "get-url", "origin"], capture_output=True, text=True).stdout
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?\s*$", url)
    if not m:
        deny("cannot read the origin GitHub URL")
    slug = f"{m.group(1)}/{m.group(2)}"
    if repo_flag and repo_flag.lower() != slug.lower():
        deny(f"run gh pr merge from the repo directory without -R ({repo_flag} is not {slug})")
    pr = json.loads(gh(cwd, "pr", "view", *([selector] if selector else []), "--json", "number,headRefOid,baseRefName"))
    head = pr["headRefOid"]
    base_tip = gh(cwd, "api", f"repos/{slug}/branches/{pr['baseRefName']}", "-q", ".commit.sha")
    combined = json.loads(gh(cwd, "api", f"repos/{slug}/commits/{head}/status?per_page=100"))
    if combined.get("sha") != head:
        deny(f"combined status is for {combined.get('sha')}, not the PR head {head}")
    statuses = combined.get("statuses") or []
    if combined.get("total_count", 0) > len(statuses):
        deny(f"incomplete status response ({len(statuses)} of {combined.get('total_count')})")
    mine = [s for s in statuses if str(s.get("context", "")).lower() == CONTEXT]
    if not mine:
        deny(f"no {CONTEXT} status on {head[:12]}: run `local-ci run --event pull_request --pr {pr['number']}`")
    if len(mine) != 1:
        deny(f"expected exactly one {CONTEXT} status, found {len(mine)}")
    s = mine[0]
    if s.get("state") != "success":
        deny(f"{CONTEXT} state is {s.get('state')}")
    d = DESC.match(s.get("description") or "")
    if not d:
        deny(f"unexpected status description: {s.get('description')!r}")
    if d.group(1) != base_tip:
        deny(f"stale: re-run local-ci (tested base {d.group(1)[:12]}, base is now {base_tip[:12]})")
    image_id = os.environ.get("LOCAL_CI_IMAGE_ID") or subprocess.run(
        ["docker", "image", "inspect", "-f", "{{.Id}}", IMAGE], capture_output=True, text=True).stdout.strip()
    if image_id[7:19] != d.group(2):
        deny(f"image changed since the run (status {d.group(2)}, local {image_id[7:19] or 'missing'}): re-run local-ci")
    if (s.get("creator") or {}).get("login") != gh(cwd, "api", "user", "-q", ".login"):
        deny(f"status creator {(s.get('creator') or {}).get('login')} is not the gh user")


def main() -> None:
    data = json.loads(sys.stdin.read() or "{}")
    if data.get("tool_name") != "Bash":
        return
    cwd = data.get("cwd") or os.getcwd()
    try:
        calls = merge_calls(data.get("tool_input", {}).get("command", ""))
    except ValueError:
        return  # unbalanced quotes: the command cannot run either
    if not calls:
        return
    on = subprocess.run(["git", "-C", cwd, "config", "--get", "local-ci.guard"], capture_output=True, text=True)
    if on.stdout.strip() != "true":
        return
    for args in calls:
        try:
            check(cwd, args)
        except Exception as e:  # SystemExit from deny() is not an Exception; anything else must deny, never crash open
            deny(f"cannot verify the local-ci status ({type(e).__name__}): denied")


if __name__ == "__main__":
    main()
