"""local-ci pre-push: tier by branch, edge refs, chained existing hook, opt-in."""
import os
import stat
import subprocess
from pathlib import Path

from test_local_ci import GIT_ENV, LOCAL_CI, fake_act, git, make_repo

ZERO = "0" * 40


def hook_env(tmp_path):
    return {**os.environ, **GIT_ENV, "LOCAL_CI_ACT": str(fake_act(tmp_path)), "LOCAL_CI_HOME": str(tmp_path / "home"),
            "LOCAL_CI_IMAGE_ID": "sha256:" + "ab" * 32}


def pre_push(tmp_path, repo, lines):
    return subprocess.run([str(LOCAL_CI), "pre-push", "origin", "https://github.com/acme/widget.git"], cwd=repo,
                          input="".join(l + "\n" for l in lines), capture_output=True, text=True, env=hook_env(tmp_path))


def tiers(tmp_path):
    p = tmp_path / "act-calls"
    return p.read_text().splitlines() if p.exists() else []


def installed(tmp_path):
    repo, sha = make_repo(tmp_path)
    subprocess.run([str(LOCAL_CI), "install", "--repo", str(repo), "--workflows", "ci.yml", "--fast-jobs", "check"],
                   check=True, env=hook_env(tmp_path))
    for branch in ("main", "feat/x", "feat/new"):  # the skip baseline is per ref
        subprocess.run([str(LOCAL_CI), "run", "--repo", str(repo), "--ref", f"refs/heads/{branch}", "--record-baseline",
                        sha], check=True, env=hook_env(tmp_path), capture_output=True)
    (tmp_path / "act-calls").unlink()
    return repo, sha


def test_not_opted_in_does_nothing(tmp_path):
    repo, sha = make_repo(tmp_path)
    r = pre_push(tmp_path, repo, [f"refs/heads/feat/x {sha} refs/heads/feat/x {ZERO}"])
    assert r.returncode == 0 and tiers(tmp_path) == []


def test_deploy_branch_gets_full_tier(tmp_path):
    repo, _ = installed(tmp_path)
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")
    sha = git(repo, "rev-parse", "HEAD")
    r = pre_push(tmp_path, repo, [f"refs/heads/main {sha} refs/heads/main {ZERO}"])
    assert r.returncode == 0, r.stdout + r.stderr
    assert len(tiers(tmp_path)) == 2  # both jobs: full tier


def test_feature_branch_gets_fast_tier(tmp_path):
    repo, _ = installed(tmp_path)
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")
    sha = git(repo, "rev-parse", "HEAD")
    r = pre_push(tmp_path, repo, [f"refs/heads/feat/x {sha} refs/heads/feat/x {ZERO}"])
    assert r.returncode == 0
    assert len(tiers(tmp_path)) == 1 and "partial — not a merge gate" in r.stdout


def test_pre_push_skips_delete_and_tag(tmp_path):
    repo, sha = installed(tmp_path)
    r = pre_push(tmp_path, repo, [f"(delete) {ZERO} refs/heads/old {sha}", f"refs/tags/v1 {sha} refs/tags/v1 {ZERO}"])
    assert r.returncode == 0 and tiers(tmp_path) == []


def test_pre_push_new_branch(tmp_path):
    repo, _ = installed(tmp_path)
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")
    sha = git(repo, "rev-parse", "HEAD")
    assert pre_push(tmp_path, repo, [f"refs/heads/feat/new {sha} refs/heads/feat/new {ZERO}"]).returncode == 0
    assert '"before": "' + ZERO in (tmp_path / "payload.json").read_text()


def test_failure_blocks_push(tmp_path):
    repo, _ = installed(tmp_path)
    git(repo, "commit", "-q", "--allow-empty", "-m", "x")
    sha = git(repo, "rev-parse", "HEAD")
    env = {**hook_env(tmp_path), "LOCAL_CI_ACT": str(fake_act(tmp_path, body="exit 1"))}
    r = subprocess.run([str(LOCAL_CI), "pre-push", "origin", "u"], cwd=repo, env=env, capture_output=True, text=True,
                       input=f"refs/heads/main {sha} refs/heads/main {ZERO}\n")
    assert r.returncode == 1


def test_install_chains_existing_hook(tmp_path):
    repo, _ = make_repo(tmp_path)
    hook = repo / ".git" / "hooks" / "pre-push"
    hook.write_text(f"#!/usr/bin/env bash\ncat > {tmp_path}/old-hook-stdin\n")
    hook.chmod(hook.stat().st_mode | stat.S_IEXEC)
    subprocess.run([str(LOCAL_CI), "install", "--repo", str(repo), "--workflows", "ci.yml"], check=True,
                   env=hook_env(tmp_path))
    assert (repo / ".git" / "hooks" / "pre-push.local").exists()
    assert "local-ci pre-push" in hook.read_text()
    git(repo, "config", "local-ci.enabled", "false")  # chain check only, no run
    subprocess.run([str(hook), "origin", "u"], input="refs/heads/x a refs/heads/x b\n", text=True, check=True,
                   cwd=repo, env=hook_env(tmp_path))
    assert (tmp_path / "old-hook-stdin").read_text() == "refs/heads/x a refs/heads/x b\n"
