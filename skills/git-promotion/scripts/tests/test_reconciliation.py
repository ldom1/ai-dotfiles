import os
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import reconciliation


def test_carries_reconciliation_footer_true():
    message = "fix(core): patch the leak\n\nEmergency-Reconciliation: prod data leak, 2026-09-08"
    assert reconciliation.carries_reconciliation_footer(message) is True


def test_carries_reconciliation_footer_false_for_an_ordinary_commit():
    assert (
        reconciliation.carries_reconciliation_footer("fix(core): patch the leak")
        is False
    )


def _git(repo_dir: Path, *args: str, env: dict[str, str] | None = None) -> str:
    full_env = os.environ.copy()
    if env:
        full_env.update(env)
    result = subprocess.run(
        ["git", *args],
        cwd=repo_dir,
        capture_output=True,
        text=True,
        check=True,
        env=full_env,
    )
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


def test_patch_id_matches_for_a_cherry_picked_commit(repo: Path):
    """The whole point of patch-id over SHA: a cherry-pick produces a different SHA
    but the same patch-id when the content is identical."""
    (repo / "file.txt").write_text("two\n")
    _git(
        repo,
        "commit",
        "-q",
        "-am",
        "fix(core): second commit",
        env={
            "GIT_AUTHOR_DATE": "2000-01-01 00:00:00",
            "GIT_COMMITTER_DATE": "2000-01-01 00:00:00",
        },
    )
    original_sha = _git(repo, "rev-parse", "HEAD")

    _git(repo, "checkout", "-q", "-b", "other", "HEAD~1")
    _git(
        repo,
        "cherry-pick",
        original_sha,
        env={
            "GIT_AUTHOR_DATE": "2000-01-01 00:00:01",
            "GIT_COMMITTER_DATE": "2000-01-01 00:00:01",
        },
    )
    cherry_picked_sha = _git(repo, "rev-parse", "HEAD")

    assert original_sha != cherry_picked_sha
    assert reconciliation.patch_id(original_sha, str(repo)) == reconciliation.patch_id(
        cherry_picked_sha, str(repo)
    )


def test_is_authorized_divergence_true_when_footer_and_patch_id_both_match(repo: Path):
    (repo / "file.txt").write_text("two\n")
    _git(
        repo,
        "commit",
        "-q",
        "-am",
        "fix(core): hotfix\n\nEmergency-Reconciliation: prod incident",
        env={
            "GIT_AUTHOR_DATE": "2000-01-01 00:00:00",
            "GIT_COMMITTER_DATE": "2000-01-01 00:00:00",
        },
    )
    hotfix_sha = _git(repo, "rev-parse", "HEAD")

    _git(repo, "checkout", "-q", "-b", "other", "HEAD~1")
    _git(
        repo,
        "cherry-pick",
        hotfix_sha,
        env={
            "GIT_AUTHOR_DATE": "2000-01-01 00:00:01",
            "GIT_COMMITTER_DATE": "2000-01-01 00:00:01",
        },
    )
    cherry_picked_sha = _git(repo, "rev-parse", "HEAD")

    assert (
        reconciliation.is_authorized_divergence(
            [hotfix_sha], [cherry_picked_sha], str(repo)
        )
        is True
    )


def test_is_authorized_divergence_false_without_the_footer(repo: Path):
    (repo / "file.txt").write_text("two\n")
    _git(repo, "commit", "-q", "-am", "fix(core): a normal commit, not an emergency")
    plain_sha = _git(repo, "rev-parse", "HEAD")
    assert (
        reconciliation.is_authorized_divergence([plain_sha], [plain_sha], str(repo))
        is False
    )


def test_is_authorized_divergence_false_when_content_is_not_found_on_develop(
    repo: Path,
):
    (repo / "file.txt").write_text("two\n")
    _git(
        repo,
        "commit",
        "-q",
        "-am",
        "fix(core): hotfix\n\nEmergency-Reconciliation: prod incident",
    )
    hotfix_sha = _git(repo, "rev-parse", "HEAD")
    # candidate_shas is empty -- nothing on develop matches this commit's content
    assert reconciliation.is_authorized_divergence([hotfix_sha], [], str(repo)) is False
