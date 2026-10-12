"""run-cursor.sh: pins the model, stops on a usage limit (no fallback), times out hangs, keeps brain hooks off, resumes by session id."""
import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "implement-with-cursor-agent" / "scripts" / "run-cursor.sh"

FAKE_AGENT = """#!/usr/bin/env bash
echo "$BRAIN_AGENT_HOOKS $*" >> "$CALLS"
case "$*" in
  *"--model limited"*) echo "Error: You've hit your usage limit for this model" >&2; exit 1 ;;
  *"--model broken"*) echo "Error: workspace not found" >&2; exit 1 ;;
  *"--model slow"*) sleep 5 ;;
esac
echo '{"type":"result","session_id":"s-123","result":"PROJECT_PR=x"}'
"""


def run_script(tmp_path: Path, model: str, *extra: str, timeout: str = "30") -> subprocess.CompletedProcess:
    bin_dir = tmp_path / "bin"
    if not bin_dir.exists():
        bin_dir.mkdir()
        (bin_dir / "agent").write_text(FAKE_AGENT)
        (bin_dir / "agent").chmod(0o755)
        (tmp_path / "run").mkdir()
        (tmp_path / "prompt.md").write_text("do task 1")
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}", "CALLS": str(tmp_path / "calls"),
           "CURSOR_MODEL": model, "CURSOR_TIMEOUT": timeout}
    return subprocess.run(["bash", str(SCRIPT), str(tmp_path / "run"), str(tmp_path / "prompt.md"), *extra],
                          env=env, capture_output=True, text=True)


def calls(tmp_path: Path) -> list[str]:
    return (tmp_path / "calls").read_text().splitlines()


def test_default_model_and_hooks_off(tmp_path):
    env_model = run_script(tmp_path, "")  # empty CURSOR_MODEL -> script default
    assert env_model.returncode == 0, env_model.stderr
    assert " --model gpt-5.3-codex " in calls(tmp_path)[0]
    assert calls(tmp_path)[0].startswith("0 ")  # BRAIN_AGENT_HOOKS=0
    assert json.loads((tmp_path / "run" / "result-0.json").read_text())["session_id"] == "s-123"


def test_usage_limit_stops_without_fallback(tmp_path):
    r = run_script(tmp_path, "limited")
    assert r.returncode == 75
    assert "usage limit on limited" in r.stderr
    assert len(calls(tmp_path)) == 1  # no retry on another model
    assert "rc=75 model=limited" in (tmp_path / "run" / "runs.log").read_text()


def test_other_errors_keep_their_code(tmp_path):
    r = run_script(tmp_path, "broken")
    assert r.returncode == 1
    assert len(calls(tmp_path)) == 1


def test_hang_times_out_with_124(tmp_path):
    r = run_script(tmp_path, "slow", timeout="1")
    assert r.returncode == 124
    assert "rc=124" in (tmp_path / "run" / "runs.log").read_text()


def test_resume_uses_previous_session_id(tmp_path):
    assert run_script(tmp_path, "composer-2.5").returncode == 0
    assert run_script(tmp_path, "composer-2.5", "resume").returncode == 0
    assert "--resume s-123" in calls(tmp_path)[-1]
    assert (tmp_path / "run" / "result-1.json").exists()
