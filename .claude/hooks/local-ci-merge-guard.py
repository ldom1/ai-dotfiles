#!/usr/bin/env python3
"""PreToolUse (Bash): deny `gh pr merge` unless the PR head has a fresh `local-ci/pull_request` success.

Active only in repos with `git config local-ci.guard true`. Any error, gap or mismatch denies (fail closed).
In every directory, guard on or off, it denies a merge aimed at another repo (`-R`, `GH_REPO`, `cd`, `env -C`, a URL for another repo) and a merge
through `gh api`: the guard value comes from the session directory, so these forms would bypass it.
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
DESC = re.compile(r"^full base=([0-9a-f]{40}) img=([0-9a-f]{12}) \S+")
SEPARATORS = {";", "&&", "||", "|", "&", "\n"}
VALUE_OPTS = {"-R", "--repo", "-t", "--subject", "-b", "--body", "-F", "--body-file", "-A", "--author-email",
              "--match-head-commit"}


def deny(reason: str) -> None:
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": "deny",
                                             "permissionDecisionReason": f"local-ci merge guard: {reason}"}}))
    sys.exit(0)


MERGE_RE = re.compile(r"\bgh\b.*\bpr\b.*\bmerge\b", re.S)
API_MERGE_RE = re.compile(r"pulls/[^/\s\"']+/merge|mergePullRequest", re.I)
CD_RE = re.compile(r"(?:^|[\s(])(?:cd|pushd)(?:\s|$)")
# In a command the parser cannot check: any repo flag, GH_REPO or directory change, anywhere.
REDIRECT_RE = re.compile(r"(?:^|[\s(;&|'\"`])(?:-R|-C|--repo\b|--chdir\b|GH_REPO=|(?:cd|pushd)(?:[\s;)'\"]|$))")
# A PR URL selector (`https://github.com/o/r/pull/5`, scheme optional) names the repo, like -R.
URL_SELECTOR_RE = re.compile(r"^(?:https?://)?([^/\s]+)/([^/\s]+)/([^/\s]+)/pull/", re.I)
ASSIGN_RE = re.compile(r"^\w+=")
REDIRECT = "run gh pr merge from the repo directory, without -R/GH_REPO/cd or a URL for another repo"


def parse(command: str) -> tuple[list[list[str]], list[str], bool, bool]:
    """(argument lists after `gh pr merge`, GH_REPO values, uncheckable, cd before a merge).

    Fail closed: `uncheckable` is true when the command may run `gh pr merge` in a form this parser cannot check
    (subshell, `bash -c`, `sudo`, `if ... then`, command substitution, unbalanced quotes, line continuation).
    """
    calls, env_repos, uncheckable, cd_seen, cd_before = [], [], False, False, False
    for line in command.split("\n"):
        lex = shlex.shlex(line, posix=True, punctuation_chars=";&|")
        lex.whitespace_split = True
        try:
            tokens = list(lex) + [";"]
        except ValueError:
            return calls, env_repos, bool(MERGE_RE.search(command)), cd_before
        cur = []
        for tok in tokens:
            if tok not in SEPARATORS:
                cur.append(tok)
                continue
            env_repos += [w[len("GH_REPO="):] for w in cur if w.startswith("GH_REPO=")]
            words = list(cur)
            while words and ASSIGN_RE.match(words[0]):
                words.pop(0)
            joined = " ".join(cur)
            if words[:3] == ["gh", "pr", "merge"]:
                calls.append(words[3:])
            elif MERGE_RE.search(joined):
                uncheckable = True
            else:
                cd_seen = cd_seen or bool(CD_RE.search(joined))
                cur = []
                continue
            cd_before = cd_before or cd_seen
            cur = []
    return calls, env_repos, uncheckable, cd_before


def gh(cwd, *args) -> str:
    return subprocess.run([GH, *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def split_args(args: list[str]) -> tuple[str | None, list[str]]:
    """(PR selector, repos named by `-R`/`--repo` or by a URL selector) of the arguments after `gh pr merge`."""
    selector, repos, i = None, [], 0
    while i < len(args):
        a = args[i]
        if a in VALUE_OPTS:
            if a in ("-R", "--repo") and i + 1 < len(args):
                repos.append(args[i + 1])
            i += 2
            continue
        if a.startswith("--repo="):
            repos.append(a[len("--repo="):])
        elif a.startswith("-R"):
            repos.append(a[2:].lstrip("="))
        elif not a.startswith("-") and selector is None:
            selector = a
        i += 1
    url = URL_SELECTOR_RE.match(selector or "")
    if url:  # a host other than github.com stays in the name, so it never equals the origin slug
        host, owner, name = url.groups()
        repos.append(f"{owner}/{name}" if host.lower() == "github.com" else f"{host}/{owner}/{name}")
    return selector, repos


def origin_slug(cwd: str) -> str | None:
    url = subprocess.run(["git", "-C", cwd, "remote", "get-url", "origin"], capture_output=True, text=True).stdout
    m = re.search(r"github\.com[:/]([^/]+)/(.+?)(?:\.git)?\s*$", url)
    return f"{m.group(1)}/{m.group(2)}" if m else None


def check(cwd: str, args: list[str]) -> None:
    selector, _repos = split_args(args)  # main() has checked the repos
    slug = origin_slug(cwd)
    if not slug:
        deny("cannot read the origin GitHub URL")
    pr = json.loads(gh(cwd, "pr", "view", *([selector] if selector else []), "--json", "number,headRefOid,baseRefName"))
    head = pr["headRefOid"]
    base_tip = gh(cwd, "api", f"repos/{slug}/branches/{pr['baseRefName']}", "-q", ".commit.sha")
    combined = json.loads(gh(cwd, "api", f"repos/{slug}/commits/{head}/status?per_page=100"))
    if combined.get("sha") != head:
        deny(f"combined status is for {combined.get('sha')}, not the PR head {head}")
    statuses = combined.get("statuses") or []
    if combined["total_count"] > len(statuses):
        deny(f"incomplete status response ({len(statuses)} of {combined.get('total_count')})")
    mine = [s for s in statuses if str(s.get("context", "")).lower() == CONTEXT]
    if not mine:
        deny(f"no {CONTEXT} status on {head[:12]}: run `local-ci run --event pull_request --pr {pr['number']}`")
    if len(mine) != 1:
        deny(f"expected exactly one {CONTEXT} status, found {len(mine)}")
    s = mine[0]
    if s.get("state") != "success":
        deny(f"{CONTEXT} state is {s.get('state')}")
    d = DESC.fullmatch(s.get("description") or "")
    if not d:
        deny(f"unexpected status description: {s.get('description')!r}")
    if d.group(1) != base_tip:
        deny(f"stale: re-run local-ci (tested base {d.group(1)[:12]}, base is now {base_tip[:12]})")
    image_id = os.environ.get("LOCAL_CI_IMAGE_ID") or subprocess.run(
        ["docker", "image", "inspect", "-f", "{{.Id}}", IMAGE], capture_output=True, text=True).stdout.strip()
    if image_id[7:19] != d.group(2):
        deny(f"image changed since the run (status {d.group(2)}, local {image_id[7:19] or 'missing'}): re-run local-ci")
    # The combined status has no `creator`: read it from the statuses list entry with the same id.
    listed = json.loads(gh(cwd, "api", f"repos/{slug}/commits/{head}/statuses?per_page=100"))
    entry = next((e for e in listed if e.get("id") == s["id"]), None)
    if entry is None:
        deny(f"status {s['id']} is not in the statuses list of {head[:12]}")
    creator = (entry.get("creator") or {}).get("login")
    if creator != gh(cwd, "api", "user", "-q", ".login"):
        deny(f"status creator {creator} is not the gh user")


def main(raw: str) -> None:
    data = json.loads(raw or "{}")
    if data.get("tool_name") != "Bash":
        return
    cwd = data.get("cwd") or os.getcwd()
    command = data.get("tool_input", {}).get("command", "")
    if API_MERGE_RE.search(command):
        deny("merge PRs with a plain `gh pr merge <N>` from the repo directory")
    calls, env_repos, uncheckable, cd_before = parse(command)
    if not calls and not uncheckable:
        return
    # Before the guard value: it is read from the session directory, which these forms leave.
    if cd_before or (uncheckable and REDIRECT_RE.search(command)):
        deny(REDIRECT)
    repos = env_repos + [r for args in calls for r in split_args(args)[1]]
    if repos:
        slug = origin_slug(cwd)
        other = [r for r in repos if not slug or r.lower() != slug.lower()]
        if other:
            deny(f"{REDIRECT} ({other[0]} is not {slug or 'the origin of ' + cwd})")
    on = subprocess.run(["git", "-C", cwd, "config", "--get", "local-ci.guard"], capture_output=True, text=True)
    if on.stdout.strip() != "true":
        return
    if uncheckable:
        deny("cannot parse this gh pr merge command; run it as a plain `gh pr merge <N>` line")
    for args in calls:
        try:
            check(cwd, args)
        except Exception as e:  # SystemExit from deny() is not an Exception; anything else must deny, never crash open
            deny(f"cannot verify the local-ci status ({type(e).__name__}): denied")


if __name__ == "__main__":
    stdin = sys.stdin.read()
    try:
        main(stdin)
    except Exception as e:  # bad input or a bug outside check(): deny what may be a merge, allow the rest
        if MERGE_RE.search(stdin) or API_MERGE_RE.search(stdin):
            deny(f"cannot read the hook input ({type(e).__name__}): denied")
