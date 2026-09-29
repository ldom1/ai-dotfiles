import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import git_ops


def _git(repo_dir: Path, *args: str) -> str:
    result = subprocess.run(["git", *args], cwd=repo_dir, capture_output=True, text=True, check=True)
    return result.stdout.strip()


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-q")
    _git(repo_dir, "config", "user.email", "test@example.com")
    _git(repo_dir, "config", "user.name", "Test")
    (repo_dir / "file.txt").write_text("one\n")
    _git(repo_dir, "add", "file.txt")
    _git(repo_dir, "commit", "-q", "-m", "fix(core): first commit")
    return repo_dir


def test_is_ancestor_true_for_the_same_commit(repo: Path):
    head = git_ops.rev_parse("HEAD", str(repo))
    assert git_ops.is_ancestor(head, head, str(repo)) is True


def test_is_ancestor_false_for_unrelated_history(repo: Path):
    head = git_ops.rev_parse("HEAD", str(repo))
    _git(repo, "checkout", "-q", "--orphan", "unrelated")
    _git(repo, "commit", "-q", "--allow-empty", "-m", "fix(core): unrelated root")
    unrelated_head = git_ops.rev_parse("HEAD", str(repo))
    assert git_ops.is_ancestor(unrelated_head, head, str(repo)) is False


def test_is_clean_tree(repo: Path):
    assert git_ops.is_clean_tree(str(repo)) is True
    (repo / "file.txt").write_text("dirty\n")
    assert git_ops.is_clean_tree(str(repo)) is False


def test_commit_messages_between_keeps_bodies_and_strips_leading_newlines(repo: Path):
    """Regression: git log leaves a leading "\\n" on every entry but the first,
    which hid every fix/feat after the first commit of a multi-commit range."""
    base = git_ops.rev_parse("HEAD", str(repo))
    (repo / "file.txt").write_text("two\n")
    _git(repo, "commit", "-q", "-am", "fix(core): second\n\nBREAKING CHANGE: detail")
    (repo / "file.txt").write_text("three\n")
    _git(repo, "commit", "-q", "-am", "doc(docs): third")
    head = git_ops.rev_parse("HEAD", str(repo))
    messages = git_ops.commit_messages_between(base, head, str(repo))
    assert sorted(m.splitlines()[0] for m in messages) == ["doc(docs): third", "fix(core): second"]
    assert any("BREAKING CHANGE: detail" in m for m in messages)


def test_commit_messages_between_without_base_is_the_whole_history(repo: Path):
    head = git_ops.rev_parse("HEAD", str(repo))
    assert git_ops.commit_messages_between(None, head, str(repo)) == ["fix(core): first commit"]


def test_show_file_returns_none_for_a_missing_path(repo: Path):
    assert git_ops.show_file("HEAD", "file.txt", str(repo)) == "one"
    assert git_ops.show_file("HEAD", "missing.md", str(repo)) is None


@pytest.fixture
def repo_with_remote(tmp_path: Path) -> tuple[Path, Path]:
    remote_dir = tmp_path / "remote.git"
    remote_dir.mkdir()
    subprocess.run(["git", "init", "-q", "--bare"], cwd=remote_dir, check=True)
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()
    _git(repo_dir, "init", "-q")
    _git(repo_dir, "config", "user.email", "test@example.com")
    _git(repo_dir, "config", "user.name", "Test")
    _git(repo_dir, "remote", "add", "origin", str(remote_dir))
    (repo_dir / "file.txt").write_text("one\n")
    _git(repo_dir, "add", "file.txt")
    _git(repo_dir, "commit", "-q", "-m", "fix(core): first commit")
    _git(repo_dir, "push", "-q", "origin", "HEAD:refs/heads/main")
    return repo_dir, remote_dir


def test_create_tag_is_annotated_and_push_tag_lands(repo_with_remote):
    repo_dir, remote_dir = repo_with_remote
    head = git_ops.rev_parse("HEAD", str(repo_dir))
    git_ops.create_tag("v0.2.1", head, "msg", str(repo_dir))
    assert _git(repo_dir, "cat-file", "-t", "v0.2.1") == "tag"
    assert git_ops.tags_pointing_at(head, str(repo_dir)) == ["v0.2.1"]
    git_ops.push_tag("v0.2.1", str(repo_dir))
    assert _git(remote_dir, "tag").splitlines() == ["v0.2.1"]


def test_push_atomic_moves_the_branch_and_the_tag_together(repo_with_remote):
    repo_dir, remote_dir = repo_with_remote
    (repo_dir / "file.txt").write_text("two\n")
    _git(repo_dir, "commit", "-q", "-am", "fix(core): second commit")
    head = git_ops.rev_parse("HEAD", str(repo_dir))
    git_ops.create_tag("0.2.2", head, "promote", str(repo_dir))
    git_ops.push_atomic("0.2.2", head, "preprod", str(repo_dir))
    assert _git(remote_dir, "rev-parse", "refs/heads/preprod") == head
    assert "0.2.2" in _git(remote_dir, "tag").splitlines()


def test_push_branch_only_does_not_create_a_tag(repo_with_remote):
    repo_dir, remote_dir = repo_with_remote
    head = git_ops.rev_parse("HEAD", str(repo_dir))
    git_ops.push_branch_only(head, "preprod", str(repo_dir))
    assert _git(remote_dir, "rev-parse", "refs/heads/preprod") == head
    assert _git(remote_dir, "tag") == ""
