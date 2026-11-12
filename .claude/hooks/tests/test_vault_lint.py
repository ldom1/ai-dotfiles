"""vault-lint.sh: unresolved links, orphans, stale-cache warning, missing skill paths."""
import json
import os
import subprocess
import time
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "brain-audit" / "scripts" / "vault-lint.sh"

# STUB_CRLF=1 mimics the Windows .com (CRLF output).
STUB = """#!/bin/bash
set -o pipefail
main() {
shift
case "$*" in
  "unresolved total")
    [ -n "$STUB_FAIL" ] && { echo "$STUB_FAIL" >&2; exit 1; }
    [ -n "$STUB_FAIL_STDOUT" ] && { echo "$STUB_FAIL_STDOUT"; exit 1; }
    echo "${STUB_TOTAL:-82}" ;;
  "unresolved format=json") if [ -n "$STUB_JSON_RAW" ]; then echo "$STUB_JSON_RAW"; else cat "$STUB_UNRESOLVED_JSON"; fi ;;
  "orphans") printf '%s\\n' inbox/daily/2026-01-01.md projects/x/a.md projects/x.md resources/o.md ;;
  file\\ path=*) [ -n "$STUB_MODIFIED" ] && printf 'path       %s\\nmodified   %s\\n' "${2#path=}" "$STUB_MODIFIED" || { echo "File not found" >&2; exit 1; } ;;
  *) echo "unexpected: $*" >&2; exit 2 ;;
esac
}
main "$@" | if [ -n "$STUB_CRLF" ]; then sed 's/$/\\r/'; else cat; fi
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
        + [{"link": "arr", "count": "0", "sources": ["a.md", "b.md"]}]
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


def fresh_ms(note: Path) -> str:
    return str(int(note.stat().st_mtime * 1000) + 1000)


def test_counts_from_cli(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills)
    assert r.returncode == 0, r.stderr
    assert "unresolved: 82" in r.stdout
    # resources/o.md and projects/x.md count; inbox/daily/ and projects/x/ do not
    assert "orphans (outside inbox/daily, projects/*/): 2" in r.stdout
    top = [ln for ln in r.stdout.splitlines() if ln.startswith("  ")]
    assert len(top) == 10
    assert "t12" in top[0] and "s12.md" in top[0]  # sorted by int(count) desc
    assert "t3" in top[-1]  # t1, t2 and arr cut off


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
    (skills / "x" / "SKILL.md").write_text(
        "line1\nsee `$BRAIN_PATH/nope/` and `$BRAIN_PATH/ok/`\n"
        "ignored: `$BRAIN_PATH/a/<slug>/` `$BRAIN_PATH/$TODAY/x.md` `$BRAIN_PATH/g/*.md`\n"
    )
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
    r = run(vault, stub, unresolved, skills, STUB_MODIFIED=fresh_ms(note))
    assert r.returncode == 0
    assert "unresolved: 82" in r.stdout
    assert "warning:" not in r.stdout


def test_unresolved_json_garbage_is_an_error(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills, STUB_JSON_RAW="hello")
    assert r.returncode == 1
    assert "error:" in r.stdout + r.stderr


def test_array_sources_joined(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    unresolved.write_text(json.dumps([{"link": "arr", "count": "5", "sources": ["a.md", "b.md"]}]))
    r = run(vault, stub, unresolved, skills)
    assert "arr (5): a.md, b.md" in r.stdout


def test_multiline_total_is_an_error(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills, STUB_TOTAL="8\n2")
    assert r.returncode == 1
    assert "error:" in r.stdout + r.stderr
    assert "unresolved:" not in r.stdout


def test_crlf_output_parses(tmp_path):
    vault, note, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills, STUB_CRLF="1", STUB_MODIFIED=fresh_ms(note))
    assert r.returncode == 0, r.stderr
    assert "unresolved: 82" in r.stdout
    assert "orphans (outside inbox/daily, projects/*/): 2" in r.stdout
    assert "warning:" not in r.stdout
    assert "\r" not in r.stdout


def test_error_falls_back_to_stdout_line(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    r = run(vault, stub, unresolved, skills, STUB_FAIL_STDOUT="Error: vault not found")
    assert r.returncode == 1
    assert "error: Obsidian CLI failed (exit 1): Error: vault not found" in r.stdout + r.stderr


def test_cli_not_executable_is_an_error(tmp_path):
    vault, _, stub, unresolved, skills = setup(tmp_path)
    stub.chmod(0o644)
    r = run(vault, stub, unresolved, skills)
    assert r.returncode == 1
    assert "error:" in r.stdout + r.stderr
    assert "skipped:" not in r.stdout


def test_newest_file_in_dot_directory_ignored(tmp_path):
    vault, note, stub, unresolved, skills = setup(tmp_path)
    trash = vault / ".trash"
    trash.mkdir()
    (trash / "deleted.md").write_text("x")
    future = time.time() + 3600
    os.utime(trash / "deleted.md", (future, future))
    r = run(vault, stub, unresolved, skills, STUB_MODIFIED=fresh_ms(note))
    assert "warning:" not in r.stdout


def test_stale_cache_warns_through_symlinked_vault(tmp_path):
    vault, note, stub, unresolved, skills = setup(tmp_path)
    link = tmp_path / "linked"
    link.symlink_to(vault)
    old = int(note.stat().st_mtime * 1000) - 60000
    r = run(link, stub, unresolved, skills, STUB_MODIFIED=str(old))
    assert "warning: Obsidian link cache is stale" in r.stdout
