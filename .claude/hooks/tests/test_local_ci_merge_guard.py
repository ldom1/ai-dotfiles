"""local-ci-merge-guard.py: deny `gh pr merge` unless a fresh local-ci/pull_request success is on the PR head."""
import json
import os
import stat
import subprocess
from pathlib import Path

import pytest
from test_local_ci import GIT_ENV, git, make_repo

HOOK = Path(__file__).resolve().parents[1] / "local-ci-merge-guard.py"
H, B = "a" * 40, "b" * 40
IMG = "sha256:" + "ab" * 32


def status(state="success", desc=f"full base={B} img=abababababab 42s", context="local-ci/pull_request", login="ldom1"):
    return {"state": state, "context": context, "description": desc, "creator": {"login": login}}


def fake_gh(tmp_path, statuses, total=None, head=H, base_tip=B, sha=None):
    p = tmp_path / "gh"
    combined = {"sha": sha or head, "total_count": len(statuses) if total is None else total, "statuses": statuses}
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


PARSE_FAIL = "cannot parse this gh pr merge command"
REPO_DIR = "run gh pr merge from the repo directory"


def test_merge_on_a_later_line_is_checked(tmp_path):
    assert "no local-ci/pull_request status" in guard(tmp_path, "echo hi\ngh pr merge 7", fake_gh(tmp_path, []))


def test_next_line_is_not_an_argument(tmp_path):
    assert guard(tmp_path, "gh pr merge 7 --squash\ngit status", fake_gh(tmp_path, [status()])) is None


@pytest.mark.parametrize("command", [
    "(gh pr merge 7)",
    "if true; then gh pr merge 7; fi",
    "bash -c 'gh pr merge 7'",
    "echo $(gh pr merge 7)",
    "sudo gh pr merge 7",
    "cat <<EOF\nit's\nEOF\ngh pr merge 7",
    "gh pr \\\nmerge 7",
])
def test_unparseable_merge_forms_deny(tmp_path, command):
    assert PARSE_FAIL in guard(tmp_path, command, fake_gh(tmp_path, [status()]))


def test_unparseable_merge_is_allowed_when_guard_is_off(tmp_path):
    assert guard(tmp_path, "bash -c 'gh pr merge 7'", fake_gh(tmp_path, []), guard_on=False) is None


def test_glued_repo_flag_denies(tmp_path):
    assert REPO_DIR in guard(tmp_path, "gh pr merge 7 -Rother/repo", fake_gh(tmp_path, [status()]))


def test_repo_equals_flag_for_another_repo_denies(tmp_path):
    assert REPO_DIR in guard(tmp_path, "gh pr merge 7 --repo=other/repo", fake_gh(tmp_path, [status()]))


def test_gh_repo_env_for_another_repo_denies(tmp_path):
    assert REPO_DIR in guard(tmp_path, "GH_REPO=o/r gh pr merge 7", fake_gh(tmp_path, [status()]))


def test_gh_repo_env_for_this_repo_allows(tmp_path):
    assert guard(tmp_path, "GH_REPO=acme/widget gh pr merge 7", fake_gh(tmp_path, [status()])) is None


@pytest.mark.parametrize("command", ["cd /tmp && gh pr merge 7", "pushd /tmp; gh pr merge 7", "(cd /tmp; gh pr merge 7)"])
def test_cd_before_merge_denies(tmp_path, command):
    assert "without cd" in guard(tmp_path, command, fake_gh(tmp_path, [status()]))


def test_cd_after_merge_is_fine(tmp_path):
    assert guard(tmp_path, "gh pr merge 7 && cd /tmp", fake_gh(tmp_path, [status()])) is None


def test_cd_without_merge_is_ignored(tmp_path):
    assert guard(tmp_path, "cd /tmp && gh pr view 7", fake_gh(tmp_path, [])) is None


def test_trailing_newline_in_description_denies(tmp_path):
    assert "description" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status(desc=f"full base={B} img=abababababab 42s\n")]))


def test_combined_status_for_another_sha_denies(tmp_path):
    assert "not the PR head" in guard(tmp_path, "gh pr merge 7", fake_gh(tmp_path, [status()], sha="d" * 40))
