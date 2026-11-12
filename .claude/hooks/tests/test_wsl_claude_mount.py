"""~/.claude as a bind mount (WSL): wsl-claude-mount.sh switches the symlink, install.sh keeps the mount.

Windows cannot follow a WSL symlink over \\\\wsl.localhost, so Orca's agent session history saw no
Claude session. Each test runs in a private mount namespace (`unshare -rm`): no sudo, no host change.
"""
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ENV_PATH = "/usr/bin:/bin:/usr/sbin:/sbin"

pytestmark = pytest.mark.skipif(
    subprocess.run(["unshare", "-rm", "true"], capture_output=True).returncode != 0,
    reason="unprivileged mount namespaces are not available",
)


def git(*args, cwd):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True,
                   env={"PATH": ENV_PATH, "HOME": str(cwd), "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t",
                        "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"})


@pytest.fixture
def env(tmp_path):
    d = tmp_path / "dotfiles"
    (d / "scripts").mkdir(parents=True)
    (d / "bin").mkdir()
    for rel in ("scripts/install.sh", "scripts/wsl-claude-mount.sh", "bin/aif-platform"):
        shutil.copy(REPO / rel, d / rel)
    (d / "scripts" / "build-agent-rules.sh").write_text("true\n")
    (d / "scripts" / "merge-settings.py").write_text("raise SystemExit(7)\n")  # stops install.sh after step 1c
    (d / ".claude" / "projects").mkdir(parents=True)
    git("init", "-q", cwd=d)
    git("add", "scripts", "bin", cwd=d)
    git("commit", "-q", "-m", "init", cwd=d)
    home = tmp_path / "home"
    home.mkdir()
    fstab = tmp_path / "fstab"
    fstab.write_text("# fstab\n")
    return d, home, fstab


def in_ns(script: str, home: Path, fstab: Path, platform: str = "wsl"):
    """Run a bash snippet in a private mount namespace; return its result."""
    return subprocess.run(["unshare", "-rm", "bash", "-c", script], capture_output=True, text=True,
                          env={"PATH": ENV_PATH, "HOME": str(home), "AIF_FSTAB": str(fstab),
                               "AIF_PLATFORM": platform})


def test_symlink_becomes_bind_mount_with_fstab_line_and_rerun_is_a_noop(env):
    d, home, fstab = env
    (home / ".claude").symlink_to(d / ".claude")
    mount = d / "scripts" / "wsl-claude-mount.sh"
    r = in_ns(f"bash {mount} && bash {mount} && mountpoint -q ~/.claude && ! test -L ~/.claude"
              f" && test -d ~/.claude/projects", home, fstab)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "already a bind mount" in r.stdout
    assert fstab.read_text().splitlines()[1:] == [f"{d}/.claude {home}/.claude none bind 0 0"]


def test_install_keeps_a_bind_mounted_claude_dir(env):
    d, home, fstab = env
    (home / ".claude").mkdir()
    install = d / "scripts" / "install.sh"
    r = in_ns(f"mount --bind {d}/.claude ~/.claude && {{ bash {install}; echo rc=$?; }}"
              f" && mountpoint -q ~/.claude && ! test -L ~/.claude", home, fstab)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "rc=7" in r.stdout and "is a bind mount of" in r.stdout
    assert not (home / ".claude.bak").exists()


def test_non_empty_claude_dir_is_refused_and_fstab_untouched(env):
    d, home, fstab = env
    (home / ".claude").mkdir()
    (home / ".claude" / "settings.json").write_text("{}")
    r = in_ns(f"bash {d}/scripts/wsl-claude-mount.sh", home, fstab)
    assert r.returncode == 1 and "non-empty directory" in r.stderr
    assert fstab.read_text() == "# fstab\n"


def test_other_fstab_entry_on_claude_is_refused(env):
    d, home, fstab = env
    (home / ".claude").symlink_to(d / ".claude")
    fstab.write_text(f"/elsewhere {home}/.claude none bind 0 0\n")
    r = in_ns(f"bash {d}/scripts/wsl-claude-mount.sh", home, fstab)
    assert r.returncode == 1 and "something else" in r.stderr
    assert (home / ".claude").is_symlink()


def test_native_linux_keeps_the_symlink(env):
    d, home, fstab = env
    (home / ".claude").symlink_to(d / ".claude")
    r = in_ns(f"bash {d}/scripts/wsl-claude-mount.sh", home, fstab, platform="linux")
    assert r.returncode == 0 and "Not WSL" in r.stdout
    assert (home / ".claude").is_symlink() and fstab.read_text() == "# fstab\n"
