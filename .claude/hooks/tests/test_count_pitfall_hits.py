"""count-pitfall-hits.py: count distinct sessions per pitfall id from '**Pitfall hit:**' lines."""
import subprocess
from datetime import date, timedelta
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "brain-audit" / "scripts" / "count-pitfall-hits.py"
TODAY = date.today()


def day(n: int) -> str:
    return (TODAY - timedelta(days=n)).isoformat()


def log(vault: Path, name: str, *hits: str) -> None:
    f = vault / "inbox/daily/implementation/proj" / f"{name}.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text("## t\n\n" + "".join(f"**Pitfall hit:** {h}\n" for h in hits))


def make_vault(tmp_path: Path) -> Path:
    ops = tmp_path / "resources/operational/ai-agents"
    ops.mkdir(parents=True)
    (ops / "pitfalls.md").write_text(
        "## Verification\n- Verify the effect. ^v1\n- Read the skip count. ^v3\n"
        "## Git\n- Pin the branch. ^g2\n\n## Retired ids\n^v2→^v1 ^g4→^g2\n"
    )
    pat = tmp_path / "resources/knowledge/patterns"
    pat.mkdir(parents=True)
    (pat / "git-patterns.md").write_text("## Rules\n- Squash merge. ^g6\n")
    log(tmp_path, f"{day(1)}-a", "[[pitfalls#^v1]]", "[[pitfalls#^v3]]")
    log(tmp_path, f"{day(2)}-b", "[[pitfalls#^v2]]", "[[git-patterns#^g6]]")  # ^v2 retired -> ^v1
    log(tmp_path, f"{day(3)}-c", "[[pitfalls#^v3]]", "[[pitfalls#^v3]]")  # repeat in one session counts once
    log(tmp_path, f"{day(60)}-old", "[[pitfalls#^g6]]", "[[git-patterns#^g6]]")  # outside the window
    return tmp_path


def run(vault: Path, *args: str) -> str:
    return subprocess.run(["python3", str(SCRIPT), str(vault), *args], capture_output=True, text=True, check=True).stdout


def test_two_shared_ids_are_candidates_and_retired_id_maps_to_current(tmp_path):
    out = run(make_vault(tmp_path))
    assert f"^v1 2 sessions: {day(2)}-b, {day(1)}-a" in out
    assert f"^v3 2 sessions: {day(3)}-c, {day(1)}-a" in out
    assert "^g6 1 session" in out and "candidate" not in out.split("^g6")[1].splitlines()[0]
    assert "^v2" not in out
    assert out.strip().endswith("2 candidates")


def test_log_outside_window_is_ignored(tmp_path):
    vault = make_vault(tmp_path)
    assert "^g6 1 session" in run(vault)  # the old log would make it 2
    assert "^g6 2 sessions" in run(vault, "--days", "90")


def test_existing_draft_and_sensor_suffix_are_skipped(tmp_path):
    vault = make_vault(tmp_path)
    (vault / "inbox/sensors").mkdir(parents=True)
    (vault / "inbox/sensors/2026-10-01-verify.md").write_text("---\npitfall: ^v1\n---\n")
    p = vault / "resources/operational/ai-agents/pitfalls.md"
    p.write_text(p.read_text().replace("Read the skip count. ^v3", "Read the skip count. (sensor: skip-check) ^v3"))
    out = run(vault)
    assert "^v1 2 sessions" in out and "skip: draft exists" in out
    assert "skip: has sensor" in out
    assert out.strip().endswith("0 candidates")


def test_no_hit_lines_reports_zero_candidates(tmp_path):
    (tmp_path / "inbox/daily/implementation/proj").mkdir(parents=True)
    assert run(tmp_path).strip().endswith("0 candidates")
