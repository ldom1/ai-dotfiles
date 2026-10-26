"""harness-metrics.py: session transcript -> one record; append replaces the line per session id."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime, timedelta, timezone
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


def typed(cmd):
    # Shape of a user-typed slash command, copied from a real transcript (Claude Code 2.1.310).
    return {"type": "user", "message": {"role": "user",
            "content": f"<command-message>{cmd}</command-message>\n<command-name>/{cmd}</command-name>"}}


def test_typed_slash_command_counts_as_skill(tmp_path):
    listing = {"type": "attachment", "attachment": {"type": "skill_listing", "names": ["capture", "brain-search"]}}
    rec = hm.parse_session(transcript(tmp_path, listing, typed("capture"), typed("brain-search"), typed("compact")))
    assert rec["skills"] == {"capture": 1, "brain-search": 1}  # /compact is a built-in, not a skill
    assert rec["captured"] is True


def test_user_turns_skip_injected_messages(tmp_path):
    # Shapes copied from real transcripts (Claude Code 2.1.310): a typed prompt, an injected skill body,
    # a background-task notification. Only the first is a user turn.
    prompt = {"type": "user", "origin": {"kind": "human"}, "promptSource": "typed",
              "message": {"role": "user", "content": "cherche dans le brain"}}
    skill_body = {"type": "user", "isMeta": True,
                  "message": {"role": "user", "content": [{"type": "text", "text": "Base directory for this skill: x"}]}}
    notification = {"type": "user", "origin": {"kind": "task-notification", "producer": "session-task"},
                    "promptSource": "system", "message": {"role": "user", "content": "<task-notification>x"}}
    rec = hm.parse_session(transcript(tmp_path, prompt, skill_body, notification, typed("capture")))
    assert rec["user_turns"] == 2  # the prompt and the typed /capture


def test_rules_added(tmp_path):
    pit = f"{VAULT}/resources/operational/ai-agents/pitfalls.md"
    t = transcript(tmp_path, use("Edit", file_path=pit, old_string="- a ^v1", new_string="- a ^v1\n- b ^v13"))
    rec = hm.parse_session(t)
    assert rec["rules_added"] == ["v13"]
    assert rec["harness_edits"] == ["resources/operational/ai-agents/pitfalls.md"]
    t = transcript(tmp_path, use("Write", file_path=pit, content="- a ^v1 ^v99"), name="sid-2")
    rec = hm.parse_session(t)
    assert rec["rules_added"] == [] and rec["harness_edits"] == ["resources/operational/ai-agents/pitfalls.md"]


def test_rules_added_counts_definitions_only(tmp_path):
    pit = f"{VAULT}/resources/operational/ai-agents/pitfalls.md"
    new = "- a ^v1\n- see [[pitfalls#^v5]]\n- ^v7→^v2"
    t = transcript(tmp_path, use("Edit", file_path=pit, old_string="- a ^v1", new_string=new))
    assert hm.parse_session(t)["rules_added"] == []
    t = transcript(tmp_path, use("Edit", file_path=pit, old_string="- a ^v1", new_string=new + "\n- New rule. ^v13"),
                   name="sid-2")
    assert hm.parse_session(t)["rules_added"] == ["v13"]


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


def test_append_closes_temp_before_replace(tmp_path, monkeypatch):
    real_ntf, real_replace, handles, states = tempfile.NamedTemporaryFile, os.replace, [], []

    def spy_ntf(*a, **k):
        handles.append(real_ntf(*a, **k))
        return handles[-1]

    def spy_replace(src, dst):
        states.append(handles[-1].closed)  # NTFS (drvfs) cannot rename an open file
        real_replace(src, dst)

    monkeypatch.setattr(hm.tempfile, "NamedTemporaryFile", spy_ntf)
    monkeypatch.setattr(os, "replace", spy_replace)
    hm.append_record(rec_with(), tmp_path, "h")
    assert states == [True]


def test_append_write_failure_leaves_no_temp(tmp_path, monkeypatch):
    path = hm.append_record(rec_with(skills={"a": 1}), tmp_path, "h")
    before = path.read_text()

    real_ntf = tempfile.NamedTemporaryFile

    class Boom:
        def __init__(self, *a, **k):
            self.real = real_ntf(*a, **k)
            self.name = self.real.name

        def __enter__(self):
            return self

        def __exit__(self, *a):
            self.real.close()

        def write(self, _):
            raise OSError("disk full")

    monkeypatch.setattr(hm.tempfile, "NamedTemporaryFile", Boom)
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


# --- history ---

def at(day, *records):
    return [{**r, "timestamp": f"{day}T10:00:00Z"} for r in records]


def git(vault, *args, day="2026-10-21"):
    env = {**os.environ, "GIT_AUTHOR_DATE": f"{day}T10:00:00", "GIT_COMMITTER_DATE": f"{day}T10:00:00"}
    subprocess.run(["git", "-C", str(vault), "-c", "user.name=t", "-c", "user.email=t@t", *args],
                   check=True, capture_output=True, env=env)


def commit_pitfalls(vault, text, day="2026-10-21"):
    f = vault / "resources/operational/ai-agents/pitfalls.md"
    f.parent.mkdir(parents=True, exist_ok=True)
    f.write_text(text)
    git(vault, "add", "-A", day=day)
    git(vault, "commit", "-m", "x", day=day)


@pytest.fixture
def world(tmp_path, monkeypatch):
    """Two main transcripts (one captures), one subagent transcript, a skill log, a git vault."""
    proj = tmp_path / "projects" / "p"
    (proj / "a" / "subagents").mkdir(parents=True)
    transcript(proj, *at("2026-10-20", use("Skill", skill="capture"), use("Agent", 1, subagent_type="reviewer")),
               name="a")
    transcript(proj, *at("2026-10-22", use("Skill", skill="git-commit"), refusal("PreToolUse:Bash hook error: "
               "local-ci merge guard: x")), name="b")
    (proj / "a" / "subagents" / "agent-1.jsonl").write_text(json.dumps(use("Read", 2)) + "\n")
    log = tmp_path / "skill-usage.log"
    log.write_text("2026-09-30T09:00:00+01:00 old-skill\n2026-10-21T09:00:00+01:00 capture claude:Skill\n"
                   + "2026-10-21T10:00:00+01:00 brain-load claude:sessionEnd\n" * 10)
    vault = tmp_path / "vault"
    vault.mkdir()
    git(vault, "init", "-q")
    monkeypatch.setattr(hm, "REPO_DIR", tmp_path / "repo")
    (tmp_path / "repo" / ".claude").mkdir(parents=True)
    return tmp_path / "projects", log, vault


def test_capture_rate_same_population(world):
    projects, log, vault = world
    h = hm.history(projects, log, vault)
    assert h["sessions"]["count"]["value"] == 2  # subagent transcript is not a session
    assert h["capture_rate"]["value"] == 0.5 and h["capture_rate"]["label"] == "incomplet"  # Bash-written logs unseen
    assert h["skills"]["total"]["label"] == "mesuré"
    assert h["skill_log"]["by_source"]["value"]["claude:sessionEnd"] == 10  # the log never feeds the rate
    assert h["skills"]["by_name"]["value"] == {"capture": 1, "git-commit": 1}
    assert h["agents"]["by_name"]["value"] == {"reviewer": 1}
    assert h["hook_refusals"]["by_guard"]["value"] == {"merge-guard": 1}


def test_window_reported(world):
    projects, log, vault = world
    h = hm.history(projects, log, vault)
    assert h["window"] == {"from": "2026-10-20", "to": "2026-10-22"}
    assert h["skill_log"]["range"] == {"from": "2026-09-30", "to": "2026-10-21"}  # its own full range
    assert h["skill_log"]["total"]["value"] == 12 and h["skill_log"]["in_window"]["value"] == 11
    assert h["skill_log"]["by_month"]["value"] == {"2026-09": 1, "2026-10": 11}


def test_rules_from_git(world):
    projects, log, vault = world
    commit_pitfalls(vault, "- rule one ^v1\n")
    commit_pitfalls(vault, "- rule two ^v2\n")
    h = hm.history(projects, log, vault)
    assert (h["rules"]["added"]["value"], h["rules"]["removed"]["value"]) == (2, 1)
    assert h["rules"]["added"]["label"] == "mesuré" and "definitions only" in h["rules"]["added"]["source"]
    assert h["rules"]["added_in_window"]["value"] == 2
    commit_pitfalls(vault, "- rule two ^v2\n- three ^v3\n", day="2026-12-01")  # outside the window
    h = hm.history(projects, log, vault)
    assert h["rules"]["added"]["value"] == 3 and h["rules"]["added_in_window"]["value"] == 2


def test_rules_without_git_is_incomplete(world, tmp_path):
    projects, log, _ = world
    h = hm.history(projects, log, tmp_path / "nogit")
    assert h["rules"]["added"]["label"] == "incomplet"


def test_sensors(world, tmp_path):
    projects, log, vault = world
    for n in ("s1.md", "s2.md"):
        (vault / "inbox/sensors").mkdir(parents=True, exist_ok=True)
        (vault / "inbox/sensors" / n).write_text("draft")
    (tmp_path / "repo/.claude/settings.json.tpl").write_text('{"hooks": [{\n  "command": "x",\n  "type": "command"\n}]}')
    h = hm.history(projects, log, vault)
    assert h["sensors"]["drafts"]["value"] == 2 and h["sensors"]["installed"]["value"] == 1


def test_session_logs_and_harness_sessions(world):
    projects, log, vault = world
    d = vault / "inbox/daily/implementation/proj"
    d.mkdir(parents=True)
    (d / "2026-10-21-a.md").write_text("## x\n**Pitfall hit:** [[pitfalls#^v5]]\n**Pitfall hit:** [[pitfalls#^v5]] [[pitfalls#^c1]]\n")
    (d / "2026-08-01-old.md").write_text("**Pitfall hit:** [[pitfalls#^v9]]\n")
    (vault / "meta/harness-sessions").mkdir(parents=True)
    (vault / "meta/harness-sessions/2026-10-h.jsonl").write_text('{"a": 1}\n{"a": 2}\n')
    h = hm.history(projects, log, vault)
    assert h["session_logs"]["files"]["value"] == 1 and h["session_logs"]["pitfall_hits"]["value"] == 2
    assert h["session_logs"]["hits_by_rule"]["value"] == {"v5": 2, "c1": 1}
    assert h["harness_sessions"]["value"] == 2


def test_empty_world_does_not_crash(tmp_path, monkeypatch):
    monkeypatch.setattr(hm, "REPO_DIR", tmp_path)
    h = hm.history(tmp_path / "none", tmp_path / "none.log", tmp_path / "vault")
    assert h["sessions"]["count"]["value"] == 0 and h["capture_rate"]["value"] is None


def test_cli_history_prints_json(world):
    projects, log, vault = world
    out = run("history", "--vault", str(vault), "--projects", str(projects), "--skill-log", str(log))
    assert out.returncode == 0
    assert list(json.loads(out.stdout)) == ["window", "sessions", "capture_rate", "skills", "mcp", "agents",
                                            "hook_refusals", "skill_log", "session_logs", "rules", "sensors",
                                            "harness_sessions"]


def test_rule_references_do_not_count(world):
    projects, log, vault = world
    commit_pitfalls(vault, "- rule one ^v1\n- see [[pitfalls#^v5]]\n## Retired ids\n^v2→^v1 ^v8→^v5\n")
    commit_pitfalls(vault, "- rule one ^v1\n- see [[pitfalls#^v7]] and ^v9 too.\n## Retired ids\n^v2→^v1 ^v3→^v7\n")
    h = hm.history(projects, log, vault)
    assert (h["rules"]["added"]["value"], h["rules"]["removed"]["value"]) == (1, 0)


def test_retiring_a_rule_counts_as_removed(world):
    projects, log, vault = world
    commit_pitfalls(vault, "- one ^v1\n- two ^v2\n## Retired ids\n")
    commit_pitfalls(vault, "- one ^v1\n## Retired ids\n^v2→^v1\n")
    h = hm.history(projects, log, vault)
    assert (h["rules"]["added"]["value"], h["rules"]["removed"]["value"]) == (2, 1)


def test_unreadable_transcript_degrades_labels(world):
    projects, log, vault = world
    (projects / "p" / "empty.jsonl").write_text("")
    h = hm.history(projects, log, vault)
    assert h["sessions"]["unreadable"]["value"] == 1 and h["sessions"]["count"]["value"] == 2
    for leaf in (h["sessions"]["count"], h["skills"]["total"], h["mcp"]["total"], h["agents"]["by_name"],
                 h["hook_refusals"]["by_guard"], h["capture_rate"]):
        assert leaf["label"] == "incomplet"


def test_partial_transcript_degrades_labels(world):
    projects, log, vault = world
    with open(projects / "p" / "b.jsonl", "a") as f:
        f.write('{"type": "assis')
    h = hm.history(projects, log, vault)
    assert h["sessions"]["partial"]["value"] == 1 and h["sessions"]["unreadable"]["value"] == 0
    assert h["skills"]["total"]["label"] == h["sessions"]["count"]["label"] == "incomplet"


def test_missing_skill_log_is_incomplete(world, tmp_path):
    projects, _, vault = world
    h = hm.history(projects, tmp_path / "absent.log", vault)
    assert h["skill_log"]["total"]["label"] == "incomplet" and h["skill_log"]["total"]["value"] == 0


def test_arrow_in_definition_prose_counts(world):
    projects, log, vault = world
    commit_pitfalls(vault, "- Link `a` → `b`. ^g9\n## Retired ids\n^v2→^v1 ^g4→^g2\n")
    h = hm.history(projects, log, vault)
    assert (h["rules"]["added"]["value"], h["rules"]["removed"]["value"]) == (1, 0)


def day(n):
    return (datetime.now(timezone.utc) - timedelta(days=n)).strftime("%Y-%m-%d")


def write_log(vault, n, *rows, slug="proj"):
    d = vault / "inbox/daily/implementation" / slug
    d.mkdir(parents=True, exist_ok=True)
    body = "**Goal:** g\n**Changes:**\n- not a harness row\n**Harness changes:** <optional>\n" + "".join(f"- {r}\n" for r in rows)
    (d / f"{day(n)}-topic.md").write_text(body + "**Metrics:** x\n")


def test_pending_changes_age_and_verdict(tmp_path):
    row = "skill capture · add step · expected: fewer misses · check: skills.capture"
    write_log(tmp_path, 10, row)
    write_log(tmp_path, 10, f"{row} · verdict: helped (3 vs 5, {day(1)})", slug="other")
    write_log(tmp_path, 2, row, slug="recent")
    got = hm.pending_changes(tmp_path)
    assert [(g["date"], g["line"], g["component"], g["change"], g["expected"], g["check"]) for g in got] == [
        (day(10), 5, "skill capture", "add step", "fewer misses", "skills.capture")]
    assert got[0]["log"].endswith(f"proj/{day(10)}-topic.md")


def test_pending_changes_bad_row_flagged(tmp_path):
    write_log(tmp_path, 10, "skill capture · add step · check: skills.capture", "just text")
    write_log(tmp_path, 1, "bad young row", slug="recent")  # malformed rows ignore the age filter
    got = hm.pending_changes(tmp_path)
    assert [(g["line"], g.get("malformed")) for g in got] == [(5, True), (6, True), (5, True)]
    assert all(set(g) == {"log", "line", "malformed"} for g in got)


def test_pending_changes_dot_in_text_and_blank_line(tmp_path):
    d = tmp_path / "inbox/daily/implementation/proj"
    d.mkdir(parents=True)
    (d / f"{day(10)}-topic.md").write_text(
        "**Harness changes:**\n- hook a · fix x · y · expected: e · f · check: c\n\n"
        "- hook b · tweak · expected: e · check: c · verdict: helped (1 vs 2, 2026-01-01)\n"
        "**Metrics:** x\n- not a row\n")
    got = hm.pending_changes(tmp_path)
    assert len(got) == 1 and got[0]["change"] == "fix x · y" and got[0]["expected"] == "e · f"
    assert got[0]["check"] == "c" and got[0]["line"] == 2


def test_cli_changes_prints_json(tmp_path):
    write_log(tmp_path, 10, "hook x · tweak · expected: e · check: c")
    out = subprocess.run([sys.executable, "-I", str(SCRIPT), "changes", "--vault", str(tmp_path), "--days", "7"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)[0]["component"] == "hook x"
