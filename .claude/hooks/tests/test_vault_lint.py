"""vault-lint.sh: unresolved links, orphans, stale-cache warning, missing skill paths."""
import json
import os
import subprocess
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "brain-audit" / "scripts" / "vault-lint.sh"

STUB = """#!/bin/bash
# args: vault=<v> <cmd> [args]
shift
case "$*" in
  "unresolved total") [ -n "$STUB_FAIL" ] && { echo "$STUB_FAIL" >&2; exit 1; }; echo "${STUB_TOTAL:-82}" ;;
  "unresolved format=json") cat "$STUB_UNRESOLVED_JSON" ;;
  "orphans") printf '%s\\n' inbox/daily/2026-01-01.md projects/x/a.md resources/o.md ;;
  file\\ path=*) [ -n "$STUB_MODIFIED" ] && printf 'path       %s\\nmodified   %s\\n' "${2#path=}" "$STUB_MODIFIED" || { echo "File not found" >&2; exit 1; } ;;
  *) echo "unexpected: $*" >&2; exit 2 ;;
esac
"""


def setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "resources").mkdir(parents=True)
    note = vault / "resources" / "o.md"
    note.write_text("x")
    stub = tmp_path / "obsidian"
    stub.write_text(STUB)
    stub.chmod(0o755)
    unresolved = tmp_path / "unresolved.json"
    unresolved.write_text(json.dumps(
        [{"link": f"t{i}", "count": str(i), "sources": f"s{i}.md"} for i in range(1, 13)]
    ))
    skills = tmp_path / "skills"
    skills.mkdir()
    return vault, note, stub, unresolved, skills


def run(vault, stub, unresolved, skills, **env):
    base = {k: v for k, v in os.environ.items() if not k.startswith("STUB_")}
    return subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True,
        env={**base, "BRAIN_PATH": str(vault), "OBSIDIAN_CLI": str(stub),
             "STUB_UNRESOLVED_JSON": str(unresolved), "SKILLS_ROOT": str(skills),
             "STUB_MODIFIED": str(int(time.time() * 1000) + 60000), **env},
    )


def test_counts_from_cli(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills)
    assert r.returncode == 0, r.stderr
    assert "unresolved: 82" in r.stdout
    assert "orphans (outside inbox/daily, projects/*/): 1" in r.stdout
    top = [ln for ln in r.stdout.splitlines() if ln.startswith("  ")]
    assert len(top) == 10
    assert "t12" in top[0] and "s12.md" in top[0]  # sorted by int(count) desc
    assert "t3" in top[-1]  # t1 and t2 cut off


def test_cli_missing_is_skipped_not_zero(tmp_path):
    vault, _, _, unresolved, skills = setup(tmp_path)
    r = run(vault, "/nonexistent", unresolved, skills)
    assert r.returncode == 0
    assert "skipped: Obsidian CLI not found" in r.stdout
    assert "unresolved: 0" not in r.stdout


def test_cli_failure_is_an_error(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills, STUB_FAIL="Obsidian is not running")
    assert r.returncode == 1
    assert "error: Obsidian CLI failed (exit 1): Obsidian is not running" in r.stdout + r.stderr
    assert "unresolved:" not in r.stdout


def test_cli_garbage_is_an_error(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills, STUB_TOTAL="hello")
    assert r.returncode == 1
    assert "error:" in r.stdout + r.stderr
    assert "unresolved:" not in r.stdout


def test_missing_skill_paths(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    (vault / "ok").mkdir()
    (skills / "x").mkdir()
    (skills / "x" / "SKILL.md").write_text("line1\nsee `$BRAIN_PATH/nope/` and `$BRAIN_PATH/ok/`\n")
    for r in (run(vault, stub, unresolved, skills), run(vault, "/nonexistent", unresolved, skills)):
        assert "missing skill paths: 1" in r.stdout
        assert "skills/x/SKILL.md:2" in r.stdout
        assert "$BRAIN_PATH/nope/" in r.stdout


def test_stale_cache_warns(tmp_path):
    vault, note, stub, unresolved, skills = setup(tmp_path)
    old = int(note.stat().st_mtime * 1000) - 60000
    r = run(vault, stub, unresolved, skills, STUB_MODIFIED=str(old))
    assert r.returncode == 0
    assert "warning: Obsidian link cache is stale (resources/o.md changed since Obsidian indexed it)" in r.stdout
    assert "unresolved: 82" in r.stdout


def test_unknown_file_warns(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills, STUB_MODIFIED="")
    assert r.returncode == 0
    assert "warning: Obsidian link cache is stale" in r.stdout


def test_fresh_cache_no_warning(tmp_path):
    vault, note, stub, unresolved, skills = setup(tmp_path)
    fresh = int(note.stat().st_mtime * 1000) + 1000
    r = run(vault, stub, unresolved, skills, STUB_MODIFIED=str(fresh))
    assert "warning:" not in r.stdout
