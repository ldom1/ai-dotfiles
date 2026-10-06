"""scripts/vibe-claude-hook.py runs a Claude Code hook as a Vibe hook. Only exact refusal shapes become a deny."""
import json
import os
import shutil
import subprocess
import tomllib
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
ADAPTER = REPO / "scripts" / "vibe-claude-hook.py"
HOOKS = REPO / ".claude" / "hooks"
ENV_PATH = "/usr/bin:/bin"


def pre_tool(cwd: Path, command: str) -> dict:
    return {"hook_event_name": "pre_tool", "session_id": "s", "parent_session_id": None, "transcript_path": "/t",
            "cwd": str(cwd), "tool_name": "bash", "tool_call_id": "c1", "tool_input": {"command": command, "timeout": None}}


def post_agent(cwd: Path) -> dict:
    return {"hook_event_name": "post_agent", "session_id": "s", "parent_session_id": None, "transcript_path": "/t",
            "cwd": str(cwd)}


def adapt(hook: Path, event: dict, tmp_path: Path) -> subprocess.CompletedProcess:
    return subprocess.run(["python3", str(ADAPTER), str(hook)], input=json.dumps(event), cwd=event["cwd"],
                          capture_output=True, text=True, env={"PATH": ENV_PATH, "HOME": str(tmp_path)})


def decision(r: subprocess.CompletedProcess) -> dict:
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout) if r.stdout.strip() else {}


def make_repo(path: Path, check: str) -> Path:
    path.mkdir(parents=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    (path / ".claude").mkdir()
    (path / ".claude" / "stop-check").write_text(check + "\n")
    (path / "x.py").write_text("x = 1\n")
    return path


# Real hooks

def test_bad_commit_message_is_denied(tmp_path):
    out = decision(adapt(HOOKS / "git-commit-check.sh", pre_tool(tmp_path, 'git commit -m "bad message"'), tmp_path))
    assert out["decision"] == "deny"
    assert "Commit message format invalid" in out["reason"]


def test_good_commit_message_passes(tmp_path):
    assert decision(adapt(HOOKS / "git-commit-check.sh", pre_tool(tmp_path, 'git commit -m "fix(x): y"'), tmp_path)) == {}


def test_tier1_command_is_denied(tmp_path):
    out = decision(adapt(HOOKS / "hardline-check.py", pre_tool(tmp_path, "rm -rf ~"), tmp_path))
    assert out["decision"] == "deny"
    assert out["reason"].startswith("hardline-check ")


def test_tier2_command_needs_confirmation(tmp_path):
    out = decision(adapt(HOOKS / "hardline-check.py", pre_tool(tmp_path, "git push --force origin main"), tmp_path))
    assert out["decision"] == "deny"
    assert out["reason"].startswith("needs confirmation: hardline-check ")
    assert out["reason"].endswith(". Ask the user to run it.")


def test_failing_stop_check_is_denied_without_its_tag(tmp_path):
    repo = make_repo(tmp_path / "p", "echo 'E501 line too long'; exit 1")
    out = decision(adapt(HOOKS / "stop-check.sh", post_agent(repo), tmp_path))
    assert out["decision"] == "deny"
    assert "E501 line too long" in out["reason"]
    assert not out["reason"].startswith("[stop-check]")


def test_passing_stop_check_is_silent(tmp_path):
    repo = make_repo(tmp_path / "p", "true")
    assert decision(adapt(HOOKS / "stop-check.sh", post_agent(repo), tmp_path)) == {}


# Stub hooks: one case per mapping row and per error path

def stub(tmp_path: Path, stdout: str = "", rc: int = 0, stderr: str = "") -> Path:
    (tmp_path / "out.txt").write_text(stdout)
    (tmp_path / "err.txt").write_text(stderr)
    hook = tmp_path / "hook.sh"
    hook.write_text(f"#!/bin/bash\ncat > {tmp_path}/stdin.json\ncat {tmp_path}/out.txt\ncat {tmp_path}/err.txt >&2\nexit {rc}\n")
    hook.chmod(0o755)
    return hook


def pre_tool_output(d: str, reason: str) -> str:
    return json.dumps({"hookSpecificOutput": {"hookEventName": "PreToolUse", "permissionDecision": d,
                                              "permissionDecisionReason": reason}})


MAPPING = [
    (json.dumps({"decision": "block", "reason": "[stop-check] tests fail"}), {"decision": "deny", "reason": "tests fail"}),
    (pre_tool_output("deny", "no"), {"decision": "deny", "reason": "no"}),
    (pre_tool_output("ask", "risky."), {"decision": "deny", "reason": "needs confirmation: risky. Ask the user to run it."}),
    ("", {}),
    (pre_tool_output("allow", "reminder"), {}),
    (json.dumps({"systemMessage": "note"}), {"system_message": "note"}),
]


@pytest.mark.parametrize("stdout,expected", MAPPING)
def test_mapping_row(stdout, expected, tmp_path):
    assert decision(adapt(stub(tmp_path, stdout), pre_tool(tmp_path, "ls"), tmp_path)) == expected


def test_event_is_claude_shaped(tmp_path):
    adapt(stub(tmp_path), pre_tool(tmp_path, "ls"), tmp_path)
    event = json.loads((tmp_path / "stdin.json").read_text())
    assert event["tool_name"] == "Bash"
    assert event["stop_hook_active"] is False
    assert event["tool_input"]["command"] == "ls"


def test_exit_2_is_deny_with_stderr(tmp_path):
    out = decision(adapt(stub(tmp_path, rc=2, stderr="blocked by rule"), pre_tool(tmp_path, "ls"), tmp_path))
    assert out == {"decision": "deny", "reason": "blocked by rule"}


@pytest.mark.parametrize("stdout,rc", [
    (json.dumps({"foo": 1}), 0),
    (json.dumps({"decision": "block"}), 0),
    (json.dumps({"hookSpecificOutput": {"permissionDecision": "maybe"}}), 0),
    (json.dumps(["deny"]), 0),
    ("not json {", 0),
    ("", 1),
    (pre_tool_output("deny", "no"), 1),
])
def test_anything_else_is_an_adapter_error(stdout, rc, tmp_path):
    r = adapt(stub(tmp_path, stdout, rc=rc, stderr="boom"), pre_tool(tmp_path, "ls"), tmp_path)
    assert r.returncode == 1
    assert r.stdout == ""
    assert r.stderr.startswith("vibe-claude-hook:")


def test_missing_hook_is_an_adapter_error(tmp_path):
    r = adapt(tmp_path / "nope.sh", pre_tool(tmp_path, "ls"), tmp_path)
    assert (r.returncode, r.stdout) == (1, "")
    assert "nope.sh" in r.stderr


def test_timeout_message_becomes_system_message(tmp_path):
    out = decision(adapt(stub(tmp_path, json.dumps({"systemMessage": "[stop-check] timed out"})), post_agent(tmp_path),
                         tmp_path))
    assert out == {"system_message": "[stop-check] timed out"}


# The shipped hooks file. Named user-hooks.toml: a repo .vibe/hooks.toml would load twice in this
# trusted repo (project file + ~/.vibe/hooks.toml link), and Vibe reports each duplicate name.

USER_HOOKS = REPO / ".vibe" / "user-hooks.toml"


def test_hooks_toml_wires_the_three_sensors():
    hooks = {h["name"]: h for h in tomllib.loads(USER_HOOKS.read_text())["hooks"]}
    assert set(hooks) == {"hardline", "commit-scope", "stop-check"}
    for name, script in [("hardline", "hardline-check.py"), ("commit-scope", "git-commit-check.sh")]:
        assert hooks[name]["type"] == "pre_tool" and hooks[name]["match"] == "bash" and hooks[name]["strict"] is True
        assert hooks[name]["command"].endswith(f"vibe-claude-hook.py ~/ai-dotfiles/.claude/hooks/{script}")
    assert hooks["stop-check"]["type"] == "post_agent" and hooks["stop-check"]["timeout"] == 180.0
    assert hooks["stop-check"]["command"].endswith("vibe-claude-hook.py ~/ai-dotfiles/.claude/hooks/stop-check.sh")
    assert list(hooks) == ["hardline", "commit-scope", "stop-check"]  # hardline runs first
    assert not (REPO / ".vibe" / "hooks.toml").exists()


def test_install_links_user_hooks_toml(tmp_path):
    d, home = tmp_path / "dotfiles", tmp_path / "home"
    (d / "scripts").mkdir(parents=True)
    home.mkdir()
    shutil.copy(REPO / "scripts" / "install.sh", d / "scripts" / "install.sh")
    (d / "scripts" / "build-agent-rules.sh").write_text("true\n")
    (d / "scripts" / "merge-settings.py").write_text("raise SystemExit(7)\n")  # stops install.sh after step 1c
    r = subprocess.run(["bash", str(d / "scripts" / "install.sh")], capture_output=True, text=True,
                       env={"PATH": ENV_PATH, "HOME": str(home)})
    assert r.returncode == 7, r.stdout + r.stderr
    assert os.readlink(home / ".vibe" / "hooks.toml") == str(d / ".vibe" / "user-hooks.toml")
