"""init-project.sh / upgrade-project.sh / bin/ai-dotfiles, run from a tmp copy of the repo.

The scripts derive AI_DOTFILES (registry, templates, lib-mcp) from their own location and
write under $HOME (setup_central_mcp) and $BRAIN_PATH. The fixture copies them into a tmp
root with its own brain.env and registry, and sets HOME to a tmp dir: nothing real is touched.
"""
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def env(tmp_path):
    dot = tmp_path / "dot"
    shutil.copytree(ROOT / "bin", dot / "bin")
    shutil.copytree(ROOT / "scripts", dot / "scripts")
    shutil.copytree(ROOT / "config/memory-templates", dot / "config/memory-templates")
    shutil.copytree(ROOT / "skills/brain-load/scripts", dot / "skills/brain-load/scripts")
    vault = tmp_path / "vault"
    (vault / "projects").mkdir(parents=True)
    home = tmp_path / "home"
    home.mkdir()
    (dot / "config/brain.env").write_text(
        f'export BRAIN_PATH="{vault}"\nexport QMD_INDEX_PATH="{tmp_path}/brain.db"\n'
    )
    clean = {k: v for k, v in os.environ.items()
             if k not in ("BRAIN_PATH", "BRAIN_ENV_FILE", "QMD_INDEX_PATH", "INDEX_PATH", "PRATIQUE_IA_PATH")}
    clean["HOME"] = str(home)
    return dot, clean, tmp_path


def _repo(base: Path, name: str) -> Path:
    repo = base / name
    repo.mkdir()
    (repo / ".brain-project").write_text(f"{name}\n")
    return repo


def _run(dot, clean, *args):
    return subprocess.run(["bash", str(dot / "bin/ai-dotfiles"), *args],
                          env=clean, capture_output=True, text=True)


def test_init_and_upgrade_render_same_agents_md(env):
    dot, clean, tmp = env
    a, b = _repo(tmp, "repo-a"), _repo(tmp, "repo-b")
    r = _run(dot, clean, "init", str(a))
    assert r.returncode == 0, r.stderr
    r = _run(dot, clean, "upgrade", str(b))
    assert r.returncode == 0, r.stderr
    tpl = (ROOT / "config/memory-templates/AGENTS.md.tpl").read_bytes()
    assert (a / "AGENTS.md").read_bytes() == tpl
    assert (b / "AGENTS.md").read_bytes() == tpl


def test_upgrade_reports_settings_merge_failure(env):
    dot, clean, tmp = env
    repo = _repo(tmp, "repo-a")
    assert _run(dot, clean, "upgrade", str(repo)).returncode == 0
    bad = repo / ".claude/memory/settings.json"
    bad.write_text("{not json")
    r = _run(dot, clean, "upgrade", str(repo))
    assert r.returncode != 0
    assert str(bad) in r.stderr


def test_merge_memory_subcommand_removed(env):
    dot, clean, tmp = env
    assert not (ROOT / "scripts/merge-memory.sh").exists()
    r = _run(dot, clean, "merge-memory", str(_repo(tmp, "repo-a")))
    assert r.returncode != 0
    assert "upgrade" in r.stderr
    assert "merge-memory" not in r.stderr


def test_upgrade_all_continues_past_failed_project(env):
    dot, clean, tmp = env
    a, b = _repo(tmp, "repo-a"), _repo(tmp, "repo-b")
    for repo in (a, b):  # registers both, in order
        assert _run(dot, clean, "upgrade", str(repo)).returncode == 0
    (a / ".claude/memory/settings.json").write_text("{not json")
    (b / "AGENTS.md").unlink()
    r = _run(dot, clean, "upgrade", "--all")
    assert r.returncode != 0
    assert "repo-a" in r.stderr
    assert (b / "AGENTS.md").exists()


def _registry(dot, *repos):
    rows = "".join(f"{r.name}\t{r}\t2026-01-01T00:00:00Z\n" for r in repos)
    (dot / "config/brain-projects.tsv").write_text("name\tabs_path\tregistered_at\n" + rows)


@pytest.mark.skipif(os.geteuid() == 0, reason="root ignores read-only directories")
def test_upgrade_all_marks_failed_migration(env):
    dot, clean, tmp = env
    a, b = _repo(tmp, "repo-a"), _repo(tmp, "repo-b")
    (a / ".claude/brain").mkdir(parents=True)
    _registry(dot, a, b)
    # Read-only .claude: `mv .claude/brain .claude/memory` cannot rename inside it.
    (a / ".claude").chmod(0o555)
    try:
        r = _run(dot, clean, "upgrade", "--all")
    finally:
        (a / ".claude").chmod(0o755)
    assert r.returncode != 0
    assert "upgrade failed for: repo-a" in r.stderr
    assert (b / "AGENTS.md").exists()  # next project still runs
    assert not (a / "AGENTS.md").exists()  # errexit stopped repo-a at the mv
    assert not (tmp / "vault/projects/repo-a").exists()
    assert (a / ".claude/brain").is_dir() and not (a / ".claude/memory").exists()


def test_upgrade_all_runs_central_mcp_once(env):
    dot, clean, tmp = env
    a, b = _repo(tmp, "repo-a"), _repo(tmp, "repo-b")
    _registry(dot, a, b)
    marker = tmp / "mcp-calls"
    (dot / "scripts/lib-mcp.sh").write_text(f'setup_central_mcp() {{ echo x >> "{marker}"; }}\n')
    assert _run(dot, clean, "upgrade", "--all").returncode == 0
    assert marker.read_text().count("x") == 1
    assert _run(dot, clean, "upgrade", str(a)).returncode == 0
    assert marker.read_text().count("x") == 2  # single-project path still syncs
