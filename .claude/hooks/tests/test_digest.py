"""digest.sh: resets the maintenance clock and writes nothing else."""
import re
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "brain-audit" / "scripts" / "digest.sh"


def run_digest(tmp_path: Path, *args: str) -> tuple[subprocess.CompletedProcess, Path]:
    vault = tmp_path / "vault"
    (vault / ".git").mkdir(parents=True)
    env_file = tmp_path / "brain.env"
    env_file.write_text(f"BRAIN_PATH={vault}\n")
    r = subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env={"PATH": "/usr/bin:/bin", "BRAIN_ENV_FILE": str(env_file)},
    )
    return r, vault


def test_digest_writes_only_the_clock(tmp_path):
    r, vault = run_digest(tmp_path, "2", "3", "1")
    assert r.returncode == 0, r.stderr
    clock = (vault / "meta" / "last-maintenance.md").read_text()
    assert re.search(r"^\*\*Epoch Seconds:\*\* \d+$", clock, re.M)
    assert not (vault / "resources").exists()
    written = {p.relative_to(vault).as_posix() for p in vault.rglob("*") if p.is_file()}
    assert written == {"meta/last-maintenance.md"}
    for text in ("Committed", "✅", "connect", "check-pitfalls-budget"):
        assert text not in r.stdout, r.stdout


def test_clock_format_feeds_the_session_start_nudge(tmp_path):
    # Same extraction as .claude/hooks/brain-session-start.sh (maintenance nudge).
    _, vault = run_digest(tmp_path)
    r = subprocess.run(
        ["grep", "-oP", r"\*\*Epoch Seconds:\*\* \K[0-9]+", str(vault / "meta" / "last-maintenance.md")],
        capture_output=True,
        text=True,
    )
    assert r.stdout.strip().isdigit()
