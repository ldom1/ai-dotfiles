"""run-cursor.sh: Cursor runs in a container that mounts only the run dir, gets no GitHub credentials, gets the API key
by name only; pins the model, stops on a usage limit (no fallback), times out hangs, resumes by session id."""
import json
import os
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "skills" / "implement-with-cursor-agent" / "scripts" / "run-cursor.sh"
KEY = "test-key-123"

FAKE_DOCKER = """#!/usr/bin/env bash
if [ "$1" = rm ]; then echo "rm $*" >> "$CALLS"; exit 0; fi
printf '%s\\n' "KEY=${CURSOR_API_KEY:-}" "$@" > "$CALLS.args.$(date +%s%N)"
echo "run $*" >> "$CALLS"
case "$*" in
  *"--model limited"*) echo "Error: You've hit your usage limit for this model" >&2; exit 1 ;;
  *"--model broken"*) echo "Error: workspace not found" >&2; exit 1 ;;
  *"--model slow"*) sleep 5 ;;
esac
echo '{"type":"result","session_id":"s-123","result":"STATUS=done"}'
"""


def run_script(tmp_path: Path, model: str, *extra: str, timeout: str = "30", key: str | None = KEY):
    bin_dir = tmp_path / "bin"
    if not bin_dir.exists():
        bin_dir.mkdir()
        for name, body in (("docker", FAKE_DOCKER), ("agent", "#!/bin/sh\n"), ("uv", "#!/bin/sh\n")):
            (bin_dir / name).write_text(body)
            (bin_dir / name).chmod(0o755)
        (tmp_path / "run").mkdir()
        (tmp_path / "prompt.md").write_text("do task 1")
    env = {k: v for k, v in os.environ.items() if k != "CURSOR_API_KEY"}
    env.update(PATH=f"{bin_dir}:{os.environ['PATH']}", CALLS=str(tmp_path / "calls"), CURSOR_MODEL=model,
               CURSOR_TIMEOUT=timeout, CURSOR_API_KEY_FILE=str(tmp_path / "no-such-key-file"))
    if key is not None:
        env["CURSOR_API_KEY"] = key
    return subprocess.run(["bash", str(SCRIPT), str(tmp_path / "run"), str(tmp_path / "prompt.md"), *extra],
                          env=env, capture_output=True, text=True)


def calls(tmp_path: Path) -> list[str]:
    return (tmp_path / "calls").read_text().splitlines()


def last_args(tmp_path: Path) -> list[str]:
    files = sorted(tmp_path.glob("calls.args.*"))
    return files[-1].read_text().splitlines()


def test_container_sees_only_the_run_dir_and_gets_key_by_name(tmp_path):
    r = run_script(tmp_path, "")  # empty CURSOR_MODEL -> script default
    assert r.returncode == 0, r.stderr
    args = last_args(tmp_path)
    assert args[0] == f"KEY={KEY}"  # the key reaches docker through the environment
    assert KEY not in "\n".join(args[1:])  # and never through its arguments
    mounts = [args[i + 1] for i, a in enumerate(args) if a == "-v"]
    run = str((tmp_path / "run").resolve())
    assert [m for m in mounts if not m.endswith(":ro")] == [f"{run}:/work"]
    assert not any(m.split(":")[0] == os.environ["HOME"] for m in mounts)
    assert "-e" in args and "CURSOR_API_KEY" in args and "BRAIN_AGENT_HOOKS=0" in args
    assert not any("GH_TOKEN" in a or "GITHUB_TOKEN" in a or ".config/gh" in a for a in args)
    assert args[args.index("--model") + 1] == "gpt-5.3-codex"
    assert args[args.index("--workspace") + 1] == "/work/project"
    assert json.loads((tmp_path / "run" / "result-0.json").read_text())["session_id"] == "s-123"


def test_missing_key_stops_before_docker(tmp_path):
    r = run_script(tmp_path, "composer-2.5", key=None)
    assert r.returncode == 4
    assert "no Cursor API key" in r.stderr
    assert not (tmp_path / "calls").exists()


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


def test_hang_times_out_and_removes_the_container(tmp_path):
    r = run_script(tmp_path, "slow", timeout="1")
    assert r.returncode == 124
    assert any(c.startswith("rm rm -f cursor-run-0-") for c in calls(tmp_path))
    assert "rc=124" in (tmp_path / "run" / "runs.log").read_text()


def test_resume_uses_previous_session_id(tmp_path):
    assert run_script(tmp_path, "composer-2.5").returncode == 0
    assert run_script(tmp_path, "composer-2.5", "resume").returncode == 0
    args = last_args(tmp_path)
    assert args[args.index("--resume") + 1] == "s-123"
    assert (tmp_path / "run" / "result-1.json").exists()
