"""sync.sh end returns before qmd finishes: Claude Code cancels the SessionEnd hook ~20 s after exit."""
import os
import shutil
import subprocess
import time
from pathlib import Path

SYNC = Path(__file__).resolve().parents[3] / "skills/brain-sync/scripts/sync.sh"


def test_sync_end_does_not_wait_for_qmd(tmp_path):
    # Copy sync.sh alone: its AI_DOTFILES_PATH (three levels up) then has no sync-project.sh to run.
    script = tmp_path / "dot/skills/brain-sync/scripts/sync.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(SYNC, script)
    vault = tmp_path / "vault"
    vault.mkdir()
    subprocess.run(["git", "init", "-q", str(vault)], check=True)
    env_file = tmp_path / "brain.env"
    env_file.write_text(f"BRAIN_PATH={vault}\nQMD_INDEX_PATH={tmp_path / 'index.sqlite'}\n")
    marker = tmp_path / "qmd.calls"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    qmd = bin_dir / "qmd"
    qmd.write_text(f'#!/bin/sh\nsleep 3\necho "$1" >> {marker}\n')
    qmd.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k != "NVM_BIN"}  # sync.sh puts $NVM_BIN (the real qmd) first
    env.update(BRAIN_ENV_FILE=str(env_file), HOME=str(tmp_path), PATH=f"{bin_dir}:{os.environ['PATH']}")

    start = time.monotonic()
    subprocess.run(["bash", str(script), "end"], env=env, capture_output=True, check=True, timeout=30)
    assert time.monotonic() - start < 2.5  # capture_output also waits for any child holding the pipes

    deadline = time.monotonic() + 15
    while time.monotonic() < deadline and not (marker.exists() and len(marker.read_text().split()) == 2):
        time.sleep(0.2)
    assert marker.read_text().split() == ["update", "embed"]


# ── embed lock and commit guard ───────────────────────────────────────────────
# Every path (script copy, vault, HOME, XDG_CACHE_HOME, PATH) lives under tmp_path:
# the copied sync.sh has no sync-project.sh beside it, so the real repo and vault stay untouched.
GIT_ENV = dict(GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t")


def _fixture(tmp_path, *, with_qmd=True, path=None):
    script = tmp_path / "dot/skills/brain-sync/scripts/sync.sh"
    script.parent.mkdir(parents=True)
    shutil.copy(SYNC, script)
    vault = tmp_path / "vault"
    vault.mkdir()
    env = {**os.environ, **GIT_ENV, "HOME": str(tmp_path), "XDG_CACHE_HOME": str(tmp_path / "cache")}
    env.pop("NVM_BIN", None)  # sync.sh puts $NVM_BIN (the real qmd) first
    for cmd in (["init", "-q"], ["commit", "-q", "--allow-empty", "-m", "init"]):
        subprocess.run(["git", "-C", str(vault), *cmd], check=True, env=env)
    (vault / "note.md").write_text("new note\n")  # something to commit
    lines = f"BRAIN_PATH={vault}\n"
    calls = tmp_path / "qmd.calls"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    if with_qmd:
        lines += f"QMD_INDEX_PATH={tmp_path / 'index.sqlite'}\n"
        qmd = bin_dir / "qmd"
        qmd.write_text(f'#!/bin/sh\necho "$1" >> {calls}\n')
        qmd.chmod(0o755)
    (tmp_path / "brain.env").write_text(lines)
    env.update(BRAIN_ENV_FILE=str(tmp_path / "brain.env"), PATH=path or f"{bin_dir}:{os.environ['PATH']}")
    return script, vault, env, calls, tmp_path / ".claude/logs/brain-sync.log"


def _wait(predicate, timeout=15):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(0.1)
    return False


def _end(script, env):
    return subprocess.run(["bash", str(script), "end"], env=env, capture_output=True, text=True, check=True, timeout=30)


def _commits(vault):
    out = subprocess.run(["git", "-C", str(vault), "rev-list", "--count", "HEAD"], capture_output=True, text=True, check=True)
    return int(out.stdout)


def test_second_end_skips_embed_while_locked(tmp_path):
    script, _, env, calls, log = _fixture(tmp_path)
    lock = tmp_path / "cache/qmd-brain.lock"
    lock.parent.mkdir()
    holder = subprocess.Popen(["flock", str(lock), "sleep", "60"])
    try:
        # flock -n fails only once the holder owns the lock
        assert _wait(lambda: subprocess.run(["flock", "-n", str(lock), "true"]).returncode != 0)
        _end(script, env)
        assert _wait(lambda: log.exists() and "qmd embed already running" in log.read_text())
        assert not calls.exists()  # the message is printed before any qmd call would start
    finally:
        holder.kill()
        holder.wait()


def test_no_flock_still_embeds_once(tmp_path):
    # PATH holds only the binaries sync.sh calls, no flock
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for tool in ("bash", "git", "date", "dirname", "mkdir", "grep", "wc", "tr", "setsid", "nohup", "sleep", "cat"):
        (bin_dir / tool).symlink_to(shutil.which(tool))
    script, _, env, calls, log = _fixture(tmp_path, path=str(bin_dir))
    assert shutil.which("flock", path=env["PATH"]) is None
    result = _end(script, env)
    assert "no flock" in result.stderr
    assert _wait(lambda: calls.exists() and len(calls.read_text().split()) == 2)
    assert calls.read_text().split() == ["update", "embed"]


def test_commit_refuses_mid_rebase(tmp_path):
    script, vault, env, _, _ = _fixture(tmp_path, with_qmd=False)
    (vault / ".git/rebase-merge").mkdir()
    before = _commits(vault)
    result = _end(script, env)
    assert "rebase in progress" in result.stderr
    assert _commits(vault) == before


def test_commit_refuses_detached_head(tmp_path):
    script, vault, env, _, _ = _fixture(tmp_path, with_qmd=False)
    subprocess.run(["git", "-C", str(vault), "checkout", "-q", "--detach"], check=True, env=env)
    before = _commits(vault)
    result = _end(script, env)
    assert "detached HEAD" in result.stderr
    assert _commits(vault) == before


def test_commit_still_works_on_a_branch(tmp_path):
    script, vault, env, _, _ = _fixture(tmp_path, with_qmd=False)
    before = _commits(vault)
    _end(script, env)
    assert _commits(vault) == before + 1
