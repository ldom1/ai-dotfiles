"""Thin subprocess wrappers over git/gh -- no version math here (see versioning.py)
and no decisions about what's authorized (see reconciliation.py). Every function
takes repo_dir explicitly rather than relying on cwd.
"""

from __future__ import annotations

import json
import subprocess


class GitCommandError(RuntimeError):
    pass


def _run(cmd: list[str], repo_dir: str) -> str:
    result = subprocess.run(cmd, cwd=repo_dir, capture_output=True, text=True)
    if result.returncode != 0:
        raise GitCommandError(f"{' '.join(cmd)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _git(args: list[str], repo_dir: str) -> str:
    return _run(["git", *args], repo_dir)


def gh(args: list[str], repo_dir: str) -> str:
    return _run(["gh", *args], repo_dir)


def gh_json(args: list[str], repo_dir: str) -> dict:
    return json.loads(gh(args, repo_dir))


def fetch_origin(repo_dir: str) -> None:
    _git(["fetch", "--tags", "origin"], repo_dir)


def fetch_ref(ref: str, repo_dir: str) -> None:
    _git(["fetch", "origin", ref], repo_dir)


def rev_parse(ref: str, repo_dir: str) -> str:
    return _git(["rev-parse", ref], repo_dir)


def is_ancestor(maybe_ancestor: str, descendant: str, repo_dir: str) -> bool:
    result = subprocess.run(
        ["git", "merge-base", "--is-ancestor", maybe_ancestor, descendant],
        cwd=repo_dir,
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def tags_merged(sha: str, repo_dir: str) -> list[str]:
    """Every tag reachable as an ancestor of sha -- never git describe."""
    return [line for line in _git(["tag", "--merged", sha], repo_dir).splitlines() if line]


def tags_pointing_at(sha: str, repo_dir: str) -> list[str]:
    return [
        line for line in _git(["tag", "--points-at", sha], repo_dir).splitlines() if line
    ]


def commits_ahead(head_ref: str, base_ref: str, repo_dir: str) -> list[str]:
    """SHAs reachable from head_ref but not from base_ref (git log base..head)."""
    output = _git(["log", f"{base_ref}..{head_ref}", "--format=%H"], repo_dir)
    return [line for line in output.splitlines() if line]


def commit_messages_between(base: str | None, head: str, repo_dir: str) -> list[str]:
    """Full messages (subject + body/footers), one per commit; base None means the
    whole history of head. NUL-separated so a multi-line body is never mis-split;
    the leading "\\n" git log puts before every entry but the first is stripped, or
    summarize_commits would read an empty subject for all but one commit."""
    rev_range = f"{base}..{head}" if base else head
    output = _git(["log", rev_range, "--format=%B%x00"], repo_dir)
    return [msg.strip("\n") for msg in output.split("\x00") if msg.strip()]


def show_file(sha: str, path: str, repo_dir: str) -> str | None:
    try:
        return _git(["show", f"{sha}:{path}"], repo_dir)
    except GitCommandError:
        return None


def current_branch(repo_dir: str) -> str:
    return _git(["branch", "--show-current"], repo_dir)


def is_clean_tree(repo_dir: str) -> bool:
    return _git(["status", "--porcelain"], repo_dir) == ""


def create_tag(tag_name: str, sha: str, message: str, repo_dir: str) -> None:
    """Always annotated -- a lightweight tag has no message and no tagger."""
    _git(["tag", "-a", tag_name, sha, "-m", message], repo_dir)


def push_tag(tag_name: str, repo_dir: str) -> None:
    _git(["push", "origin", f"refs/tags/{tag_name}"], repo_dir)


def push_atomic(
    tag_name: str, target_sha: str, target_branch: str, repo_dir: str
) -> None:
    """Tag (already created locally) and branch move in one transaction, so a
    branch never lands without its tag or the other way round."""
    _git(
        [
            "push",
            "--atomic",
            "origin",
            f"refs/tags/{tag_name}",
            f"{target_sha}:refs/heads/{target_branch}",
        ],
        repo_dir,
    )


def push_branch_only(target_sha: str, target_branch: str, repo_dir: str) -> None:
    _git(["push", "origin", f"{target_sha}:refs/heads/{target_branch}"], repo_dir)
