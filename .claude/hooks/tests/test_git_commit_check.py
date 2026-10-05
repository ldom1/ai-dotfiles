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
