"""install.sh refuses unknown arguments and refuses to run from a linked git worktree."""
import os
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
ENV_PATH = "/usr/bin:/bin"


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"PATH": ENV_PATH, "HOME": str(cwd), "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


def fake_repo(tmp_path: Path) -> Path:
    d = tmp_path / "dotfiles"
    (d / "scripts").mkdir(parents=True)
    shutil.copy(REPO / "scripts" / "install.sh", d / "scripts" / "install.sh")
    (d / "scripts" / "build-agent-rules.sh").write_text("true\n")
    (d / "scripts" / "merge-settings.py").write_text("raise SystemExit(7)\n")  # stops install.sh after step 1c
    git("init", "-q", cwd=d)
    git("add", ".", cwd=d)
    git("commit", "-q", "-m", "init", cwd=d)
    (tmp_path / "home").mkdir()
    return d


def install(script: Path, home: Path, *args):
    return subprocess.run(["bash", str(script), *args], capture_output=True, text=True,
                          env={"PATH": ENV_PATH, "HOME": str(home)})


def test_main_checkout_passes_the_guard(tmp_path):
    d = fake_repo(tmp_path)
    r = install(d / "scripts" / "install.sh", tmp_path / "home")
    assert r.returncode == 7, r.stdout + r.stderr
    assert os.readlink(tmp_path / "home" / ".claude") == str(d / ".claude")


def test_unknown_argument_is_refused_before_any_change(tmp_path):
    d = fake_repo(tmp_path)
    r = install(d / "scripts" / "install.sh", tmp_path / "home", "--dry-run")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "unknown argument: --dry-run" in r.stderr
    assert list((tmp_path / "home").iterdir()) == []


def test_linked_worktree_is_refused_before_any_change(tmp_path):
    d = fake_repo(tmp_path)
    git("worktree", "add", "-q", str(tmp_path / "wt"), cwd=d)
    r = install(tmp_path / "wt" / "scripts" / "install.sh", tmp_path / "home")
    assert r.returncode == 2, r.stdout + r.stderr
    assert "linked git worktree" in r.stderr and str(d) in r.stderr
    assert list((tmp_path / "home").iterdir()) == []
