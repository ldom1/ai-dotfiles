import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import git_ops
from promote import promote


def _git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True)
    return result.stdout.strip()


def _commit(repo_dir: Path, message: str, content: str = "x", path: str = "file.txt") -> str:
    (repo_dir / path).write_text(content)
    _git(repo_dir, "add", path)
    _git(repo_dir, "commit", "-q", "-m", message)
    return _git(repo_dir, "rev-parse", "HEAD")


def _init_repo(tmp_path: Path, config: dict) -> Path:
    remote_dir = tmp_path / "remote.git"
    remote_dir.mkdir()
    subprocess.run(["git", "init", "-q", "--bare"], cwd=remote_dir, check=True)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-q", "-b", "scratch")  # never a stage name, whatever init.defaultBranch says
    _git(repo_dir, "config", "user.email", "test@example.com")
    _git(repo_dir, "config", "user.name", "Test")
    _git(repo_dir, "remote", "add", "origin", str(remote_dir))
    (repo_dir / ".git-promotion.json").write_text(json.dumps(config))
    _git(repo_dir, "add", ".git-promotion.json")
    return repo_dir


def _remote_ref(repo_dir: Path, ref: str) -> str:
    out = _git(repo_dir, "ls-remote", "origin", ref)
    return out.split()[0] if out else ""


# ── Multi-stage: develop -> preprod -> main ─────────────────────────────────────


@pytest.fixture
def three_stage_repo(tmp_path: Path) -> Path:
    repo_dir = _init_repo(
        tmp_path, {"stages": ["develop", "preprod", "main"], "gate": [["true"]]}
    )
    root = _commit(repo_dir, "fix(core): initial commit", "one")
    _git(repo_dir, "tag", "-a", "0.2.1", root, "-m", "start")
    for branch in ("main", "preprod", "develop"):
        _git(repo_dir, "branch", "-f", branch, root)
    _git(repo_dir, "push", "-q", "origin", "main", "preprod", "develop", "0.2.1")
    _git(repo_dir, "checkout", "-q", "develop")
    return repo_dir


def test_refuses_without_a_config(tmp_path: Path):
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-q", "-b", "scratch")  # never a stage name, whatever init.defaultBranch says
    assert promote("main", str(repo_dir), execute=False) == 2


def test_refuses_to_promote_into_the_first_stage(three_stage_repo: Path):
    assert promote("develop", str(three_stage_repo), execute=False) == 2


def test_no_op_when_target_already_equals_source(three_stage_repo: Path):
    assert promote("preprod", str(three_stage_repo), execute=False) == 0


def test_refuses_when_target_has_diverged_from_source(three_stage_repo: Path):
    _git(three_stage_repo, "checkout", "-q", "preprod")
    _commit(three_stage_repo, "fix(core): a commit only on preprod", "diverged")
    _git(three_stage_repo, "push", "-q", "origin", "preprod")
    _git(three_stage_repo, "checkout", "-q", "develop")
    assert promote("preprod", str(three_stage_repo), execute=False) == 1


def test_version_scan_starts_at_the_last_release_tag(tmp_path: Path, capsys):
    repo_dir = _init_repo(tmp_path, {"stages": ["develop", "preprod", "main"]})
    root = _commit(repo_dir, "feat(core): ancient feat", "one")
    _git(repo_dir, "tag", "-a", "0.2.1", root, "-m", "start")
    tip = _commit(repo_dir, "fix(core): change after the tag", "two")
    _git(repo_dir, "branch", "-f", "main", root)
    _git(repo_dir, "branch", "-f", "preprod", root)
    _git(repo_dir, "branch", "-f", "develop", tip)
    _git(repo_dir, "push", "-q", "origin", "main", "preprod", "develop", "0.2.1")

    assert promote("preprod", str(repo_dir), execute=False) == 0
    out = capsys.readouterr().out
    assert "Version: 0.2.2a1" in out


def test_dry_run_reports_the_version_without_pushing(three_stage_repo: Path, capsys):
    before = _remote_ref(three_stage_repo, "refs/heads/preprod")
    _commit(three_stage_repo, "fix(core): a real change", "changed")
    _git(three_stage_repo, "push", "-q", "origin", "develop")

    assert promote("preprod", str(three_stage_repo), execute=False) == 0
    out = capsys.readouterr().out
    assert "DRY RUN" in out and "0.2.2a1" in out
    assert _remote_ref(three_stage_repo, "refs/heads/preprod") == before


def test_execute_pushes_tag_and_branch_atomically(three_stage_repo: Path):
    sha = _commit(three_stage_repo, "fix(core): a real change", "changed")
    _git(three_stage_repo, "push", "-q", "origin", "develop")

    assert promote("preprod", str(three_stage_repo), execute=True) == 0
    assert _remote_ref(three_stage_repo, "refs/heads/preprod") == sha
    assert "0.2.2a1" in _git(three_stage_repo, "ls-remote", "--tags", "origin")


def test_execute_refuses_when_the_gate_fails(tmp_path: Path):
    repo_dir = _init_repo(tmp_path, {"stages": ["develop", "main"], "gate": [["false"]]})
    root = _commit(repo_dir, "fix(core): initial", "one")
    _git(repo_dir, "branch", "-f", "main", root)
    _git(repo_dir, "checkout", "-q", "-b", "develop")
    _commit(repo_dir, "fix(core): change", "two")
    _git(repo_dir, "push", "-q", "origin", "main", "develop")

    assert promote("main", str(repo_dir), execute=True) == 1
    assert _remote_ref(repo_dir, "refs/heads/main") == root


def test_doc_only_commits_fast_forward_without_a_tag(three_stage_repo: Path):
    sha = _commit(three_stage_repo, "doc(docs): update readme", "docs-only")
    _git(three_stage_repo, "push", "-q", "origin", "develop")

    assert promote("preprod", str(three_stage_repo), execute=True) == 0
    assert _remote_ref(three_stage_repo, "refs/heads/preprod") == sha
    assert "0.2.2" not in _git(three_stage_repo, "ls-remote", "--tags", "origin")


def test_gate_checks_refuse_off_branch_or_dirty(three_stage_repo: Path):
    _commit(three_stage_repo, "fix(core): a real change", "changed")
    _git(three_stage_repo, "push", "-q", "origin", "develop")
    (three_stage_repo / "file.txt").write_text("uncommitted")
    assert promote("preprod", str(three_stage_repo), execute=False) == 1
    _git(three_stage_repo, "checkout", "-q", "--", "file.txt")
    _git(three_stage_repo, "checkout", "-q", "main")
    assert promote("preprod", str(three_stage_repo), execute=False) == 1


def test_release_stage_takes_the_base_of_the_preprod_alpha(three_stage_repo: Path, monkeypatch):
    releases = []
    monkeypatch.setattr(git_ops, "gh", lambda args, repo_dir: releases.append(args) or "")
    _git(three_stage_repo, "checkout", "-q", "preprod")
    sha = _commit(three_stage_repo, "feat(core): a change on preprod", "changed")
    _git(three_stage_repo, "tag", "-a", "0.3.0a2", sha, "-m", "candidate")
    _git(three_stage_repo, "push", "-q", "origin", "preprod", "0.3.0a2")

    assert promote("main", str(three_stage_repo), execute=True) == 0
    assert _remote_ref(three_stage_repo, "refs/heads/main") == sha
    assert "refs/tags/0.3.0\n" in _git(three_stage_repo, "ls-remote", "--tags", "origin") + "\n"
    assert releases[0][:2] == ["release", "create"] and releases[0][2] == "0.3.0"


def test_docs_only_advance_after_a_release_does_not_retag(three_stage_repo: Path, monkeypatch):
    """Hit live in prosper: after 0.2.2 shipped, a doc-only preprod advance
    recomputed 0.2.2 from the old alpha and crashed on 'tag already exists'."""
    monkeypatch.setattr(git_ops, "gh", lambda args, repo_dir: "")
    _git(three_stage_repo, "checkout", "-q", "preprod")
    fix_sha = _commit(three_stage_repo, "fix(core): a change on preprod", "fix")
    _git(three_stage_repo, "tag", "-a", "0.2.2a1", fix_sha, "-m", "candidate")
    _git(three_stage_repo, "push", "-q", "origin", "preprod", "0.2.2a1")
    assert promote("main", str(three_stage_repo), execute=True) == 0

    docs_sha = _commit(three_stage_repo, "doc(docs): update readme", "docs-only")
    _git(three_stage_repo, "push", "-q", "origin", "preprod")
    assert promote("main", str(three_stage_repo), execute=True) == 0
    assert _remote_ref(three_stage_repo, "refs/heads/main") == docs_sha


# ── Single stage: main only, releases come from a PR ────────────────────────────


class FakeGitHub:
    """Stands in for `gh`: serves one PR and performs its squash-merge on the
    local bare remote, so the tag/release steps run against real git state."""

    def __init__(self, repo_dir: Path, head_sha: str, commits: list[str]):
        self.repo_dir = repo_dir
        self.releases: list[list[str]] = []
        self.merges = 0
        self.pr = {
            "state": "OPEN",
            "baseRefName": "main",
            "headRefName": "feature",
            "headRefOid": head_sha,
            "mergeCommit": None,
            "url": "https://example.test/pull/19",
            "commits": [
                {"messageHeadline": c.split("\n\n")[0], "messageBody": ""} for c in commits
            ],
        }

    def __call__(self, args: list[str], repo_dir: str) -> str:
        if args[:2] == ["pr", "view"]:
            return json.dumps(self.pr)
        if args[:2] == ["repo", "view"]:
            return json.dumps({"nameWithOwner": "owner/repo"})
        if args[:2] == ["pr", "merge"]:
            self.merges += 1
            tree = _git(self.repo_dir, "rev-parse", f"{self.pr['headRefOid']}^{{tree}}")
            main = _git(self.repo_dir, "rev-parse", "origin/main")
            squash = _git(self.repo_dir, "commit-tree", tree, "-p", main, "-m", "squash (#19)")
            _git(self.repo_dir, "push", "-q", "origin", f"{squash}:refs/heads/main")
            self.pr.update(state="MERGED", mergeCommit={"oid": squash})
            return ""
        if args[:2] == ["release", "create"]:
            self.releases.append(args)
            return ""
        raise AssertionError(f"unexpected gh call: {args}")


CHANGELOG_070 = "# Changelog\n\n## [Unreleased]\n\n## [0.7.0] - 2026-09-29\n\n### Added\n- git-promotion\n"


@pytest.fixture
def single_stage(tmp_path: Path, monkeypatch):
    repo_dir = _init_repo(
        tmp_path, {"stages": ["main"], "tag_prefix": "v", "changelog": "CHANGELOG.md"}
    )
    root = _commit(repo_dir, "feat(skill): first", "# Changelog\n", "CHANGELOG.md")
    _git(repo_dir, "tag", "-a", "v0.6.0", root, "-m", "release")
    _git(repo_dir, "branch", "-M", "main")
    _git(repo_dir, "push", "-q", "origin", "main", "v0.6.0")
    _git(repo_dir, "checkout", "-q", "-b", "feature")

    def open_pr(*messages: str, changelog: str = CHANGELOG_070) -> FakeGitHub:
        for i, message in enumerate(messages):
            _commit(repo_dir, message, str(i))
        head = _commit(repo_dir, "doc(docs): cut CHANGELOG", changelog, "CHANGELOG.md")
        _git(repo_dir, "push", "-q", "origin", f"{head}:refs/pull/19/head")
        fake = FakeGitHub(repo_dir, head, [*messages, "doc(docs): cut CHANGELOG"])
        monkeypatch.setattr(git_ops, "gh", fake)
        return fake

    return repo_dir, open_pr


def test_single_stage_requires_a_pr(single_stage):
    repo_dir, _ = single_stage
    assert promote("main", str(repo_dir), execute=False) == 2


def test_pr_dry_run_reports_the_version_and_does_not_merge(single_stage, capsys):
    repo_dir, open_pr = single_stage
    fake = open_pr("feat(skill): add git-promotion", "fix(skill): typo")
    assert promote("main", str(repo_dir), execute=False, pr=19) == 0
    assert "Version: v0.7.0" in capsys.readouterr().out
    assert fake.merges == 0


def test_pr_execute_merges_tags_and_releases_with_changelog_notes(single_stage):
    repo_dir, open_pr = single_stage
    fake = open_pr("feat(skill): add git-promotion")
    # a dirty tree is fine without a gate: nothing local is tested or touched
    (repo_dir / "wip.txt").write_text("unrelated")

    assert promote("main", str(repo_dir), execute=True, pr=19) == 0
    merge_sha = fake.pr["mergeCommit"]["oid"]
    assert _remote_ref(repo_dir, "refs/tags/v0.7.0^{}") == merge_sha
    notes = fake.releases[0][fake.releases[0].index("--notes") + 1]
    assert notes == "### Added\n- git-promotion"


def test_pr_execute_refuses_without_a_changelog_section(single_stage):
    repo_dir, open_pr = single_stage
    fake = open_pr("feat(skill): add git-promotion", changelog="# Changelog\n\n## [Unreleased]\n- x\n")
    assert promote("main", str(repo_dir), execute=True, pr=19) == 1
    assert fake.merges == 0


def test_pr_rerun_after_release_is_a_no_op(single_stage):
    repo_dir, open_pr = single_stage
    fake = open_pr("feat(skill): add git-promotion")
    assert promote("main", str(repo_dir), execute=True, pr=19) == 0
    assert promote("main", str(repo_dir), execute=True, pr=19) == 0
    assert fake.merges == 1 and len(fake.releases) == 1


def test_pr_merged_but_untagged_resumes_at_the_tag_step(single_stage):
    repo_dir, open_pr = single_stage
    fake = open_pr("fix(skill): typo", changelog=CHANGELOG_070.replace("0.7.0", "0.6.1"))
    fake(["pr", "merge"], str(repo_dir))  # merged by hand, never tagged

    assert promote("main", str(repo_dir), execute=True, pr=19) == 0
    assert _remote_ref(repo_dir, "refs/tags/v0.6.1^{}") == fake.pr["mergeCommit"]["oid"]


def test_pr_against_another_base_is_refused(single_stage):
    repo_dir, open_pr = single_stage
    fake = open_pr("feat(skill): add git-promotion")
    fake.pr["baseRefName"] = "develop"
    assert promote("main", str(repo_dir), execute=False, pr=19) == 1
