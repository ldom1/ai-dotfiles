"""SessionEnd appends the harness-metrics line before the vault sync and never blocks the sync.
SessionStart exports CLAUDE_SESSION_ID. Dependencies (sync, usage log) are stubs."""
import json
import shutil
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
END = REPO / ".claude" / "hooks" / "brain-session-end.sh"
START = REPO / ".claude" / "hooks" / "brain-session-start.sh"
FIXTURE = Path(__file__).parent / "fixtures" / "harness-metrics" / "session.jsonl"


def exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body + "\n")
    path.chmod(0o755)


def setup(tmp_path: Path, metrics_stub: str | None = None) -> dict:
    dot, vault, home = tmp_path / "dot", tmp_path / "vault", tmp_path / "home"
    home.mkdir()
    vault.mkdir()
    exe(dot / "skills/brain-sync/scripts/sync.sh", f"echo synced > '{tmp_path}/marker'")
    exe(dot / "scripts/log-skill-usage.sh", "exit 0")
    script = dot / "scripts/harness-metrics.py"
    if metrics_stub is None:
        shutil.copy(REPO / "scripts/harness-metrics.py", script)
    else:
        script.write_text(metrics_stub)
    env_file = tmp_path / "brain.env"
    env_file.write_text(f"BRAIN_PATH={vault}\n")
    return {"PATH": "/usr/bin:/bin", "HOME": str(home), "AI_DOTFILES": str(dot), "BRAIN_ENV_FILE": str(env_file)}


def run_end(env: dict, payload: dict | str) -> subprocess.CompletedProcess:
    stdin = payload if isinstance(payload, str) else json.dumps(payload)
    return subprocess.run(["bash", str(END)], input=stdin, capture_output=True, text=True, env=env)


def lines(tmp_path: Path) -> list:
    return [json.loads(x) for f in (tmp_path / "vault/meta/harness-sessions").glob("*.jsonl") for x in f.read_text().splitlines()]


def test_appends_line_then_syncs(tmp_path):
    env = setup(tmp_path)
    tp = tmp_path / "t.jsonl"
    shutil.copy(FIXTURE, tp)
    r = run_end(env, {"session_id": "s1", "transcript_path": str(tp), "reason": "prompt_input_exit"})
    assert r.returncode == 0
    recs = lines(tmp_path)
    assert len(recs) == 1 and recs[0]["reason"] == "prompt_input_exit"
    assert (tmp_path / "marker").exists()


def test_metrics_failure_keeps_sync(tmp_path):
    env = setup(tmp_path, metrics_stub="import sys\nprint('boom', file=sys.stderr)\nsys.exit(1)\n")
    tp = tmp_path / "t.jsonl"
    shutil.copy(FIXTURE, tp)
    r = run_end(env, {"session_id": "s1", "transcript_path": str(tp), "reason": "other"})
    assert r.returncode == 0
    assert (tmp_path / "marker").exists()
    assert "boom" in (Path(env["HOME"]) / ".claude/logs/harness-metrics.log").read_text()
    assert "boom" not in r.stdout


def test_subagent_transcript_skipped(tmp_path):
    env = setup(tmp_path)
    sub = tmp_path / "x/subagents/agent-1.jsonl"
    sub.parent.mkdir(parents=True)
    shutil.copy(FIXTURE, sub)
    r = run_end(env, {"session_id": "s1", "transcript_path": str(sub), "reason": "other"})
    assert r.returncode == 0 and lines(tmp_path) == []
    assert (tmp_path / "marker").exists()


def test_no_transcript_path(tmp_path):
    env = setup(tmp_path)
    r = run_end(env, "{}")
    assert r.returncode == 0 and lines(tmp_path) == []
    assert (tmp_path / "marker").exists()
    assert not (Path(env["HOME"]) / ".claude/logs/harness-metrics.log").exists()


def test_session_start_exports_id(tmp_path):
    env = setup(tmp_path)
    exe(Path(env["AI_DOTFILES"]) / "skills/brain-load/scripts/load.sh", "exit 0")
    env_out = tmp_path / "claude-env"
    env |= {"CLAUDE_ENV_FILE": str(env_out), "BRAIN_LOAD_SLIM": "1"}
    r = subprocess.run(["bash", str(START)], input='{"session_id":"abc","source":"startup"}',
                       capture_output=True, text=True, env=env)
    assert r.returncode == 0
    assert "export CLAUDE_SESSION_ID=abc\n" in env_out.read_text()
