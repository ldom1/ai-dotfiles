"""compact-nudge.sh warns once per 100k step past 250k of context, read from the transcript."""
import json
import subprocess
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "compact-nudge.sh"


def transcript(path: Path, context: int) -> Path:
    usage = {"input_tokens": 10, "cache_creation_input_tokens": 0, "cache_read_input_tokens": context - 10,
             "output_tokens": 50}
    lines = [{"type": "user", "message": {"role": "user", "content": "hi"}},
             {"type": "assistant", "message": {"id": "m1", "role": "assistant", "usage": usage}}]
    path.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return path


def run(tmp_path: Path, context: int, session: str = "s1") -> str:
    t = transcript(tmp_path / f"{session}-{context}.jsonl", context)
    event = {"session_id": session, "transcript_path": str(t), "hook_event_name": "Stop"}
    out = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True,
                         check=True, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}).stdout
    return json.loads(out)["systemMessage"] if out.strip() else ""


def test_below_threshold_is_silent(tmp_path):
    assert run(tmp_path, 180_000) == ""


def test_crossing_250k_warns_with_the_size(tmp_path):
    msg = run(tmp_path, 262_000)
    assert "262k" in msg and "/compact" in msg


def test_same_step_warns_only_once(tmp_path):
    assert run(tmp_path, 262_000)
    assert run(tmp_path, 300_000) == ""


def test_next_100k_step_warns_again(tmp_path):
    assert run(tmp_path, 262_000)
    assert run(tmp_path, 351_000)


def test_sessions_are_independent(tmp_path):
    assert run(tmp_path, 262_000, "a")
    assert run(tmp_path, 262_000, "b")


def test_missing_transcript_is_silent(tmp_path):
    event = {"session_id": "x", "transcript_path": str(tmp_path / "nope.jsonl")}
    out = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True,
                         check=True, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}).stdout
    assert out.strip() == ""
