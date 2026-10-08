"""The template wires the local-ci merge guard and denies `git push --no-verify` to Claude."""
import json
from pathlib import Path

TPL = Path(__file__).resolve().parents[2] / "settings.json.tpl"


def test_template_denies_no_verify_push():
    deny = json.loads(TPL.read_text())["permissions"]["deny"]
    assert "Bash(git push --no-verify*)" in deny
    assert "Bash(git push * --no-verify*)" in deny


def test_template_runs_the_merge_guard_on_bash():
    pre = json.loads(TPL.read_text())["hooks"]["PreToolUse"]
    cmds = [h["command"] for g in pre if g.get("matcher") == "Bash" for h in g["hooks"]]
    assert "__HOME__/.claude/hooks/local-ci-merge-guard.py" in cmds


def test_template_denies_hook_bypasses_through_git_options():
    deny = json.loads(TPL.read_text())["permissions"]["deny"]
    assert "Bash(git -C * push*--no-verify*)" in deny
    assert "Bash(git -c core.hooksPath*)" in deny
