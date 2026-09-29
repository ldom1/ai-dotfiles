#!/usr/bin/env python3
"""git-promotion: move code between a repo's stage branches with a version tag.

Stages come from .git-promotion.json at the repo root (see SKILL.md):

- two or more stages (develop -> preprod -> main, or develop -> main): each stage
  is fast-forwarded from the previous one; intermediate stages get alpha tags,
  the last stage gets the release tag and a GitHub Release.
- one stage (main only, no preprod): PRs are the source -- `--pr N` squash-merges
  the PR, then tags the merge commit and creates the GitHub Release.

Defaults to a dry run (no push, no merge, no gate) -- pass --execute to act.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import git_ops  # noqa: E402
import reconciliation  # noqa: E402
import versioning  # noqa: E402
from versioning import ZERO, Version  # noqa: E402

CONFIG_FILE = ".git-promotion.json"
EXAMPLE_CONFIG = """{
  "stages": ["main"],
  "tag_prefix": "v",
  "gate": [["uv", "run", "pytest", "-q"]],
  "changelog": "CHANGELOG.md"
}"""


class ConfigError(ValueError):
    pass


def load_config(repo_dir: str) -> dict:
    path = Path(repo_dir) / CONFIG_FILE
    if not path.exists():
        raise ConfigError(f"no {CONFIG_FILE} at the repo root. Example:\n{EXAMPLE_CONFIG}")
    config = json.loads(path.read_text())
    stages = config.get("stages")
    if not stages or not all(isinstance(s, str) for s in stages):
        raise ConfigError(f"{CONFIG_FILE}: 'stages' must be a non-empty list of branch names")
    return {
        "stages": stages,
        "tag_prefix": config.get("tag_prefix", ""),
        "gate": config.get("gate", []),
        "changelog": config.get("changelog"),
    }


def promote(target: str, repo_dir: str, execute: bool, pr: int | None = None) -> int:
    try:
        config = load_config(repo_dir)
    except ConfigError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 2
    stages = config["stages"]
    if target not in stages:
        print(f"unknown target {target!r}, must be one of {stages}", file=sys.stderr)
        return 2

    if len(stages) == 1:
        if pr is None:
            print(
                f"REFUSED: {target} is the only stage -- releases come from a PR: --pr N",
                file=sys.stderr,
            )
            return 2
        return _release_pr(target, pr, config, repo_dir, execute)

    if pr is not None:
        print(
            f"REFUSED: --pr is for single-stage repos; PRs here merge into {stages[0]}",
            file=sys.stderr,
        )
        return 2
    index = stages.index(target)
    if index == 0:
        print(f"REFUSED: {target} is the first stage; nothing promotes into it", file=sys.stderr)
        return 2
    return _promote_stage(target, stages[index - 1], config, repo_dir, execute)


# ── Multi-stage: fast-forward the target to the previous stage ──────────────────


def _promote_stage(target: str, source: str, config: dict, repo_dir: str, execute: bool) -> int:
    stages = config["stages"]
    is_release = target == stages[-1]

    git_ops.fetch_origin(repo_dir)
    source_sha = git_ops.rev_parse(f"origin/{source}", repo_dir)

    if not git_ops.is_ancestor(f"origin/{target}", source_sha, repo_dir):
        return _handle_diverged_target(target, source, source_sha, stages, repo_dir, is_release)

    if git_ops.rev_parse(f"origin/{target}", repo_dir) == source_sha:
        print(f"nothing to promote: origin/{target} already == origin/{source} ({source_sha})")
        return 0

    if not _check_and_run_gate(config["gate"], source, source_sha, repo_dir, execute):
        return 1

    version, summary, subjects = _compute_version(source_sha, config, repo_dir, is_release)
    notes = None
    if version is not None and is_release:
        notes = _release_notes(source_sha, version, subjects, config, repo_dir, execute)
        if notes is None:
            return 1

    if not execute:
        print(
            f"DRY RUN -- would promote origin/{source} ({source_sha}) to {target}. "
            f"Version: {_describe(version, config)}"
        )
        return 0

    if version is None:
        git_ops.push_branch_only(source_sha, target, repo_dir)
        print(f"Promoted {source} -> {target}: {source_sha} (no versionable change, no new tag)")
        return 0
    tag_name = config["tag_prefix"] + str(version)
    git_ops.create_tag(tag_name, source_sha, _tag_message(summary), repo_dir)
    git_ops.push_atomic(tag_name, source_sha, target, repo_dir)
    print(f"Promoted {source} -> {target}: {source_sha} tagged {tag_name}")
    return _create_github_release(tag_name, notes, repo_dir) if is_release else 0


def _handle_diverged_target(
    target: str, source: str, source_sha: str, stages: list[str], repo_dir: str, is_release: bool
) -> int:
    diverged = git_ops.commits_ahead(f"origin/{target}", source_sha, repo_dir)
    if is_release and diverged:
        candidates = git_ops.commits_ahead(f"origin/{stages[0]}", f"origin/{target}", repo_dir)
        if reconciliation.is_authorized_divergence(diverged, candidates, repo_dir):
            print(
                f"AUTHORIZED emergency-hotfix divergence on {target}: every diverged commit "
                f"carries Emergency-Reconciliation: and has a patch-id twin on {stages[0]}. "
                "A scoped reset is required, not a fast-forward -- see SKILL.md "
                "'Emergency hotfix'. Do it by hand, then re-run this command."
            )
            return 3
    print(f"REFUSED: origin/{target} is not an ancestor of {source_sha} (origin/{source}'s tip).")
    print(f"Diverged commit(s) on {target}:")
    for sha in diverged:
        print(f"  {sha}")
    print("A human must reconcile this -- it is never auto-resolved.")
    return 1


def _compute_version(source_sha: str, config: dict, repo_dir: str, is_release: bool):
    prefix = config["tag_prefix"]
    source_tags = git_ops.tags_merged(source_sha, repo_dir)
    current_final = versioning.highest_final_tag(source_tags, prefix)
    base_sha = (
        git_ops.rev_parse(f"{prefix}{current_final}^{{commit}}", repo_dir)
        if current_final
        else None
    )
    messages = git_ops.commit_messages_between(base_sha, source_sha, repo_dir)
    summary = versioning.summarize_commits(messages)
    current_final = current_final or ZERO
    if is_release:
        version = versioning.next_release_version(current_final, summary, source_tags, prefix)
    else:
        version = versioning.next_prerelease_version(current_final, summary, source_tags, prefix)
    return version, summary, [m.splitlines()[0] for m in messages]


# ── Single stage: squash-merge a PR into the release branch ─────────────────────


def _release_pr(target: str, pr: int, config: dict, repo_dir: str, execute: bool) -> int:
    prefix = config["tag_prefix"]
    info = git_ops.gh_json(
        [
            "pr", "view", str(pr), "--json",
            "state,baseRefName,headRefName,headRefOid,mergeCommit,commits,url",
        ],
        repo_dir,
    )
    if info["baseRefName"] != target:
        print(f"REFUSED: PR #{pr} targets {info['baseRefName']!r}, not {target!r}", file=sys.stderr)
        return 1
    if info["state"] == "CLOSED":
        print(f"REFUSED: PR #{pr} is closed without merge", file=sys.stderr)
        return 1
    merged = info["state"] == "MERGED"

    git_ops.fetch_origin(repo_dir)
    git_ops.fetch_ref(f"pull/{pr}/head", repo_dir)
    head_sha = info["headRefOid"]

    if merged:
        merge_sha = info["mergeCommit"]["oid"]
        released = [t for t in git_ops.tags_pointing_at(merge_sha, repo_dir)
                    if versioning.parse_tag(t, prefix)]
        if released:
            print(f"nothing to do: PR #{pr} is merged and released as {released[0]}")
            return 0
        print(f"PR #{pr} is already merged ({merge_sha}) but untagged -- resuming at the tag step")
        base = f"{merge_sha}^"
    else:
        if not _check_and_run_gate(config["gate"], info["headRefName"], head_sha, repo_dir, execute):
            return 1
        base = f"origin/{target}"

    current_final = versioning.highest_final_tag(git_ops.tags_merged(base, repo_dir), prefix) or ZERO
    messages = [f"{c['messageHeadline']}\n\n{c['messageBody']}".strip() for c in info["commits"]]
    summary = versioning.summarize_commits(messages)
    version = versioning.next_release_version(current_final, summary, [], prefix)
    notes = None
    if version is not None:
        subjects = [c["messageHeadline"] for c in info["commits"]]
        notes = _release_notes(head_sha, version, subjects, config, repo_dir, execute)
        if notes is None:
            return 1

    if not execute:
        action = "tag" if merged else "squash-merge"
        print(
            f"DRY RUN -- would {action} PR #{pr} ({info['url']}) on {target}. "
            f"Version: {_describe(version, config)}"
        )
        return 0

    if not merged:
        repo = git_ops.gh_json(["repo", "view", "--json", "nameWithOwner"], repo_dir)
        # --repo keeps gh from switching or deleting the local checkout's branch.
        git_ops.gh(
            [
                "pr", "merge", str(pr), "--repo", repo["nameWithOwner"], "--squash",
                "--delete-branch", "--match-head-commit", head_sha,
            ],
            repo_dir,
        )
        merge_sha = git_ops.gh_json(["pr", "view", str(pr), "--json", "mergeCommit"], repo_dir)[
            "mergeCommit"
        ]["oid"]
        git_ops.fetch_origin(repo_dir)
        print(f"Merged PR #{pr} into {target}: {merge_sha}")

    if version is None:
        print("No versionable change -- merged, no new tag")
        return 0
    tag_name = prefix + str(version)
    git_ops.create_tag(tag_name, merge_sha, _tag_message(summary), repo_dir)
    git_ops.push_tag(tag_name, repo_dir)
    print(f"Tagged {merge_sha} as {tag_name}")
    return _create_github_release(tag_name, notes, repo_dir)


# ── Shared steps ────────────────────────────────────────────────────────────────


def _check_and_run_gate(
    gate: list[list[str]], branch: str, sha: str, repo_dir: str, execute: bool
) -> bool:
    """The local-checkout checks exist so the gate tests exactly the commit being
    promoted -- with no gate there is nothing to test, and they are skipped."""
    if not gate:
        print("Gate: none configured")
        return True
    if git_ops.current_branch(repo_dir) != branch:
        print(f"REFUSED: checked-out branch must be {branch!r} to run the gate", file=sys.stderr)
        return False
    if not git_ops.is_clean_tree(repo_dir):
        print("REFUSED: working tree is not clean", file=sys.stderr)
        return False
    if git_ops.rev_parse("HEAD", repo_dir) != sha:
        print(f"REFUSED: local HEAD is not {sha} -- pull first", file=sys.stderr)
        return False
    print("Gate: " + " && ".join(" ".join(cmd) for cmd in gate))
    if not execute:
        print("(dry run: gate not executed)")
        return True
    for cmd in gate:
        if subprocess.run(cmd, cwd=repo_dir).returncode != 0:
            print(f"REFUSED: gate failed: {' '.join(cmd)}", file=sys.stderr)
            return False
    return True


def _release_notes(
    sha: str, version: Version, subjects: list[str], config: dict, repo_dir: str, execute: bool
) -> str | None:
    """The CHANGELOG section for the version when a changelog is configured (it
    must exist at the promoted commit), else the list of commit subjects."""
    path = config["changelog"]
    if not path:
        return "\n".join(f"- {s}" for s in subjects)
    section = versioning.changelog_section(git_ops.show_file(sha, path, repo_dir) or "", version)
    if section:
        return section
    message = (
        f"{path} at {sha[:7]} has no '## [{version}]' section -- cut [Unreleased] into "
        f"'## [{version}] - YYYY-MM-DD' on the source branch, push, then re-run"
    )
    if execute:
        print(f"REFUSED: {message}", file=sys.stderr)
        return None
    print(f"NOTE: {message}")
    return ""


def _describe(version: Version | None, config: dict) -> str:
    if version is None:
        return "(no versionable change -- no new tag)"
    return config["tag_prefix"] + str(version)


def _tag_message(summary) -> str:
    parts = []
    if summary.has_feat:
        parts.append("feat")
    if summary.has_fix_or_enh:
        parts.append("fix/enh")
    if summary.has_breaking:
        parts.append("BREAKING CHANGE")
    return f"includes: {', '.join(parts)}" if parts else "no versionable change"


def _create_github_release(tag_name: str, notes: str, repo_dir: str) -> int:
    """Runs after the tag is pushed, so a failure here must not read as a failed
    promotion -- it exits 4 with the command to finish by hand."""
    try:
        git_ops.gh(
            ["release", "create", tag_name, "--title", tag_name, "--notes", notes, "--verify-tag"],
            repo_dir,
        )
    except (git_ops.GitCommandError, OSError) as exc:
        print(f"WARNING: tag {tag_name} pushed but release not created: {exc}", file=sys.stderr)
        print(f"Finish by hand: gh release create {tag_name} --title {tag_name}", file=sys.stderr)
        return 4
    print(f"Released {tag_name}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("target", help="stage branch to promote into (e.g. preprod, main)")
    parser.add_argument("--pr", type=int, help="single-stage repos: the PR to merge and release")
    parser.add_argument("--execute", action="store_true", help="actually act -- default is dry run")
    parser.add_argument("--repo-dir", default=".")
    args = parser.parse_args()
    return promote(args.target, args.repo_dir, args.execute, args.pr)


if __name__ == "__main__":
    sys.exit(main())
