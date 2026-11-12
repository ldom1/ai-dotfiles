"""qmd index wiring: brain.env exports INDEX_PATH, lib-mcp defaults to brain.db, search.sh honours BRAIN_ENV_FILE."""
import json
import os
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def _clean_env(**extra):
    env = {k: v for k, v in os.environ.items() if k not in ("QMD_INDEX_PATH", "INDEX_PATH", "BRAIN_ENV_FILE")}
    env.update(extra)
    return env


def test_brain_env_exports_index_path(tmp_path):
    env_file = tmp_path / "brain.env"
    text = (ROOT / "config/brain.env.example").read_text()
    env_file.write_text(text.replace("QMD_INDEX_PATH=\n", "QMD_INDEX_PATH=/x/vault-qmd/brain.db\n"))
    out = subprocess.run(
        ["bash", "-c", f'source "{env_file}"; echo "$QMD_INDEX_PATH|$INDEX_PATH"'],
        env=_clean_env(), capture_output=True, text=True, check=True,
    ).stdout.strip()
    assert out == "/x/vault-qmd/brain.db|/x/vault-qmd/brain.db"


def test_lib_mcp_default_is_brain_db(tmp_path):
    dot = tmp_path / "dot"
    (dot / "scripts").mkdir(parents=True)
    shutil.copy(ROOT / "scripts/lib-mcp.sh", dot / "scripts/lib-mcp.sh")
    shutil.copytree(ROOT / "config/memory-templates", dot / "config/memory-templates")
    home = tmp_path / "home"
    home.mkdir()
    r = subprocess.run(
        ["bash", "-c", f'source "{dot}/scripts/lib-mcp.sh"; setup_central_mcp'],
        env=_clean_env(HOME=str(home)), capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    claude = (home / ".claude.json").read_text()
    json.loads(claude)
    assert "vault-qmd/brain.db" in claude
    assert "index.sqlite" not in claude
    assert "unconfirmed" not in r.stdout


def test_search_sh_honours_brain_env_file(tmp_path):
    index = tmp_path / "brain.db"
    index.write_text("")
    env_file = tmp_path / "brain.env"
    env_file.write_text(f"QMD_INDEX_PATH={index}\nexport QMD_INDEX_PATH\n")
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    qmd = bin_dir / "qmd"
    qmd.write_text('#!/bin/sh\necho "$INDEX_PATH"\n')
    qmd.chmod(0o755)
    r = subprocess.run(
        ["bash", str(ROOT / "skills/brain-search/scripts/search.sh"), "hello"],
        env=_clean_env(BRAIN_ENV_FILE=str(env_file), PATH=f"{bin_dir}:{os.environ['PATH']}"),
        capture_output=True, text=True,
    )
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == str(index)
