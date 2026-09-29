"""Classifies a release-branch divergence as an authorized emergency hotfix
(every diverged commit carries an `Emergency-Reconciliation:` footer and has a
cherry-picked twin on the integration branch) vs. an unrecognized divergence
that must stop for a human. Never auto-resolves anything.
"""

from __future__ import annotations

import re
import subprocess

_FOOTER_RE = re.compile(r"^Emergency-Reconciliation: .+", re.MULTILINE)


def carries_reconciliation_footer(commit_message: str) -> bool:
    return bool(_FOOTER_RE.search(commit_message))


def patch_id(sha: str, repo_dir: str) -> str:
    """Content-based identity: a cherry-pick gets a new SHA but the same patch-id."""
    show = subprocess.run(
        ["git", "show", sha], cwd=repo_dir, capture_output=True, text=True, check=True
    )
    result = subprocess.run(
        ["git", "patch-id"],
        cwd=repo_dir,
        input=show.stdout,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.split()[0]


def is_authorized_divergence(
    diverged_shas: list[str], candidate_shas: list[str], repo_dir: str
) -> bool:
    """True only if EVERY diverged commit carries the footer AND has a patch-id
    match in candidate_shas. False for an empty diverged_shas list."""
    if not diverged_shas:
        return False
    candidate_patch_ids = {patch_id(sha, repo_dir) for sha in candidate_shas}
    for sha in diverged_shas:
        message = subprocess.run(
            ["git", "log", "-1", "--format=%B", sha],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            check=True,
        ).stdout
        if not carries_reconciliation_footer(message):
            return False
        if patch_id(sha, repo_dir) not in candidate_patch_ids:
            return False
    return True
