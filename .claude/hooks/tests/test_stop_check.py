"""stop-check.sh runs the project's .claude/stop-check after a turn and blocks the stop only on failure.

The check runs only when its normalized command is approved in ~/.claude/stop-check-trust."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / ".claude" / "hooks" / "stop-check.sh"
TRUST = REPO / "bin" / "stop-check-trust"


def make_repo(path: Path, check: str | None = None) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    if check is not None:
        (path / ".claude").mkdir()
        (path / ".claude" / "stop-check").write_text(check + "\n")
    return path


def normalize(text: str) -> str:
    lines = [line.rstrip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line and not line.lstrip().startswith("#"))


def repo_id(repo: Path) -> str:
    out = subprocess.run(["git", "-C", str(repo), "rev-parse", "--git-common-dir"], capture_output=True,
                         text=True, check=True).stdout.strip()
    return str((repo / out).resolve())


def approve(repo: Path, tmp_path: Path, text: str | None = None) -> None:
    """Append the trust line for `text` (default: the repo's current check) to the temp HOME's store."""
    text = text if text is not None else (repo / ".claude" / "stop-check").read_text()
    digest = hashlib.sha256(normalize(text).encode()).hexdigest()
    store = tmp_path / ".claude" / "stop-check-trust"
    store.parent.mkdir(parents=True, exist_ok=True)
    with store.open("a") as f:
        f.write(f"{digest} {repo_id(repo)}\n")


def fire(cwd: Path, tmp_path: Path, active: bool = False, session: str = "s1") -> dict:
    event = {"cwd": str(cwd), "stop_hook_active": active, "hook_event_name": "Stop", "session_id": session}
    (tmp_path / "tmp").mkdir(exist_ok=True)
    env = {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "TMPDIR": str(tmp_path / "tmp")}
    out = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True,
                         check=True, env=env).stdout
    return json.loads(out) if out.strip() else {}


def run(cwd: Path, tmp_path: Path, active: bool = False) -> dict:
    """Run the hook with the repo's current check already approved."""
    if (cwd / ".claude" / "stop-check").exists():
        approve(cwd, tmp_path)
    return fire(cwd, tmp_path, active)


def test_failing_check_on_dirty_tree_blocks_with_output(tmp_path):
    repo = make_repo(tmp_path / "p", "echo 'E501 line too long'; exit 1")
    (repo / "x.py").write_text("x = 1\n")
    result = run(repo, tmp_path)
    assert result["decision"] == "block"
    assert "E501 line too long" in result["reason"]


def test_passing_check_is_silent(tmp_path):
    repo = make_repo(tmp_path / "p", "true")
    (repo / "x.py").write_text("x = 1\n")
    assert run(repo, tmp_path) == {}


def test_no_stop_check_file_is_silent(tmp_path):
    repo = make_repo(tmp_path / "p")
    (repo / "x.py").write_text("x = 1\n")
    assert run(repo, tmp_path) == {}


def test_clean_tree_skips_the_check(tmp_path):
    repo = make_repo(tmp_path / "p", "exit 1")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
                   check=True)
    assert run(repo, tmp_path) == {}


def test_second_stop_after_a_block_never_blocks_again(tmp_path):
    repo = make_repo(tmp_path / "p", "exit 1")
    (repo / "x.py").write_text("x = 1\n")
    assert run(repo, tmp_path, active=True) == {}


def test_outside_a_git_repo_is_silent(tmp_path):
    (tmp_path / "plain").mkdir()
    assert run(tmp_path / "plain", tmp_path) == {}


# --- trust gate ------------------------------------------------------------------------------

def dirty_repo(tmp_path: Path, check: str, name: str = "p") -> Path:
    repo = make_repo(tmp_path / name, check)
    (repo / "x.py").write_text("x = 1\n")
    return repo


def test_untrusted_check_warns_once_and_does_not_run(tmp_path):
    marker = tmp_path / "pwned"
    repo = dirty_repo(tmp_path, f"touch {marker}; exit 1")
    result = fire(repo, tmp_path)
    assert "decision" not in result and "reason" not in result
    assert "command not approved" in result["systemMessage"]
    assert f"touch {marker}" in result["systemMessage"]
    assert "stop-check-trust" in result["systemMessage"]
    assert not marker.exists()


def test_trusted_check_blocks_on_failure(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    approve(repo, tmp_path)
    assert fire(repo, tmp_path)["decision"] == "block"


def test_changed_command_is_untrusted_and_revert_is_trusted_again(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    approve(repo, tmp_path)
    check = repo / ".claude" / "stop-check"
    check.write_text("exit 2\n")
    assert "command not approved" in fire(repo, tmp_path, session="a")["systemMessage"]
    check.write_text("exit 1\n")
    assert fire(repo, tmp_path, session="b")["decision"] == "block"


def test_comment_blank_line_trailing_space_and_crlf_edits_stay_trusted(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    approve(repo, tmp_path)
    check = repo / ".claude" / "stop-check"
    for text in ("# new comment\n\nexit 1\n", "exit 1   \n", "exit 1\r\n", "\n\n# only comments\nexit 1\n\n"):
        check.write_bytes(text.encode())
        assert fire(repo, tmp_path)["decision"] == "block", repr(text)


def test_two_approved_hashes_for_one_repo_both_run(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    approve(repo, tmp_path)
    approve(repo, tmp_path, "exit 2\n")
    assert "exit 1" in fire(repo, tmp_path)["reason"]
    (repo / ".claude" / "stop-check").write_text("exit 2\n")
    assert "exit 2" in fire(repo, tmp_path)["reason"]


def test_worktree_of_an_approved_repo_is_trusted(tmp_path):
    repo = make_repo(tmp_path / "p", "exit 1")
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "init"],
                   check=True)
    approve(repo, tmp_path)
    wt = tmp_path / "wt"
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(wt)], check=True)
    (wt / "x.py").write_text("x = 1\n")
    assert fire(wt, tmp_path)["decision"] == "block"


def test_same_session_second_turn_is_silent_and_a_new_session_warns_again(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    assert "systemMessage" in fire(repo, tmp_path, session="one")
    assert fire(repo, tmp_path, session="one") == {}
    assert "systemMessage" in fire(repo, tmp_path, session="two")


def test_second_hash_in_same_session_warns_once_more(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    assert "systemMessage" in fire(repo, tmp_path)
    (repo / ".claude" / "stop-check").write_text("exit 2\n")
    assert "systemMessage" in fire(repo, tmp_path)
    assert fire(repo, tmp_path) == {}


def test_another_repo_with_the_same_command_is_not_trusted(tmp_path):
    a = dirty_repo(tmp_path, "exit 1", "a")
    b = dirty_repo(tmp_path, "exit 1", "b")
    approve(a, tmp_path)
    assert "command not approved" in fire(b, tmp_path)["systemMessage"]


def test_session_id_cannot_escape_tmpdir(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    fire(repo, tmp_path, session="../../evil")
    assert not (tmp_path / "evil").exists()
    assert list((tmp_path / "tmp").glob("stop-check-warned-*"))


# --- bin/stop-check-trust and the install.sh migration ---------------------------------------

def trust(tmp_path: Path, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(TRUST), *args], capture_output=True, text=True, cwd=cwd,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})


def test_trust_approves_prints_command_and_hash_and_the_hook_then_runs(tmp_path):
    repo = dirty_repo(tmp_path, "# note\nexit 1  ")
    r = trust(tmp_path, cwd=repo)
    digest = hashlib.sha256(b"exit 1").hexdigest()
    assert r.returncode == 0 and "exit 1" in r.stdout and digest in r.stdout
    assert (tmp_path / ".claude" / "stop-check-trust").read_text() == f"{digest} {repo_id(repo)}\n"
    assert fire(repo, tmp_path)["decision"] == "block"


def test_trust_is_idempotent_and_list_prints_the_store(tmp_path):
    repo = dirty_repo(tmp_path, "exit 1")
    trust(tmp_path, str(repo))
    trust(tmp_path, str(repo))
    store = (tmp_path / ".claude" / "stop-check-trust").read_text()
    assert len(store.splitlines()) == 1
    assert trust(tmp_path, "--list").stdout == store


def test_trust_revoke_removes_only_that_repo(tmp_path):
    a = dirty_repo(tmp_path, "exit 1", "a")
    b = dirty_repo(tmp_path, "exit 1", "b")
    trust(tmp_path, str(a))
    trust(tmp_path, str(b))
    assert trust(tmp_path, "--revoke", str(a)).returncode == 0
    store = (tmp_path / ".claude" / "stop-check-trust").read_text()
    assert repo_id(a) not in store and repo_id(b) in store
    assert "command not approved" in fire(a, tmp_path)["systemMessage"]


def test_trust_fails_without_a_check(tmp_path):
    repo = make_repo(tmp_path / "p")
    r = trust(tmp_path, str(repo))
    assert r.returncode != 0 and not (tmp_path / ".claude" / "stop-check-trust").exists()


def test_install_step_approves_this_repos_own_check_without_a_message(tmp_path):
    steps = [line for line in (REPO / "scripts" / "install.sh").read_text().splitlines()
             if line.startswith('"$DOTFILES/bin/stop-check-trust"')]
    assert len(steps) == 1, steps
    subprocess.run(["bash", "-c", steps[0]], check=True,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "DOTFILES": str(REPO)})
    digest = hashlib.sha256(normalize((REPO / ".claude" / "stop-check").read_text()).encode()).hexdigest()
    store = (tmp_path / ".claude" / "stop-check-trust").read_text()
    assert f"{digest} {repo_id(REPO)}" in store.splitlines()
    assert "systemMessage" not in fire(REPO, tmp_path)
