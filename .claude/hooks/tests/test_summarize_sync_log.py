"""summarize-sync-log.py: brain-sync-end.log → one [last exit] line + at most 5 notable lines."""
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "summarize-sync-log.py"
E = "\x1b"
LOG = (
    f"{E}[1m{E}[0;36m━━━ brain-sync · session end · 2026-10-06T14:26:49 ━━━{E}[0m\n\n"
    f"{E}[0;36m▸{E}[0m projects   syncing project brains (project → vault)…\n"
    "[sync-project] s3-explorer: syncing /a/.claude/memory ↔ /v/projects/s3-explorer\n"
    "[sync-project] s3-explorer: done.\n"
    "[sync-project] prosper: done.\n"
    "[sync-project] WARNING: /home/u/lab/scrimmo does not exist, skipping.\n"
    "[sync-project] WARNING: /home/u/lab/legal_tech does not exist, skipping.\n"
    f"{E}[0;32m✓{E}[0m brain      committed · 3 file(s) changed\n"
    f"{E}[0;32m✓{E}[0m brain      pushed → main\n"
)


def run(tmp_path: Path, text: str | None) -> list[str]:
    log = tmp_path / "brain-sync-end.log"
    if text is not None:
        log.write_text(text)
    out = subprocess.run(["python3", str(SCRIPT), str(log)], capture_output=True, text=True, check=True).stdout
    assert E not in out
    return out.splitlines()


def test_normal_exit_is_one_line(tmp_path):
    assert run(tmp_path, LOG) == [
        "[last exit] brain: committed · 3 file(s) changed · pushed → main"
        " | projects: 2 synced, 2 missing (scrimmo, legal_tech)"
    ]


def test_push_failure_is_in_the_status(tmp_path):
    log = LOG.replace("✓\x1b[0m brain      pushed → main", "✗\x1b[0m brain      push failed (remote rejected or no network)")
    assert "brain: committed · 3 file(s) changed · push failed (remote rejected or no network)" in run(tmp_path, log)[0]


def test_log_without_vault_line_says_so(tmp_path):
    assert run(tmp_path, "[sync-project] prosper: done.\n")[0] == (
        "[last exit] brain: no status line (sync did not finish?) | projects: 1 synced"
    )


def test_missing_notes_warning_is_kept(tmp_path):
    log = LOG + "\n⚠️  [brain-session-end] No implementation notes found for 2026-10-06\n    Next session: run /capture\n"
    assert run(tmp_path, log)[1:] == ["⚠️  [brain-session-end] No implementation notes found for 2026-10-06"]


def test_notable_lines_are_capped_at_five(tmp_path):
    log = LOG + "".join(f"⚠ projects   step {i} failed\n" for i in range(8))
    out = run(tmp_path, log)
    assert len(out) == 7
    assert out[-1] == "(+3 more: ~/.claude/logs/brain-sync-end.log.prev)"


def test_missing_log_prints_nothing(tmp_path):
    assert run(tmp_path, None) == []
