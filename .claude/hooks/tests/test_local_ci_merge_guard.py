"""local-ci-merge-guard.py: deny `gh pr merge` unless a fresh local-ci/pull_request success is on the PR head."""
import json
import os
import stat
import subprocess
from pathlib import Path

from test_local_ci import GIT_ENV, git, make_repo

HOOK = Path(__file__).resolve().parents[1] / "local-ci-merge-guard.py"
H, B = "a" * 40, "b" * 40
IMG = "sha256:" + "ab" * 32


def status(state="success", desc=f"full base={B} img=abababababab 42s", context="local-ci/pull_request", login="ldom1"):
    return {"state": state, "context": context, "description": desc, "creator": {"login": login}}


def fake_gh(tmp_path, statuses, total=None, head=H, base_tip=B):
    p = tmp_path / "gh"
    combined = {"sha": head, "total_count": len(statuses) if total is None else total, "statuses": statuses}
    (tmp_path / "combined.json").write_text(json.dumps(combined))
    p.write_text(f"""#!/usr/bin/env bash
case "$*" in
  "pr view"*) echo '{{"number":7,"headRefOid":"{head}","baseRefName":"main"}}';;
  *"/branches/main"*) echo "{base_tip}";;
  *"/status"*) cat "{tmp_path}/combined.json";;
  "api user"*) echo ldom1;;
  *) exit 2;;
esac
""")
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def guard(tmp_path, command, gh, guard_on=True):
    repo, _ = make_repo(tmp_path)
    git(repo, "config", "local-ci.guard", "true" if guard_on else "false")
    r = subprocess.run([str(HOOK)], input=json.dumps({"tool_name": "Bash", "tool_input": {"command": command},
                                                       "cwd": str(repo)}),
                       capture_output=True, text=True,
                       env={**os.environ, **GIT_ENV, "LOCAL_CI_GH": str(gh), "LOCAL_CI_IMAGE_ID": IMG})
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)["hookSpecificOutput"]["permissionDecisionReason"] if r.stdout.strip() else None


def test_fresh_success_allows(tmp_path):
    assert guard(tmp_path, "gh pr merge 7 --squash --delete-branch", fake_gh(tmp_path, [status()])) is None


def test_guard_off_allows_anything(tmp_path):
    assert guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, []), guard_on=False) is None


def test_other_commands_are_ignored(tmp_path):
    assert guard(tmp_path, "gh pr view 7 && git status", fake_gh(tmp_path, [])) is None


def test_no_status_denies(tmp_path):
    assert "no local-ci/pull_request status" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, []))


def test_failure_after_success_denies(tmp_path):
    # The combined status keeps the latest per context: a later failure is what it returns.
    assert "state is failure" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status("failure")]))


def test_pending_denies(tmp_path):
    assert "state is pending" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status("pending")]))


def test_moved_base_denies(tmp_path):
    reason = guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status()], base_tip="c" * 40))
    assert "stale: re-run local-ci" in reason


def test_rebuilt_image_denies(tmp_path):
    reason = guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status(desc=f"full base={B} img=cdcdcdcdcdcd 42s")]))
    assert "image changed" in reason


def test_incomplete_response_denies(tmp_path):
    assert "incomplete" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status()], total=150))


def test_bad_description_denies(tmp_path):
    assert "description" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status(desc="passed locally")]))


def test_context_is_case_insensitive_but_must_be_unique(tmp_path):
    assert guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status(context="Local-CI/Pull_Request")])) is None
    two = [status(), status(context="LOCAL-CI/PULL_REQUEST")]
    (tmp_path / "two").mkdir()  # make_repo cannot run twice in one directory
    assert "exactly one" in guard(tmp_path / "two", "gh pr merge 7", fake_gh(tmp_path / "two", two))


def test_other_creator_denies(tmp_path):
    assert "creator" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status(login="someone")]))


def test_repo_flag_for_another_repo_denies(tmp_path):
    reason = guard(tmp_path, "gh pr merge 7 -R other/repo", fake_gh(tmp_path, [status()]))
    assert "run gh pr merge from the repo directory" in reason
