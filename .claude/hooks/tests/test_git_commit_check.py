"""git-commit-check.sh picks the scope list of the repo the commit targets, not the session cwd."""
import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "git-commit-check.sh"


def make_repo(path: Path, marker: str) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / marker).write_text("")
    return path


def decision(cwd: Path, command: str) -> str:
    out = subprocess.run(["bash", str(HOOK)], cwd=cwd, input=json.dumps({"tool_input": {"command": command}}),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "allow"


def msg(scope: str) -> str:
    return '-m "fix(' + scope + '): x"'


def test_scope_follows_cd_target(tmp_path):
    session = make_repo(tmp_path / "ansible-proj", "ansible.cfg")
    py = make_repo(tmp_path / "py-proj", "pyproject.toml")
    assert decision(session, f"cd {py} && git commit {msg('api')}") == "allow"  # python-only scope
    assert decision(session, f"cd {py} && git commit {msg('roles')}") == "deny"  # ansible-only scope


def test_last_cd_before_commit_wins(tmp_path):
    session = make_repo(tmp_path / "ansible-proj", "ansible.cfg")
    py = make_repo(tmp_path / "py-proj", "pyproject.toml")
    assert decision(session, f"cd {session} && cd {py} && git commit {msg('api')}") == "allow"


def test_scope_follows_git_dash_c(tmp_path):
    session = make_repo(tmp_path / "ansible-proj", "ansible.cfg")
    py = make_repo(tmp_path / "py-proj", "pyproject.toml")
    assert decision(session, f"git -C {py} commit {msg('api')}") == "allow"
    assert decision(session, f"git -C {py} commit {msg('roles')}") == "deny"


def test_session_cwd_still_used_without_target(tmp_path):
    session = make_repo(tmp_path / "ansible-proj", "ansible.cfg")
    assert decision(session, f"git commit {msg('api')}") == "deny"
    assert decision(session, f"git commit {msg('roles')}") == "allow"


# T10: commit-like text inside data (heredoc bodies, quotes, args) is not a commit.

def output(cwd: Path, command: str) -> str:
    return subprocess.run(["bash", str(HOOK)], cwd=cwd, input=json.dumps({"tool_input": {"command": command}}),
                          capture_output=True, text=True, check=True).stdout.strip()


def py_session(tmp_path):
    return make_repo(tmp_path / "py-proj", "pyproject.toml")


def test_commit_text_in_heredoc_body_is_ignored(tmp_path):
    cmd = "cat > f <<'EOF'\ngit commit -m \"bad message\"\nEOF"
    assert output(py_session(tmp_path), cmd) == ""


def test_commit_text_in_python_heredoc_string_is_ignored(tmp_path):
    cmd = "python3 - <<'EOF'\ns = 'run git commit -m \"x\" now'\nprint(s)\nEOF"
    assert output(py_session(tmp_path), cmd) == ""


def test_commit_text_in_quoted_echo_is_ignored(tmp_path):
    assert output(py_session(tmp_path), "echo 'git commit -m \"bad\"' >> notes.md") == ""


def test_commit_text_in_grep_arg_is_ignored(tmp_path):
    assert output(py_session(tmp_path), 'grep -n "git commit" README.md') == ""


def test_plain_bad_commit_denied(tmp_path):
    assert decision(py_session(tmp_path), 'git commit -m "bad message"') == "deny"


def test_git_dash_c_bad_commit_denied(tmp_path):
    session = py_session(tmp_path)
    assert decision(session, 'git -C repo commit -m "bad message"') == "deny"


def test_cd_then_bad_commit_denied(tmp_path):
    session = py_session(tmp_path)
    assert decision(session, f'cd {session} && git commit -m "bad message"') == "deny"


def test_global_options_before_commit_denied(tmp_path):
    session = py_session(tmp_path)
    assert decision(session, 'git --no-pager -c user.name=x commit -m "bad message"') == "deny"


def test_commit_after_heredoc_still_detected(tmp_path):
    cmd = "cat > f <<'EOF'\nhello\nEOF\ngit commit -m \"bad message\""
    assert decision(py_session(tmp_path), cmd) == "deny"


def test_heredoc_message_valid_allowed(tmp_path):
    cmd = "git commit -m \"$(cat <<'EOF'\nfeat(core): add x\n\nbody\nEOF\n)\""
    assert output(py_session(tmp_path), cmd) == ""


def test_heredoc_message_bad_denied(tmp_path):
    cmd = "git commit -m \"$(cat <<'EOF'\nbad message\n\nbody\nEOF\n)\""
    assert decision(py_session(tmp_path), cmd) == "deny"


def test_dash_f_heredoc_allowed_with_reminder(tmp_path):
    cmd = "git commit -F - <<'EOF'\nbad message\nEOF"
    out = json.loads(output(py_session(tmp_path), cmd))
    assert out["hookSpecificOutput"]["permissionDecision"] == "allow"
    assert "reminder" in out["hookSpecificOutput"]["permissionDecisionReason"]


def test_message_forms_still_parsed(tmp_path):
    s = py_session(tmp_path)
    assert decision(s, 'git commit -m "fix(core): don\'t crash"') == "allow"
    assert decision(s, "git commit -m 'fix(core): x' --no-verify") == "allow"
    assert decision(s, 'git commit -am "bad message"') == "deny"
    assert decision(s, "git commit --message='bad message'") == "deny"
    assert decision(s, "GIT_AUTHOR_NAME=x git commit -m 'bad message'") == "deny"
    assert decision(s, "git commit -m \"Merge branch 'main' into develop\"") == "allow"


def test_unparsable_command_fails_open(tmp_path):
    assert output(py_session(tmp_path), "git commit -m \"unterminated") == ""
