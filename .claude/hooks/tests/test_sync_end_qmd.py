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
