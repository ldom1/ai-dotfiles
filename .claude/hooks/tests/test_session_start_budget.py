"""brain-session-start.sh keeps its whole output under the 9,500 B budget and drops no pitfalls rule silently.

Dependencies of the hook (sync, load, vendored check) are stubs with realistic output sizes
(measured 2026-10-06: project note 2,099 B, vendored warnings 375 B).
"""
import json
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


def env_for(tmp_path: Path, pitfalls_text: str, exit_log: str | None) -> dict:
    dot, vault, home = tmp_path / "dot", tmp_path / "vault", tmp_path / "home"
    exe(dot / "skills/brain-sync/scripts/sync.sh", "exit 0")
    note = "\n".join(f"note line {i:02d} " + "n" * 56 for i in range(30))
    exe(dot / "skills/brain-load/scripts/load.sh", f"cat <<'EOF'\n{note}\nEOF")
    exe(dot / "scripts/log-skill-usage.sh", "exit 0")
    exe(dot / "scripts/check-vendored-skill-updates.sh", "printf 'w%.0s' {1..374}; echo")
    for name in ("summarize-sync-log.py", "fit-sections.py"):
        (dot / "scripts" / name).symlink_to(REPO / "scripts" / name)
    (dot / "config").mkdir()
    (dot / "config" / "brain.env").write_text(f"BRAIN_PATH={vault}\n")
    p = vault / "resources/operational/ai-agents/pitfalls.md"
    p.parent.mkdir(parents=True)
    p.write_text(pitfalls_text)
    if exit_log is not None:
        log = home / ".claude/logs/brain-sync-end.log"
        log.parent.mkdir(parents=True)
        log.write_text(exit_log)
    return {"PATH": "/usr/bin:/bin", "HOME": str(home), "AI_DOTFILES": str(dot)}


def run_hook(env: dict, source: str = "startup") -> str:
    return subprocess.run(["bash", str(HOOK)], input=json.dumps({"source": source}), capture_output=True,
                          text=True, check=True, env=env).stdout


def test_full_budget_case_fits_without_truncation(tmp_path):
    text = pitfalls(6000)
    out = run_hook(env_for(tmp_path, text, EXIT_LOG))
    assert len(out.encode()) < BUDGET
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
