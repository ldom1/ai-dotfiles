"""brain-session-start.sh keeps its whole output under the 9,500 B budget and drops no pitfalls rule silently.

Dependencies of the hook (sync, load, vendored check) are stubs with realistic output sizes
(measured 2026-10-06: project note 2,099 B, vendored warnings 375 B).
"""
import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HOOK = REPO / ".claude" / "hooks" / "brain-session-start.sh"
BUDGET = 9500
E = "\x1b"
EXIT_LOG = "\n".join(
    [f"{E}[1m{E}[0;36m━━━ brain-sync · session end · 2026-10-06T14:26:49 ━━━{E}[0m", ""]
    + [f"[sync-project] proj{i}: syncing /home/u/p{i}/.claude/memory ↔ /mnt/c/vault/projects/proj{i}" for i in range(9)]
    + [f"[sync-project] proj{i}: done." for i in range(9)]
    + [f"[sync-project] WARNING: /home/u/lab/gone{i} does not exist, skipping." for i in range(7)]
    + [f"{E}[0;32m✓{E}[0m brain      committed · 3 file(s) changed", f"{E}[0;32m✓{E}[0m brain      pushed → main"]
) + "\n"


def pitfalls(target: int) -> str:
    """A pitfalls file of at most `target` bytes, made of 5-rule sections."""
    text, i = "---\ntitle: AI-agent pitfalls\n---\n\nIntro.\n\n", 0
    while True:
        sec = f"## Section {i}\n" + "".join(f"- rule {i}.{j} {'r' * 80} ^r{i * 5 + j}\n" for j in range(5))
        if len((text + sec).encode()) > target:
            return text
        text, i = text + sec, i + 1


def exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body + "\n")
    path.chmod(0o755)


ITEM = """---
type: action
project: "[[proj]]"
tool: claude
status: ouvert
created: 2026-11-06
why_not_agent: needs the owner's login
---
Body.
"""
REVIEW_LINE = "[review] proj: 1 ouvert (1 action) → TASKS_REVIEW"
UV = shutil.which("uv")


def uv_env() -> dict:
    """Lets `uv run --script` resolve pyyaml from the real cache, offline, with a fake HOME."""
    cache = subprocess.run([UV, "cache", "dir"], capture_output=True, text=True, check=True).stdout.strip()
    py = subprocess.run([UV, "python", "dir"], capture_output=True, text=True, check=True).stdout.strip()
    return {"PATH": f"/usr/bin:/bin:{Path(UV).parent}", "UV_CACHE_DIR": cache, "UV_PYTHON_INSTALL_DIR": py,
            "UV_OFFLINE": "1"}


def env_for(tmp_path: Path, pitfalls_text: str, exit_log: str | None, review: str | None = None) -> dict:
    dot, vault, home = tmp_path / "dot", tmp_path / "vault", tmp_path / "home"
    exe(dot / "skills/brain-sync/scripts/sync.sh", "exit 0")
    note = "\n".join(f"note line {i:02d} " + "n" * 56 for i in range(30))
    exe(dot / "skills/brain-load/scripts/load.sh",
        f"[[ \"${{1:-}}\" == --slug-only ]] && {{ echo slug=proj; exit 0; }}\ncat <<'EOF'\n{note}\nEOF")
    exe(dot / "scripts/log-skill-usage.sh", "exit 0")
    exe(dot / "scripts/check-vendored-skill-updates.sh", "printf 'w%.0s' {1..374}; echo")
    for name in ("summarize-sync-log.py", "fit-sections.py", "tasks-review.py"):
        (dot / "scripts" / name).symlink_to(REPO / "scripts" / name)
    (dot / "config").mkdir()
    (dot / "config" / "brain.env").write_text(f"BRAIN_PATH={vault}\n")
    p = vault / "resources/operational/ai-agents/pitfalls.md"
    p.parent.mkdir(parents=True)
    p.write_text(pitfalls_text)
    if review is not None:
        (vault / "inbox/review").mkdir(parents=True)
        if review:
            (vault / "inbox/review/2026-11-06-proj-login.md").write_text(review)
    if exit_log is not None:
        log = home / ".claude/logs/brain-sync-end.log"
        log.parent.mkdir(parents=True)
        log.write_text(exit_log)
    return {**uv_env(), "HOME": str(home), "AI_DOTFILES": str(dot)}


def run_hook(env: dict, source: str = "startup", cwd: Path | None = None) -> str:
    return subprocess.run(["bash", str(HOOK)], input=json.dumps({"source": source}), capture_output=True,
                          text=True, check=True, env=env, cwd=cwd).stdout


def run_real_load(tmp_path: Path, note: bytes | None, pitfalls_text: str | None = None, exit_log: str | None = None,
                  review: str | None = None) -> str:
    """Runs the hook with the REAL load.sh on a fixture vault: `projects/proj.md` holds `note` (none: no note file),
    the cwd is `proj/`."""
    env = env_for(tmp_path, pitfalls_text or pitfalls(1000), exit_log, review)
    scripts = Path(env["AI_DOTFILES"]) / "skills/brain-load/scripts"
    (scripts / "load.sh").unlink()
    for name in ("load.sh", "_brain_env.sh"):
        (scripts / name).symlink_to(REPO / "skills/brain-load/scripts" / name)
    (tmp_path / "vault/projects").mkdir()
    if note is not None:
        (tmp_path / "vault/projects/proj.md").write_bytes(note)
    (tmp_path / "proj").mkdir()
    return run_hook(env, cwd=tmp_path / "proj")


def note_text(out: str) -> str:
    """The injected project note: what sits between the header and the footer, without the truncation marker."""
    body = out.split("--- PROJECT NOTE: proj ---\n", 1)[1].split("--- END NOTE ---", 1)[0]
    return "".join(line for line in body.splitlines(keepends=True) if "[brain-load] note truncated" not in line)


def test_note_cut_by_bytes_not_lines(tmp_path):
    note = "".join(f"line {i:03d} ".ljust(39, "x") + "\n" for i in range(1, 101))
    assert len(note.encode()) == 4000
    out = run_real_load(tmp_path, note.encode())
    assert "line 050 " in out and "line 075 " in out
    assert "line 076 " not in out
    assert "note truncated: 3000 of 4000 B" in out
    assert len(note_text(out).encode()) == 3000


def test_short_note_passes_unchanged(tmp_path):
    note = "".join(f"line {i:02d}\n" for i in range(10))
    out = run_real_load(tmp_path, note.encode())
    assert note_text(out) == note
    assert "truncated" not in out


def test_cut_never_splits_utf8(tmp_path):
    out = run_real_load(tmp_path, ("é" * 30 + "\n").encode() * 80)  # 61 B per line: 49 lines fit in 3,000 B
    lines = note_text(out).splitlines(keepends=True)
    assert lines == ["é" * 30 + "\n"] * 49
    assert "note truncated: 2989 of 4880 B" in out


def test_empty_note_prints_nothing(tmp_path):
    out = run_real_load(tmp_path, b"")
    assert note_text(out) == ""
    assert "truncated" not in out


def test_last_line_without_newline(tmp_path):
    note = "".join(f"line {i:02d} ".ljust(99, "x") + "\n" for i in range(29)) + "last".ljust(90, "y")
    assert len(note.encode()) == 2990 and not note.endswith("\n")
    out = run_real_load(tmp_path, note.encode())
    assert note_text(out) == note + "\n"
    assert "truncated" not in out


def test_full_budget_case_fits_without_truncation(tmp_path):
    text = pitfalls(6000)
    out = run_hook(env_for(tmp_path, text, EXIT_LOG, review=ITEM))
    assert len(out.encode()) < BUDGET
    assert REVIEW_LINE in out
    assert "[truncated" not in out
    assert text.rstrip().splitlines()[-1] in out
    assert "--- END PITFALLS ---" in out


def test_exit_log_is_one_status_line_and_kept_as_prev(tmp_path):
    env = env_for(tmp_path, pitfalls(1000), EXIT_LOG)
    out = run_hook(env)
    assert "[last exit] brain: committed · 3 file(s) changed · pushed → main | projects: 9 synced, 7 missing" in out
    assert "syncing /home/u/p0" not in out
    logs = Path(env["HOME"]) / ".claude/logs"
    assert not (logs / "brain-sync-end.log").exists()
    assert (logs / "brain-sync-end.log.prev").read_text() == EXIT_LOG


def test_non_startup_source_leaves_the_exit_log(tmp_path):
    env = env_for(tmp_path, pitfalls(1000), EXIT_LOG)
    out = run_hook(env, source="clear")
    assert "[last exit]" not in out
    assert (Path(env["HOME"]) / ".claude/logs/brain-sync-end.log").exists()


def test_oversized_pitfalls_names_dropped_sections_and_keeps_whole_rules(tmp_path):
    out = run_hook(env_for(tmp_path, pitfalls(12_000), EXIT_LOG))
    assert len(out.encode()) < BUDGET
    note = [line for line in out.splitlines() if line.startswith("[truncated:")]
    assert len(note) == 1 and "sections dropped: Section" in note[0]
    printed = out.split("--- AI-AGENTS PITFALLS (constraints) ---", 1)[1]
    for sec in printed.split("## Section ")[1:]:
        assert sec.count("\n- rule ") == 5  # no section is cut in the middle


def test_huge_project_note_leaves_only_the_pitfalls_note(tmp_path):
    env = env_for(tmp_path, pitfalls(6000), EXIT_LOG)
    big = "\n".join("N" * 300 for _ in range(30))  # 9 KB note: the room for pitfalls drops to 0
    exe(Path(env["AI_DOTFILES"]) / "skills/brain-load/scripts/load.sh", f"cat <<'EOF'\n{big}\nEOF")
    out = run_hook(env)
    printed = out.split("--- AI-AGENTS PITFALLS (constraints) ---\n", 1)[1].split("--- END PITFALLS ---", 1)[0]
    assert printed.splitlines() == [printed.strip()]  # only the one-line note, no rule
    assert "sections dropped: (preamble), Section 0" in printed


def test_review_line_printed_before_pitfalls(tmp_path):
    out = run_hook(env_for(tmp_path, pitfalls(1000), EXIT_LOG, review=ITEM))
    assert out.count(REVIEW_LINE) == 1
    assert out.index(REVIEW_LINE) < out.index("--- AI-AGENTS PITFALLS")


def test_no_review_dir_output_unchanged(tmp_path):
    missing = run_hook(env_for(tmp_path / "a", pitfalls(1000), EXIT_LOG)).replace(str(tmp_path / "a"), "T")
    empty = run_hook(env_for(tmp_path / "b", pitfalls(1000), EXIT_LOG, review="")).replace(str(tmp_path / "b"), "T")
    assert "[review]" not in missing
    assert missing == empty


def test_failing_review_script_adds_no_line_and_logs_stderr(tmp_path):
    env = env_for(tmp_path, pitfalls(1000), EXIT_LOG, review=ITEM)
    script = Path(env["AI_DOTFILES"]) / "scripts/tasks-review.py"
    script.unlink()
    script.write_text("import sys\nprint('boom', file=sys.stderr)\nsys.exit(2)\n")
    out = run_hook(env)
    assert "[review]" not in out and "--- END PITFALLS ---" in out
    assert "boom" in (Path(env["AI_DOTFILES"]) / ".claude/logs/brain-load.log").read_text()


def real_size_pitfalls() -> str:
    """The real vault pitfalls.md is 5,987 B: pad the last section so the fixture matches."""
    base = pitfalls(6000)
    return base + "## Pad\n- " + "p" * (5987 - len(base.encode()) - len("## Pad\n- \n")) + "\n"


def test_pitfalls_outrank_a_big_project_note(tmp_path):
    text = real_size_pitfalls()
    assert len(text.encode()) == 5987
    note = ("".join(f"line {i:02d} ".ljust(59, "x") + "\n" for i in range(51))).encode()  # 3,060 B: over the 3,000 B cap
    out = run_real_load(tmp_path, note, text, EXIT_LOG, ITEM)
    printed = out.split("--- AI-AGENTS PITFALLS (constraints) ---\n", 1)[1].split("--- END PITFALLS ---", 1)[0]
    assert "[truncated" not in printed
    assert printed == text  # every section present
    assert REVIEW_LINE in out
    assert len(out.encode()) <= BUDGET
    assert "note truncated" in out  # the note gave way, not the pitfalls


def test_note_skipped_when_pitfalls_leave_no_room(tmp_path):
    out = run_real_load(tmp_path, b"note line\n" * 20, pitfalls(9000), EXIT_LOG)
    assert "[brain-load] note skipped: no room left for it after pitfalls" in out
    assert "--- PROJECT NOTE" not in out
    assert len(out.encode()) <= BUDGET


def test_missing_note_exits_2_inside_the_hook(tmp_path):
    out = run_real_load(tmp_path, None)
    assert "--- PROJECT NOTE" not in out
    assert "--- END PITFALLS ---" in out


def test_load_rejects_an_unknown_option(tmp_path):
    (tmp_path / "vault/projects").mkdir(parents=True)
    (tmp_path / "brain.env").write_text(f"BRAIN_PATH={tmp_path / 'vault'}\n")
    r = subprocess.run(["bash", str(REPO / "skills/brain-load/scripts/load.sh"), "--max-byte", "3000"],
                       capture_output=True, text=True, env={**uv_env(), "BRAIN_ENV_FILE": str(tmp_path / "brain.env")},
                       cwd=tmp_path)
    assert r.returncode == 64
    assert "usage:" in r.stderr and "--max-bytes" in r.stderr
    assert r.stdout == ""
