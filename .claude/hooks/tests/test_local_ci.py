"""bin/local-ci run: clean clone of one commit, push payload, one act call per listed job, fail closed."""
import json
import os
import signal
import stat
import subprocess
import time
from pathlib import Path

import pytest

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
    """A push run gets `--ref refs/heads/main` unless the test passes its own `--ref` (local-ci requires one)."""
    env = {**os.environ, **GIT_ENV, "LOCAL_CI_ACT": str(act or fake_act(tmp_path)),
           "LOCAL_CI_HOME": str(tmp_path / "home"), "LOCAL_CI_IMAGE_ID": "sha256:" + "ab" * 32, **(extra_env or {})}
    if "pull_request" not in args and "--ref" not in args:
        args = ("--ref", "refs/heads/main", *args)
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


def test_act_gets_an_empty_github_token(tmp_path):
    """Without a GITHUB_TOKEN secret act runs `gh auth token` and hands the user's token to the job."""
    repo, sha = make_repo(tmp_path)
    assert run(tmp_path, repo, sha, "--record-baseline").returncode == 0
    for c in (tmp_path / "act-calls").read_text().splitlines():
        assert f" {c} ".count(" -s GITHUB_TOKEN= ") == 1, c
        assert "--env UV_LINK_MODE=copy" in c, c


def test_log_dir_is_per_ref(tmp_path):
    repo, sha = make_repo(tmp_path)
    run(tmp_path, repo, sha, "--ref", "refs/heads/feat/x", "--record-baseline")
    run(tmp_path, repo, sha, "--ref", "refs/heads/main", "--record-baseline")
    state = tmp_path / "home" / "acme__widget"
    assert (state / f"{sha}-refs_heads_feat_x-push-full" / "ci__check.log").is_file()
    assert (state / f"{sha}-refs_heads_main-push-full" / "ci__check.log").is_file()


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
    assert json.loads((state / "baseline.json").read_text())["ci.yml/check@refs/heads/main"] == {"skipped": 2}


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
                             "ref": "refs/heads/main", "workflows": "ci.yml", "fast_jobs": "",
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


def test_quiet_pytest_summary_with_act_prefix_is_counted(tmp_path):
    repo, sha = make_repo(tmp_path)
    act = fake_act(tmp_path, body='printf "[ci/check]   | \\033[32m436 passed\\033[0m, 2 skipped, 1 warning in 7.23s (0:00:07)\\n"')
    assert run(tmp_path, repo, sha, "--record-baseline", act=act).returncode == 0
    rec = json.loads((tmp_path / "home" / "acme__widget" / "results.jsonl").read_text().splitlines()[-1])
    assert rec["jobs"]["ci.yml/check"]["counts"] == {"passed": 436, "skipped": 2}


def test_non_summary_lines_are_not_counted(tmp_path):
    repo, sha = make_repo(tmp_path)
    act = fake_act(tmp_path, body='echo "Downloaded 3 packages in 0.5s"; echo "ok 3 passed in review"; echo "see 3 passed in 0.5s"')
    assert run(tmp_path, repo, sha, "--record-baseline", act=act).returncode == 0
    rec = json.loads((tmp_path / "home" / "acme__widget" / "results.jsonl").read_text().splitlines()[-1])
    assert rec["jobs"]["ci.yml/check"]["counts"] == {}


def test_fast_jobs_matching_no_job_fails(tmp_path):
    repo, sha = make_repo(tmp_path)
    git(repo, "config", "local-ci.fast-jobs", "chekc")
    r = run(tmp_path, repo, sha, "--tier", "fast", "--record-baseline")
    assert r.returncode == 1
    assert "fast-jobs chekc matches no job" in r.stderr
    assert not (tmp_path / "act-calls").exists()


def fake_gh(tmp_path, head, base_sha, base_ref="main", fail_state=None):
    """A `gh` stub: answers pr view and branch lookups, logs every status POST. `fail_state` makes that POST fail."""
    p = tmp_path / "gh"
    p.write_text(f"""#!/usr/bin/env bash
echo "$*" >> "{tmp_path}/gh-calls"
case "$*" in
  "pr view"*) echo '{{"number":7,"headRefOid":"{head}","headRefName":"feat/x","baseRefName":"{base_ref}"}}';;
  *"/branches/{base_ref}"*) echo "{base_sha}";;
  *"/statuses/"*"state={fail_state}"*) echo "HTTP 502 boom" >&2; exit 1;;
  *"/statuses/"*) ;;
  *) echo "unexpected gh call: $*" >&2; exit 2;;
esac
""")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def pr_repo(tmp_path):
    repo, base = make_repo(tmp_path)
    git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "a.txt").write_text("a")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "feat")
    return repo, base, git(repo, "rev-parse", "HEAD")


def statuses(tmp_path):
    return [l for l in (tmp_path / "gh-calls").read_text().splitlines() if "/statuses/" in l]


def test_pr_run_tests_the_merge_commit_and_posts_pending_then_success(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    gh = fake_gh(tmp_path, head, base)
    act = fake_act(tmp_path, body='test -f a.txt && test -f .github/workflows/ci.yml && echo "== 1 passed in 1s =="')
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline", act=act,
            extra_env={"LOCAL_CI_GH": str(gh)})
    assert r.returncode == 0, r.stdout + r.stderr
    s = statuses(tmp_path)
    assert len(s) == 2 and "state=pending" in s[0] and "state=success" in s[1]
    assert all(f"repos/acme/widget/statuses/{head}" in x and "context=local-ci/pull_request" in x for x in s)
    assert f"description=full base={base} img=abababababab " in s[1]
    payload = json.loads((tmp_path / "payload.json").read_text())
    assert payload["pull_request"]["head"]["sha"] == head and payload["pull_request"]["base"]["sha"] == base


def test_pr_run_failure_posts_failure(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    gh = fake_gh(tmp_path, head, base)
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline",
            act=fake_act(tmp_path, body="exit 1"), extra_env={"LOCAL_CI_GH": str(gh)})
    assert r.returncode == 1
    assert "state=failure" in statuses(tmp_path)[-1]


@pytest.mark.parametrize("signum", [signal.SIGINT, signal.SIGHUP])
def test_pr_run_killed_posts_failure_not_pending(tmp_path, signum):
    repo, base, head = pr_repo(tmp_path)
    gh = fake_gh(tmp_path, head, base)
    env = {**os.environ, **GIT_ENV, "LOCAL_CI_ACT": str(fake_act(tmp_path, body="sleep 30")),
           "LOCAL_CI_HOME": str(tmp_path / "home"), "LOCAL_CI_IMAGE_ID": "sha256:" + "ab" * 32, "LOCAL_CI_GH": str(gh)}
    p = subprocess.Popen([str(LOCAL_CI), "run", "--repo", str(repo), "--event", "pull_request", "--pr", "7", head],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 20
    while not (tmp_path / "act-calls").exists() and time.time() < deadline:
        time.sleep(0.2)
    p.send_signal(signum)
    p.wait(timeout=30)
    assert p.returncode != 0
    assert "state=failure" in statuses(tmp_path)[-1]


def test_pr_merge_conflict_posts_failure(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    git(repo, "checkout", "-q", "main")
    (repo / "a.txt").write_text("conflict")
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "main change")
    new_base = git(repo, "rev-parse", "HEAD")
    gh = fake_gh(tmp_path, head, new_base)
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline",
            extra_env={"LOCAL_CI_GH": str(gh)})
    assert r.returncode == 1
    assert "merge conflict" in r.stdout
    assert "state=failure" in statuses(tmp_path)[-1]


def test_pr_missing_commit_after_fetch_posts_failure(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    gh = fake_gh(tmp_path, "c" * 40, base)  # head sha absent locally; origin is unreachable, so the fetch fails
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline",
            extra_env={"LOCAL_CI_GH": str(gh)})
    assert r.returncode == 1
    assert "missing" in r.stdout
    assert "state=failure" in statuses(tmp_path)[-1] and f"statuses/{'c' * 40}" in statuses(tmp_path)[-1]
    assert not (tmp_path / "act-calls").exists()


def test_sigterm_kills_act_and_exits_non_zero(tmp_path):
    repo, sha = make_repo(tmp_path)
    act = fake_act(tmp_path, body=f'echo $$ > "{tmp_path}/act-pid"; sleep 30')
    env = {**os.environ, **GIT_ENV, "LOCAL_CI_ACT": str(act), "LOCAL_CI_HOME": str(tmp_path / "home"),
           "LOCAL_CI_IMAGE_ID": "sha256:" + "ab" * 32}
    p = subprocess.Popen([str(LOCAL_CI), "run", "--repo", str(repo), "--ref", "refs/heads/main", "--record-baseline", sha],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 20
    while not (tmp_path / "act-pid").exists() and time.time() < deadline:
        time.sleep(0.2)
    pid = int((tmp_path / "act-pid").read_text())
    p.send_signal(signal.SIGTERM)
    p.wait(timeout=30)
    assert p.returncode != 0
    deadline = time.time() + 5
    while time.time() < deadline:
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return
        time.sleep(0.1)
    raise AssertionError(f"stub act {pid} still running")


def test_passed_pr_is_not_rerun_but_its_success_status_is_reposted(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    gh = fake_gh(tmp_path, head, base)
    env = {"LOCAL_CI_GH": str(gh)}
    args = ("--event", "pull_request", "--pr", "7")
    assert run(tmp_path, repo, head, *args, "--record-baseline", extra_env=env).returncode == 0
    acts, before = len((tmp_path / "act-calls").read_text().splitlines()), statuses(tmp_path)
    r = run(tmp_path, repo, head, *args, extra_env=env)
    assert r.returncode == 0 and "already passed" in r.stdout
    assert len((tmp_path / "act-calls").read_text().splitlines()) == acts
    after = statuses(tmp_path)
    assert len(after) == len(before) + 1 and "state=success" in after[-1]
    assert f"description=full base={base} img=abababababab " in after[-1]


def test_failed_final_post_fails_a_successful_run(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    gh = fake_gh(tmp_path, head, base, fail_state="success")
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline", extra_env={"LOCAL_CI_GH": str(gh)})
    assert r.returncode != 0
    assert "could not post success status: HTTP 502 boom" in r.stderr
    assert "state=pending" in statuses(tmp_path)[0]


def test_failed_final_post_keeps_a_failed_run_result(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    gh = fake_gh(tmp_path, head, base, fail_state="failure")
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline",
            act=fake_act(tmp_path, body="exit 1"), extra_env={"LOCAL_CI_GH": str(gh)})
    assert r.returncode == 1
    assert "could not post failure status" in r.stderr and "FAILED" in r.stdout


def base_env(tmp_path, act, **extra):
    return {**os.environ, **GIT_ENV, "LOCAL_CI_ACT": str(act), "LOCAL_CI_HOME": str(tmp_path / "home"),
            "LOCAL_CI_IMAGE_ID": "sha256:" + "ab" * 32, **extra}


def act_count(tmp_path):
    p = tmp_path / "act-calls"
    return len(p.read_text().splitlines()) if p.exists() else 0


def fake_docker(tmp_path, ps_delay=0):
    """A `docker` stub: logs every call; one act container `c1` and one act network `n1` exist.

    `ps_delay` seconds make `docker ps` slow, as a real cleanup is."""
    p = tmp_path / "docker"
    p.write_text(f"""#!/usr/bin/env bash
echo "$*" >> "{tmp_path}/docker-calls"
case "$*" in
  "ps -aq"*) sleep {ps_delay}; echo c1;;
  "network ls"*) echo n1;;
esac
""")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def test_signal_removes_act_containers_and_networks(tmp_path):
    repo, sha = make_repo(tmp_path)
    act = fake_act(tmp_path, body=f'echo $$ > "{tmp_path}/act-pid"; sleep 30')
    env = base_env(tmp_path, act, LOCAL_CI_DOCKER=str(fake_docker(tmp_path)))
    p = subprocess.Popen([str(LOCAL_CI), "run", "--repo", str(repo), "--ref", "refs/heads/main", "--record-baseline", sha],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 20
    while not (tmp_path / "act-pid").exists() and time.time() < deadline:
        time.sleep(0.2)
    p.send_signal(signal.SIGTERM)
    p.wait(timeout=30)
    assert p.returncode != 0
    calls = (tmp_path / "docker-calls").read_text().splitlines() if (tmp_path / "docker-calls").exists() else []
    assert "rm -f c1" in calls and "network rm n1" in calls, calls


def test_second_sigint_during_cleanup_still_posts_failure(tmp_path):
    # `timeout -s INT` or Ctrl-C: uv forwards SIGINT, so Python gets two ~0.2 s apart; the second lands in `finally`.
    repo, base, head = pr_repo(tmp_path)
    act = fake_act(tmp_path, body=f'echo $$ > "{tmp_path}/act-pid"; sleep 30')
    env = base_env(tmp_path, act, LOCAL_CI_GH=str(fake_gh(tmp_path, head, base)),
                   LOCAL_CI_DOCKER=str(fake_docker(tmp_path, ps_delay=1)))
    p = subprocess.Popen([str(LOCAL_CI), "run", "--repo", str(repo), "--event", "pull_request", "--pr", "7", head],
                         env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    deadline = time.time() + 20
    while not (tmp_path / "act-pid").exists() and time.time() < deadline:
        time.sleep(0.2)
    pid = int((tmp_path / "act-pid").read_text())
    p.send_signal(signal.SIGINT)
    time.sleep(0.2)
    p.send_signal(signal.SIGINT)
    p.wait(timeout=30)
    assert p.returncode != 0
    assert "state=failure" in statuses(tmp_path)[-1], statuses(tmp_path)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return
    raise AssertionError(f"stub act {pid} still running")


def test_pr_run_uses_the_merge_commits_submodule_commit(tmp_path):
    sub = tmp_path / "sub"
    git(tmp_path, "init", "-q", "-b", "main", str(sub))
    (sub / "f").write_text("1\n")
    git(sub, "add", ".")
    git(sub, "commit", "-q", "-m", "s1")
    repo, _ = make_repo(tmp_path)
    git(repo, "-c", "protocol.file.allow=always", "submodule", "add", "-q", str(sub), "vendor/sub")
    git(repo, "commit", "-q", "-m", "add sub")
    git(repo, "checkout", "-q", "-b", "feat/x")
    (repo / "a.txt").write_text("a")
    git(repo, "add", "a.txt")
    git(repo, "commit", "-q", "-m", "feat")
    head = git(repo, "rev-parse", "HEAD")
    git(repo, "checkout", "-q", "main")
    (sub / "f").write_text("2\n")
    git(sub, "commit", "-q", "-am", "s2")
    git(repo / "vendor" / "sub", "fetch", "-q", "origin", "main")
    git(repo / "vendor" / "sub", "checkout", "-q", "--detach", "FETCH_HEAD")
    git(repo, "add", "vendor/sub")
    git(repo, "commit", "-q", "-m", "bump sub")  # the base moves the submodule gitlink; the PR head does not
    base = git(repo, "rev-parse", "HEAD")
    act = fake_act(tmp_path, body='grep -qx 2 vendor/sub/f && test -f a.txt && echo "== 1 passed in 1s =="')
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline", act=act,
            extra_env={"LOCAL_CI_GH": str(fake_gh(tmp_path, head, base))})
    assert r.returncode == 0, r.stdout + r.stderr


def test_push_run_without_ref_fails(tmp_path):
    repo, sha = make_repo(tmp_path)
    r = subprocess.run([str(LOCAL_CI), "run", "--repo", str(repo), "--record-baseline", sha], capture_output=True,
                       text=True, env=base_env(tmp_path, fake_act(tmp_path)))
    assert r.returncode != 0
    assert "pass --ref refs/heads/<branch>" in r.stdout + r.stderr
    assert act_count(tmp_path) == 0


def test_success_on_another_ref_does_not_skip_the_run(tmp_path):
    repo, sha = make_repo(tmp_path)
    assert run(tmp_path, repo, sha, "--ref", "refs/heads/feat/x", "--record-baseline").returncode == 0
    n = act_count(tmp_path)
    run(tmp_path, repo, sha, "--ref", "refs/heads/main")
    assert act_count(tmp_path) > n


def test_changed_workflow_list_does_not_skip_the_run(tmp_path):
    repo, _ = make_repo(tmp_path)
    (repo / ".github" / "workflows" / "ci2.yml").write_text(WORKFLOW)
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "ci2")
    sha = git(repo, "rev-parse", "HEAD")
    assert run(tmp_path, repo, sha, "--record-baseline").returncode == 0
    n = act_count(tmp_path)
    git(repo, "config", "local-ci.workflows", "ci.yml ci2.yml")
    run(tmp_path, repo, sha)
    assert act_count(tmp_path) > n


def test_changed_fast_jobs_does_not_skip_a_fast_run(tmp_path):
    repo, sha = make_repo(tmp_path)
    git(repo, "config", "local-ci.fast-jobs", "check")
    assert run(tmp_path, repo, sha, "--tier", "fast", "--record-baseline").returncode == 0
    n = act_count(tmp_path)
    git(repo, "config", "local-ci.fast-jobs", "frontend")
    run(tmp_path, repo, sha, "--tier", "fast")
    assert act_count(tmp_path) > n


def test_pr_run_records_its_merge_ref_and_pull_request_baseline(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline",
            extra_env={"LOCAL_CI_GH": str(fake_gh(tmp_path, head, base))})
    assert r.returncode == 0, r.stdout + r.stderr
    state = tmp_path / "home" / "acme__widget"
    rec = json.loads((state / "results.jsonl").read_text().splitlines()[-1])
    assert rec["ref"] == "refs/pull/7/merge" and rec["workflows"] == "ci.yml"
    assert "ci.yml/check@pull_request" in json.loads((state / "baseline.json").read_text())


def test_baseline_is_per_ref(tmp_path):
    repo, sha = make_repo(tmp_path)
    act = fake_act(tmp_path, body='echo "== 5 passed, 1 skipped in 1s =="')
    assert run(tmp_path, repo, sha, "--ref", "refs/heads/feat/x", "--record-baseline", act=act).returncode == 0
    r = run(tmp_path, repo, sha, "--ref", "refs/heads/main", act=act)
    assert r.returncode == 1
    assert "no skip baseline for ci.yml/check@refs/heads/main" in r.stdout


def test_exact_baseline_wins_and_job_baseline_is_the_fallback(tmp_path):
    repo, sha = make_repo(tmp_path)
    state = tmp_path / "home" / "acme__widget"
    state.mkdir(parents=True)
    (state / "baseline.json").write_text(json.dumps({"ci.yml/check": {"skipped": 1}, "ci.yml/frontend": {"skipped": 1},
                                                     "ci.yml/check@refs/heads/main": {"skipped": 3}}))
    r = run(tmp_path, repo, sha, act=fake_act(tmp_path, body='echo "== 5 passed, 3 skipped in 1s =="'))
    assert "ci.yml/check: ok" in r.stdout, r.stdout
    assert "ci.yml/frontend: skipped 3 > baseline 1" in r.stdout


def skips(tmp_path, n):
    return fake_act(tmp_path, body=f'echo "== 5 passed, {n} skipped in 1s =="')


def baselines(tmp_path):
    return json.loads((tmp_path / "home" / "acme__widget" / "baseline.json").read_text())


def test_recording_on_a_feature_branch_also_writes_the_branch_class_key(tmp_path):
    repo, sha = make_repo(tmp_path)
    assert run(tmp_path, repo, sha, "--ref", "refs/heads/feat/a", "--record-baseline", act=skips(tmp_path, 1)).returncode == 0
    b = baselines(tmp_path)
    assert b["ci.yml/check@refs/heads/feat/a"] == {"skipped": 1} and b["ci.yml/check@branch"] == {"skipped": 1}


def test_a_new_feature_branch_uses_the_branch_class_baseline(tmp_path):
    repo, sha = make_repo(tmp_path)
    run(tmp_path, repo, sha, "--ref", "refs/heads/feat/a", "--record-baseline", act=skips(tmp_path, 1))
    r = run(tmp_path, repo, sha, "--ref", "refs/heads/feat/b", act=skips(tmp_path, 1))
    assert r.returncode == 0, r.stdout
    assert "ci.yml/check: ok" in r.stdout


def test_skips_above_the_branch_class_baseline_fail(tmp_path):
    repo, sha = make_repo(tmp_path)
    run(tmp_path, repo, sha, "--ref", "refs/heads/feat/a", "--record-baseline", act=skips(tmp_path, 1))
    r = run(tmp_path, repo, sha, "--ref", "refs/heads/feat/b", act=skips(tmp_path, 2))
    assert r.returncode == 1
    assert "skipped 2 > baseline 1" in r.stdout


def test_exact_ref_baseline_wins_over_the_branch_class(tmp_path):
    repo, sha = make_repo(tmp_path)
    state = tmp_path / "home" / "acme__widget"
    state.mkdir(parents=True)
    (state / "baseline.json").write_text(json.dumps({"ci.yml/check@branch": {"skipped": 1},
                                                     "ci.yml/check@refs/heads/feat/b": {"skipped": 3}}))
    r = run(tmp_path, repo, sha, "--ref", "refs/heads/feat/b", act=skips(tmp_path, 3))
    assert "ci.yml/check: ok" in r.stdout, r.stdout


def test_a_deploy_branch_never_uses_the_branch_class_baseline(tmp_path):
    repo, sha = make_repo(tmp_path)
    run(tmp_path, repo, sha, "--ref", "refs/heads/feat/a", "--record-baseline", act=skips(tmp_path, 1))
    r = run(tmp_path, repo, sha, "--ref", "refs/heads/main", act=skips(tmp_path, 1))
    assert r.returncode == 1
    assert "no skip baseline for ci.yml/check@refs/heads/main" in r.stdout


def test_recording_on_a_deploy_branch_writes_no_branch_class_key(tmp_path):
    repo, sha = make_repo(tmp_path)
    git(repo, "config", "local-ci.deploy-branches", "main release")
    for ref in ("refs/heads/main", "refs/heads/release"):
        assert run(tmp_path, repo, sha, "--ref", ref, "--record-baseline", act=skips(tmp_path, 1)).returncode == 0
    assert "ci.yml/check@branch" not in baselines(tmp_path)


def test_a_pull_request_run_never_uses_the_branch_class_baseline(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    run(tmp_path, repo, head, "--ref", "refs/heads/feat/a", "--record-baseline", act=skips(tmp_path, 1))
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", act=skips(tmp_path, 1),
            extra_env={"LOCAL_CI_GH": str(fake_gh(tmp_path, head, base))})
    assert r.returncode == 1
    assert "no skip baseline for ci.yml/check@pull_request" in r.stdout


def test_recording_a_pull_request_run_writes_no_branch_class_key(tmp_path):
    repo, base, head = pr_repo(tmp_path)
    r = run(tmp_path, repo, head, "--event", "pull_request", "--pr", "7", "--record-baseline",
            extra_env={"LOCAL_CI_GH": str(fake_gh(tmp_path, head, base))})
    assert r.returncode == 0, r.stdout + r.stderr
    assert "ci.yml/check@branch" not in baselines(tmp_path)


def test_git_dir_from_the_environment_is_ignored(tmp_path):
    repo, first = make_repo(tmp_path)
    git(repo, "commit", "-q", "--allow-empty", "-m", "second")
    index = (repo / ".git" / "index").read_bytes()
    # `git --git-dir=<repo>/.git push` runs the pre-push hook with GIT_DIR set.
    r = run(tmp_path, repo, first, "--record-baseline", extra_env={"GIT_DIR": str(repo / ".git")})
    assert git(repo, "symbolic-ref", "-q", "HEAD") == "refs/heads/main"
    assert (repo / ".git" / "index").read_bytes() == index
    assert r.returncode == 0, r.stdout + r.stderr


def test_empty_job_list_fails(tmp_path):
    repo, sha = make_repo(tmp_path, workflow="name: ci\non: [push]\njobs: {}\n")
    r = run(tmp_path, repo, sha, "--record-baseline")
    assert r.returncode == 1
    assert "no job to run" in r.stderr
    assert act_count(tmp_path) == 0
