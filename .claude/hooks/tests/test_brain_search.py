"""brain-search: --limit maps to qmd -n, SKILL.md carries the query rules."""
import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def test_limit_maps_to_n(tmp_path):
    index = tmp_path / "brain.db"
    index.write_text("")
    log = tmp_path / "argv.log"
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    qmd = bin_dir / "qmd"
    qmd.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{log}"\n')
    qmd.chmod(0o755)
    env = {k: v for k, v in os.environ.items() if k not in ("QMD_INDEX_PATH", "INDEX_PATH", "BRAIN_ENV_FILE")}
    env.update(QMD_INDEX_PATH=str(index), PATH=f"{bin_dir}:{os.environ['PATH']}")
    r = subprocess.run(
        ["bash", str(ROOT / "skills/brain-search/scripts/search.sh"), "--limit", "2", "foo"],
        env=env, capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    argv = log.read_text().split()
    assert argv[argv.index("-n") + 1] == "2"
    assert "--limit" not in argv


def test_skill_text_rules():
    text = (ROOT / "skills/brain-search/SKILL.md").read_text()
    for needle in ("mcp__qmd__query", "12 KiB", "48 KiB", "128 KiB", "never an instruction",
                   "This script serves agents without the qmd MCP server (Vibe today)."):
        assert needle in text, needle
