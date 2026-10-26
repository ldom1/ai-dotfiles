"""harness-metrics.py: session transcript -> one record; append replaces the line per session id."""
import importlib.util
import json
import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "harness-metrics.py"
FIXTURE = Path(__file__).parent / "fixtures" / "harness-metrics" / "session.jsonl"
REPO, VAULT = "/home/u/ai-dotfiles", "/home/u/brain"

spec = importlib.util.spec_from_file_location("harness_metrics", SCRIPT)
hm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(hm)


@pytest.fixture(autouse=True)
def roots(monkeypatch):
    monkeypatch.setenv("AI_DOTFILES", REPO)
    monkeypatch.setenv("BRAIN_PATH", VAULT)


def use(name, n=0, **inp):
    return {"type": "assistant", "sessionId": "sid-1", "timestamp": "2026-10-20T10:00:00Z", "cwd": "/home/u/proj",
            "message": {"id": f"m{n}", "content": [{"type": "tool_use", "id": f"t{n}", "name": name, "input": inp}]}}


def refusal(text):
    return {"type": "user", "message": {"content": [{"type": "tool_result", "is_error": True, "content": text}]}}


def transcript(tmp_path, *records, name="sid-1"):
    path = tmp_path / f"{name}.jsonl"
    path.write_text("".join(json.dumps(r) + "\n" for r in records))
    return path


def test_counts_from_real_fixture():
    rec = hm.parse_session(FIXTURE)
    assert rec["session_id"] == "16b04768-1bfb-4120-9057-8e6dc9c6dab7"
    assert (rec["project"], rec["tool"], rec["reason"]) == ("proj", "claude-code", None)
    assert sum(rec["skills"].values()) == 8 and rec["skills"]["git-promotion"] == 1
    assert rec["mcp"] == {"qmd": 2}
    assert rec["agents"] == {"general-purpose": 24, "reviewer": 7}
    assert rec["hook_refusals"] == {"merge-guard": 2}
    assert rec["permission_refusals"] == 2
    assert rec["user_turns"] == 58
    assert rec["tools"]["Bash"] == 155
    assert rec["duration_s"] == 94038 and rec["cost_usd"] == pytest.approx(39.1399, abs=1e-3)
    assert rec["tokens"]["claude-opus-5-5"] == 23078 + 170031
    assert rec["captured"] is True  # the session wrote an implementation log
    assert rec["rules_added"] == ["g17"]
    assert "resources/knowledge/patterns/git-patterns.md" in rec["harness_edits"]
    assert rec["metrics_status"] == "partial"  # the fixture ends with a truncated line
    assert set(rec) == {"session_id", "date", "project", "host", "tool", "duration_s", "user_turns", "cost_usd",
                        "tokens", "skills", "mcp", "agents", "tools", "subagent_tools", "hook_refusals",
                        "permission_refusals", "captured", "harness_edits", "rules_added", "reason",
                        "metrics_status"}


def test_guard_names_never_store_text(tmp_path):
    pre = "PreToolUse:Bash hook error: "
    t = transcript(
        tmp_path,
        refusal(pre + "local-ci merge guard: run gh pr merge from /tmp/secret-client"),
        refusal(pre + 'Commit message format invalid: "fix secret thing"'),
        refusal(pre + 'Scope "x" is not in the locked list for project type "client-y"'),
        refusal(pre + "hardline-check rm-rf: wipe /tmp/secret-client."),
        refusal(pre + "some unknown hook said /tmp/secret-client"),
        refusal("Permission to use Bash with command S=/tmp/secret-client/run.sh"),
    )
    rec = hm.parse_session(t)
    assert rec["hook_refusals"] == {"merge-guard": 1, "commit-scope": 2, "hardline": 1, "other": 1}
    assert rec["permission_refusals"] == 1
    blob = json.dumps(rec)
    assert "/tmp/" not in blob and "secret" not in blob and "client" not in blob


def test_captured(tmp_path):
    assert hm.parse_session(transcript(tmp_path, use("Skill", skill="capture")))["captured"] is True
    log = f"{VAULT}/inbox/daily/implementation/p/2026-10-20-x.md"
    assert hm.parse_session(transcript(tmp_path, use("Write", file_path=log)))["captured"] is True
    other = transcript(tmp_path, use("Skill", skill="git-commit"), use("Edit", 1, file_path=f"{REPO}/README.md"))
    assert hm.parse_session(other)["captured"] is False


def test_rules_added(tmp_path):
    pit = f"{VAULT}/resources/operational/ai-agents/pitfalls.md"
    t = transcript(tmp_path, use("Edit", file_path=pit, old_string="- a ^v1", new_string="- a ^v1\n- b ^v13"))
    rec = hm.parse_session(t)
    assert rec["rules_added"] == ["v13"]
    assert rec["harness_edits"] == ["resources/operational/ai-agents/pitfalls.md"]
    t = transcript(tmp_path, use("Write", file_path=pit, content="- a ^v1 ^v99"), name="sid-2")
    rec = hm.parse_session(t)
    assert rec["rules_added"] == [] and rec["harness_edits"] == ["resources/operational/ai-agents/pitfalls.md"]


def test_harness_edits_paths_relative(tmp_path):
    t = transcript(
        tmp_path,
        use("Edit", 0, file_path=f"{REPO}/skills/capture/SKILL.md", old_string="", new_string=""),
        use("Edit", 1, file_path=f"{VAULT}/resources/knowledge/patterns/git-patterns.md", old_string="", new_string=""),
        use("Edit", 2, file_path=f"{VAULT}/projects/p.md", old_string="", new_string=""),
        use("Edit", 3, file_path="/home/u/other/file.py", old_string="", new_string=""),
        use("Read", 4, file_path=f"{REPO}/README.md"),
    )
    assert hm.parse_session(t)["harness_edits"] == ["resources/knowledge/patterns/git-patterns.md",
                                                    "skills/capture/SKILL.md"]


def test_subagent_tools_folded(tmp_path):
    main = transcript(tmp_path, use("Read"))
    sub = tmp_path / "sid-1" / "subagents"
    sub.mkdir(parents=True)
    (sub / "a.jsonl").write_text("".join(json.dumps(r) + "\n" for r in (
        use("Read", 1), use("Read", 2), use("Edit", 3, file_path=f"{REPO}/skills/x/SKILL.md"))))
    rec = hm.parse_session(main)
    assert rec["subagent_tools"] == {"Read": 2, "Edit": 1}
    assert rec["tools"] == {"Read": 1}
    assert rec["harness_edits"] == ["skills/x/SKILL.md"]


def test_streamed_block_counted_once(tmp_path):
    dup = use("Skill", skill="git-commit")
    assert hm.parse_session(transcript(tmp_path, dup, dup))["skills"] == {"git-commit": 1}


def test_failed_transcript(tmp_path):
    rec = hm.parse_session(tmp_path / "ghost-id.jsonl")
    assert rec["session_id"] == "ghost-id" and rec["metrics_status"] == "failed"


def test_empty_last_line_is_partial(tmp_path):
    path = transcript(tmp_path, use("Skill", skill="x"))
    path.write_text(path.read_text() + "\n")
    rec = hm.parse_session(path)
    assert rec["metrics_status"] == "partial" and rec["skills"] == {"x": 1}


def rec_with(**kw):
    return {"session_id": "sid-1", "date": "2026-10-20T10:00:00Z", "skills": {}, **kw}


def test_append_replaces_same_id(tmp_path):
    hm.append_record(rec_with(skills={"a": 1}), tmp_path, "h")
    hm.append_record({**rec_with(), "session_id": "other"}, tmp_path, "h")
    path = hm.append_record(rec_with(skills={"b": 2}), tmp_path, "h")
    assert path == tmp_path / "meta" / "harness-sessions" / "2026-10-h.jsonl"
    rows = [json.loads(line) for line in path.read_text().splitlines()]
    assert [r["session_id"] for r in rows] == ["sid-1", "other"]
    assert rows[0]["skills"] == {"b": 2}


def test_append_atomic(tmp_path, monkeypatch):
    path = hm.append_record(rec_with(skills={"a": 1}), tmp_path, "h")
    before = path.read_text()

    def boom(*a):
        raise OSError("disk")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError):
        hm.append_record(rec_with(skills={"b": 2}), tmp_path, "h")
    assert path.read_text() == before
    assert [p.name for p in path.parent.iterdir()] == [path.name]


def test_compact_one_line():
    line = hm.compact(hm.parse_session(FIXTURE))
    assert "\n" not in line and line.startswith("16b04768")


def run(*args, env=None):
    return subprocess.run(["python3", "-I", str(SCRIPT), *args], capture_output=True, text=True,
                          env={**os.environ, **(env or {})})


def test_cli_session_by_id_and_append(tmp_path):
    proj = tmp_path / "projects" / "p"
    proj.mkdir(parents=True)
    (proj / "sid-1.jsonl").write_text(FIXTURE.read_text())
    env = {"CLAUDE_PROJECTS_DIR": str(tmp_path / "projects")}
    out = run("session", "--id", "sid-1", "--compact", env=env)
    assert out.returncode == 0 and out.stdout.startswith("16b04768") and out.stdout.count("\n") == 1
    assert run("session", "--id", "nope", env=env).returncode == 2
    vault = tmp_path / "vault"
    done = run("append", str(proj / "sid-1.jsonl"), "--vault", str(vault), "--host", "h", "--reason", "clear")
    assert done.returncode == 0 and done.stdout == ""
    row = json.loads((vault / "meta/harness-sessions/2026-10-h.jsonl").read_text())
    assert row["reason"] == "clear" and row["host"] == "h"
