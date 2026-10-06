"""replay-bash-rules.py replays past Bash calls through hardline-check's classify() and the template ask list."""
import json
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "replay-bash-rules.py"


def line(tool_id: str, command: str, ts: str) -> str:
    block = {"type": "tool_use", "id": tool_id, "name": "Bash", "input": {"command": command}}
    return json.dumps({"type": "assistant", "timestamp": ts, "message": {"content": [block]}}) + "\n"


def test_counts_dedupes_and_lists_every_prompt(tmp_path):
    now = datetime.now(timezone.utc)
    today, old = now.strftime("%Y-%m-%dT%H:%M:%S.000Z"), (now - timedelta(days=30)).strftime("%Y-%m-%dT%H:%M:%SZ")
    proj = tmp_path / ".claude" / "projects" / "-p"
    (proj / "s1" / "subagents").mkdir(parents=True)
    (proj / "s1.jsonl").write_text(
        line("a", "rm -rf $DIR", today) * 2  # one call streamed on two lines
        + line("b", "ansible-playbook site.yml", today)
        + line("c", "ls", today)
        + line("d", "git push -f origin main", old)  # outside --days 14
        + json.dumps({"type": "user", "timestamp": today, "message": {"content": "hi"}}) + "\n")
    (proj / "s1" / "subagents" / "agent-x.jsonl").write_text(line("e", "git clean -fdx", today))
    out = subprocess.run(["python3", str(SCRIPT), "--days", "14"], capture_output=True, text=True, check=True,
                         env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)}).stdout
    assert "| Bash calls | 3 | 1 |" in out
    assert "| Prompts | 2 | 1 |" in out
    assert "| Active days | 1 | - |" in out
    assert "| settings:ansible-playbook * | 1 | 0 |" in out
    assert "| rm-recursive-force-root-dynamic | 1 | 0 |" in out
    assert f"| {now.date()} | subagent | s1 | ask | git-clean-untracked | git clean -fdx |  |" in out
    assert "git push" not in out
