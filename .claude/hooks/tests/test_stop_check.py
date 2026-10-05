"""stop-check.sh runs the project's .claude/stop-check after a turn and blocks the stop only on failure."""
import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "stop-check.sh"


def make_repo(path: Path, check: str | None = None) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    if check is not None:
        (path / ".claude").mkdir()
        (path / ".claude" / "stop-check").write_text(check + "\n")
    return path


def run(cwd: Path, tmp_path: Path, active: bool = False) -> dict:
    event = {"cwd": str(cwd), "stop_hook_active": active, "hook_event_name": "Stop"}
    out = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True,
                         check=True, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}).stdout
    return json.loads(out) if out.strip() else {}


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
