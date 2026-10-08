"""bin/local-ci run: clean clone of one commit, push payload, one act call per listed job, fail closed."""
import json
import os
import stat
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
LOCAL_CI = REPO / "bin" / "local-ci"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t",
           "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_NOSYSTEM": "1"}
WORKFLOW = """name: ci
on: [push, pull_request]
jobs:
  check:
    runs-on: ubuntu-latest
    timeout-minutes: 1
    steps: [{run: "true"}]
  frontend:
    runs-on: ubuntu-latest
    steps: [{run: "true"}]
"""


def git(cwd, *args):
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True,
                          env={**os.environ, **GIT_ENV}).stdout.strip()


def make_repo(tmp_path, workflow=WORKFLOW):
    r = tmp_path / "src"
    (r / ".github" / "workflows").mkdir(parents=True)
    (r / ".github" / "workflows" / "ci.yml").write_text(workflow)
    (r / ".gitignore").write_text(".venv/\n")
    git(r.parent, "init", "-q", "-b", "main", str(r))
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "init")
    git(r, "remote", "add", "origin", "https://github.com/acme/widget.git")
    git(r, "config", "local-ci.workflows", "ci.yml")
    return r, git(r, "rev-parse", "HEAD")


def fake_act(tmp_path, body='echo "== 3 passed in 0.1s =="'):
    """An `act` stub: records argv, the cwd listing and the payload, then runs `body`."""
    p = tmp_path / "act"
    p.write_text(f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{tmp_path}/act-calls"
ls -A > "{tmp_path}/act-cwd-$$"
for ((i=1;i<=$#;i++)); do [[ "${{!i}}" == -e ]] && {{ j=$((i+1)); cp "${{!j}}" "{tmp_path}/payload.json"; }}; done
{body}
""")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def run(tmp_path, repo, sha, *args, act=None, extra_env=None):
    env = {**os.environ, **GIT_ENV, "LOCAL_CI_ACT": str(act or fake_act(tmp_path)),
           "LOCAL_CI_HOME": str(tmp_path / "home"), "LOCAL_CI_IMAGE_ID": "sha256:" + "ab" * 32, **(extra_env or {})}
    return subprocess.run([str(LOCAL_CI), "run", "--repo", str(repo), *args, sha], capture_output=True, text=True, env=env)


def test_one_act_call_per_listed_job_with_fixed_flags(tmp_path):
    repo, sha = make_repo(tmp_path)
    r = run(tmp_path, repo, sha, "--tier", "full", "--record-baseline")
    assert r.returncode == 0, r.stdout + r.stderr
    calls = (tmp_path / "act-calls").read_text().splitlines()
    assert len(calls) == 2
    for c in calls:
        assert c.startswith("push -W .github/workflows/ci.yml -j ")
        for flag in ("-P ubuntu-latest=local-ci-runner:24.04", "-P ubuntu-24.04=local-ci-runner:24.04", "--pull=false",
                     "--env ImageOS=ubuntu24", "--container-daemon-socket -"):
            assert flag in c, (flag, c)
        assert "--reuse" not in c


def test_clone_excludes_untracked_and_ignored(tmp_path):
    repo, sha = make_repo(tmp_path)
    (repo / ".env").write_text("SECRET=1\n")
    (repo / ".venv").mkdir()
    run(tmp_path, repo, sha, "--record-baseline")
    listing = next(tmp_path.glob("act-cwd-*")).read_text().split()
    assert ".env" not in listing and ".venv" not in listing and ".github" in listing


def test_clone_has_submodule_offline(tmp_path):
    sub = tmp_path / "sub"
    git(tmp_path, "init", "-q", "-b", "main", str(sub))
    (sub / "f").write_text("x")
    git(sub, "add", ".")
    git(sub, "commit", "-q", "-m", "s")
    repo, _ = make_repo(tmp_path)
    git(repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(sub), "vendor/sub")
    git(repo, "commit", "-q", "-m", "add sub")
    # The recorded URL is unreachable: the clone must use the source repo's module objects.
    git(repo, "config", "-f", ".gitmodules", "submodule.vendor/sub.url", "https://example.invalid/sub.git")
    git(repo, "commit", "-q", "-am", "unreachable url")
    sha = git(repo, "rev-parse", "HEAD")
    act = fake_act(tmp_path, body='test -f vendor/sub/f && echo "== 1 passed in 0.1s =="')
    r = run(tmp_path, repo, sha, "--record-baseline", act=act)
    assert r.returncode == 0, r.stdout + r.stderr


def test_push_payload_ref(tmp_path):
    repo, sha = make_repo(tmp_path)
    run(tmp_path, repo, sha, "--ref", "refs/heads/feat/x", "--before", "0" * 40, "--record-baseline")
    payload = json.loads((tmp_path / "payload.json").read_text())
    assert payload["ref"] == "refs/heads/feat/x"
    assert payload["after"] == sha and payload["before"] == "0" * 40


def test_missing_act_fails_closed(tmp_path):
    repo, sha = make_repo(tmp_path)
    r = run(tmp_path, repo, sha, act=tmp_path / "no-such-act")
    assert r.returncode == 1
    assert "act not found" in r.stderr


def test_job_timeout_kills_act_and_fails(tmp_path):
    workflow = WORKFLOW.replace("timeout-minutes: 1", "timeout-minutes: 0.02")  # 1.2 s
    repo, sha = make_repo(tmp_path, workflow)
    r = run(tmp_path, repo, sha, "--record-baseline", act=fake_act(tmp_path, body="sleep 30"))
    assert r.returncode == 1
    assert "timed out" in r.stdout


def test_pytest_summary_counts_are_parsed_and_recorded(tmp_path):
    repo, sha = make_repo(tmp_path)
    act = fake_act(tmp_path, body='echo "[ci/check] | ===== 436 passed, 2 skipped, 3 warnings in 7.23s ====="')
    r = run(tmp_path, repo, sha, "--record-baseline", act=act)
    assert r.returncode == 0, r.stdout + r.stderr
    state = tmp_path / "home" / "acme__widget"
    rec = json.loads((state / "results.jsonl").read_text().splitlines()[-1])
    assert rec["sha"] == sha and rec["result"] == "success" and rec["event"] == "push" and rec["tier"] == "full"
    assert rec["jobs"]["ci.yml/check"]["counts"] == {"passed": 436, "skipped": 2}
    assert json.loads((state / "baseline.json").read_text())["ci.yml/check"] == {"skipped": 2}


def test_more_skips_than_baseline_fails(tmp_path):
    repo, sha = make_repo(tmp_path)
    run(tmp_path, repo, sha, "--record-baseline", act=fake_act(tmp_path, body='echo "== 5 passed, 1 skipped in 1s =="'))
    git(repo, "commit", "-q", "--allow-empty", "-m", "next")
    sha2 = git(repo, "rev-parse", "HEAD")
    r = run(tmp_path, repo, sha2, act=fake_act(tmp_path, body='echo "== 4 passed, 2 skipped in 1s =="'))
    assert r.returncode == 1
    assert "skipped 2 > baseline 1" in r.stdout


def test_missing_baseline_fails_closed(tmp_path):
    repo, sha = make_repo(tmp_path)
    r = run(tmp_path, repo, sha, act=fake_act(tmp_path, body='echo "== 5 passed in 1s =="'))
    assert r.returncode == 1
    assert "no skip baseline" in r.stdout


def test_passed_commit_is_not_rerun_but_a_later_failure_wins(tmp_path):
    repo, sha = make_repo(tmp_path)
    assert run(tmp_path, repo, sha, "--record-baseline").returncode == 0
    calls = len((tmp_path / "act-calls").read_text().splitlines())
    assert run(tmp_path, repo, sha).returncode == 0
    assert len((tmp_path / "act-calls").read_text().splitlines()) == calls  # skipped: same sha, event, tier, img
    state = tmp_path / "home" / "acme__widget"
    with open(state / "results.jsonl", "a") as fh:
        fh.write(json.dumps({"sha": sha, "event": "push", "tier": "full", "base": "", "img": "abababababab",
                             "result": "failure", "duration": "1s", "jobs": {}, "ts": 0}) + "\n")
    run(tmp_path, repo, sha)
    assert len((tmp_path / "act-calls").read_text().splitlines()) > calls  # newest record is a failure: re-run


def test_fast_tier_runs_only_fast_jobs_and_says_partial(tmp_path):
    repo, sha = make_repo(tmp_path)
    git(repo, "config", "local-ci.fast-jobs", "check")
    r = run(tmp_path, repo, sha, "--tier", "fast", "--record-baseline")
    assert r.returncode == 0
    assert [c.split(" -j ")[1].split()[0] for c in (tmp_path / "act-calls").read_text().splitlines()] == ["check"]
    assert "partial — not a merge gate" in r.stdout
