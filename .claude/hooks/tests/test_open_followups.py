"""open-followups.sh: list open follow-ups from recent session logs."""
import os
import subprocess
import time
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "brain-audit" / "scripts" / "open-followups.sh"


def log(vault: Path, name: str, body: str, age_days: int = 1) -> Path:
    f = vault / "inbox/daily/implementation/proj" / f"{name}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(body)
    t = time.time() - age_days * 86400
    os.utime(f, (t, t))
    return f


def run(vault: Path, **env: str) -> str:
    base = {k: v for k, v in os.environ.items() if k != "BRAIN_AUDIT_LOOKBACK_DAYS"}
    return subprocess.run(
        ["bash", str(SCRIPT)], capture_output=True, text=True, check=True,
        env={**base, "BRAIN_PATH": str(vault), **env},
    ).stdout


def test_inline_followup_listed(tmp_path):
    log(tmp_path, "a", "## t\n\n**Follow-ups:** wire the guard\n**Next:** x\n")
    out = run(tmp_path)
    assert "=== inbox/daily/implementation/proj/a.md" in out
    assert "wire the guard" in out


@pytest.mark.parametrize("word", ["none", "None.", "Aucun.", "aucun", "(none)", "(None).", "n/a", "N/A."])
def test_inline_none_skipped(tmp_path, word):
    log(tmp_path, "a", f"## t\n\n**Follow-ups:** {word}\n")
    assert run(tmp_path).strip() == ""


def test_list_under_header_listed(tmp_path):
    log(tmp_path, "a", "## Follow-ups\n- a\n- b\n## Other\n- c\n")
    out = run(tmp_path)
    assert "- a" in out and "- b" in out
    assert "- c" not in out


def test_lookback_env(tmp_path):
    log(tmp_path, "old", "**Follow-ups:** old item\n", age_days=40)
    assert "old item" not in run(tmp_path)
    assert "old item" in run(tmp_path, BRAIN_AUDIT_LOOKBACK_DAYS="45")
