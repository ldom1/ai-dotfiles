"""precompact-checkpoint.sh appends a breadcrumb to the vault before each compaction."""
import json
import subprocess
from datetime import date
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "precompact-checkpoint.sh"
REPO = Path(__file__).resolve().parents[3]


def setup(tmp_path: Path):
    vault = tmp_path / "vault"
    vault.mkdir()
    env_file = tmp_path / "brain.env"
    env_file.write_text(f"BRAIN_PATH={vault}\nexport BRAIN_PATH\n")
    repo = tmp_path / "proj"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", "-b", "feat/x", str(repo)], check=True)
    (repo / ".brain-project").write_text("demo\n")
    (repo / "app.py").write_text("x = 1\n")
    t = tmp_path / "t.jsonl"
    lines = [{"type": "user", "message": {"role": "user", "content": "add the export endpoint"}},
             {"type": "assistant", "message": {"id": "m1", "usage": {"input_tokens": 5, "cache_read_input_tokens": 300000}}},
             {"type": "user", "message": {"role": "user", "content": [{"type": "text", "text": "now fix the tests"}]}},
             {"type": "user", "isMeta": True, "message": {"role": "user", "content": "injected skill text"}},
             {"type": "user", "origin": {"kind": "task-notification"}, "message": {"role": "user", "content": "task done"}}]
    t.write_text("\n".join(json.dumps(x) for x in lines) + "\n")
    return vault, env_file, repo, t


def run(env_file: Path, repo: Path, t: Path, tmp_path: Path, trigger: str = "auto"):
    event = {"session_id": "abcdef123456", "transcript_path": str(t), "cwd": str(repo), "trigger": trigger,
             "hook_event_name": "PreCompact"}
    subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True, check=True,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "BRAIN_ENV_FILE": str(env_file),
                        "AI_DOTFILES": str(REPO)})


def test_writes_checkpoint_with_branch_files_and_prompts(tmp_path):
    vault, env_file, repo, t = setup(tmp_path)
    run(env_file, repo, t, tmp_path)
    note = (vault / "inbox/daily/checkpoints/demo" / f"{date.today():%Y-%m-%d}.md").read_text()
    assert "auto" in note and "feat/x" in note and "app.py" in note
    assert "now fix the tests" in note and "add the export endpoint" in note
    assert "300k" in note
    assert "injected skill text" not in note and "task done" not in note


def test_second_compaction_appends(tmp_path):
    vault, env_file, repo, t = setup(tmp_path)
    run(env_file, repo, t, tmp_path, "auto")
    run(env_file, repo, t, tmp_path, "manual")
    note = (vault / "inbox/daily/checkpoints/demo" / f"{date.today():%Y-%m-%d}.md").read_text()
    assert note.count("## ") == 2 and "manual" in note


def test_never_writes_to_implementation_logs(tmp_path):
    vault, env_file, repo, t = setup(tmp_path)
    run(env_file, repo, t, tmp_path)
    assert not (vault / "inbox/daily/implementation").exists()


def test_no_vault_is_silent(tmp_path):
    _, _, repo, t = setup(tmp_path)
    event = {"session_id": "s", "transcript_path": str(t), "cwd": str(repo), "trigger": "auto"}
    r = subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "BRAIN_ENV_FILE": "/nonexistent"})
    assert r.returncode == 0


def test_resume_context_from_transcript(tmp_path):
    vault, env_file, repo, t = setup(tmp_path)
    subprocess.run(["git", "-C", str(repo), "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-q",
                    "--allow-empty", "-m", "fix(x): first step"], check=True)
    note_ = "Shell built: " + "gh" + "p_" + "A" * 36
    lines = [
        {"type": "assistant", "message": {"id": "a1", "role": "assistant", "content": [
            {"type": "text", "text": "Option 1 merges locally, option 2 opens a PR. Which option?"}]}},
        {"type": "user", "message": {"role": "user", "content": "2"}},
        {"type": "assistant", "message": {"id": "a2", "role": "assistant", "content": [
            {"type": "tool_use", "id": "t1", "name": "Edit", "input": {"file_path": "/r/app.py"}},
            {"type": "tool_use", "id": "t2", "name": "Agent", "input": {}},
            {"type": "tool_use", "id": "t3", "name": "Agent", "input": {}},
            {"type": "tool_use", "id": "t4", "name": "Bash", "input": {}}]}},
        {"type": "user", "toolUseResult": {"agentId": "aaa111", "description": "Review task 1", "status": "async_launched"},
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t2", "content": "launched"}]}},
        {"type": "user", "toolUseResult": {"agentId": "bbb222", "description": "Implement task 2", "status": "async_launched"},
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t3", "content": "launched"}]}},
        {"type": "queue-operation", "operation": "enqueue",
         "content": "<task-notification>\n<task-id>aaa111</task-id>\n<status>completed</status>"},
        {"type": "user", "message": {"role": "user", "content": [
            {"type": "tool_result", "tool_use_id": "t4", "is_error": True, "content": "Exit code 1\nboom failed"}]}},
        {"type": "user", "toolUseResult": {"answers": {"Merge the PR now?": "Merge (Recommended)"}},
         "message": {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "t5", "content": "answered"}]}},
        {"type": "user", "isCompactSummary": True, "message": {"role": "user", "content": "This session is being continued"}},
        {"type": "assistant", "message": {"id": "a3", "role": "assistant", "content": [
            {"type": "text", "text": "Pushed. Next: watch CI."}]}},
        {"type": "assistant", "message": {"id": "a3", "role": "assistant", "content": [
            {"type": "text", "text": note_}]}},
    ]
    with t.open("a") as f:
        f.write("\n".join(json.dumps(x) for x in lines) + "\n")
    run(env_file, repo, t, tmp_path)
    note = (vault / "inbox/daily/checkpoints/demo" / f"{date.today():%Y-%m-%d}.md").read_text()
    assert "fix(x): first step" in note and "no upstream" in note
    assert "Which option?" in note and "**2**" in note
    assert "`/r/app.py`" in note
    assert "Implement task 2 (`bbb222`)" in note and "aaa111" not in note
    assert "boom failed" in note
    assert "Merge the PR now? → **Merge (Recommended)**" in note
    assert "being continued" not in note
    assert "Pushed. Next: watch CI." in note and "Shell built: ***" in note and "A" * 36 not in note


def checkpoint(vault: Path, slug: str) -> str:
    return (vault / "inbox/daily/checkpoints" / slug / f"{date.today():%Y-%m-%d}.md").read_text()


def test_worktree_named_agent_uses_repo_slug(tmp_path):
    vault, env_file, _, t = setup(tmp_path)
    clone = tmp_path / "agent-abc123"
    subprocess.run(["git", "init", "-q", "-b", "main", str(clone)], check=True)
    subprocess.run(["git", "-C", str(clone), "remote", "add", "origin",
                    "https://github.com/someone/ai-dotfiles.git"], check=True)
    run(env_file, clone, t, tmp_path)
    assert "auto" in checkpoint(vault, "ai-dotfiles")
    assert not (vault / "inbox/daily/checkpoints/agent-abc123").exists()


def test_slug_falls_back_to_dir_name_without_load_sh(tmp_path):
    vault, env_file, repo, t = setup(tmp_path)
    (repo / ".brain-project").unlink()
    event = {"session_id": "s", "transcript_path": str(t), "cwd": str(repo), "trigger": "auto"}
    subprocess.run(["bash", str(HOOK)], input=json.dumps(event), capture_output=True, text=True, check=True,
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "BRAIN_ENV_FILE": str(env_file),
                        "AI_DOTFILES": str(tmp_path / "missing")})
    assert "auto" in checkpoint(vault, "proj")


def redacted(tmp_path, text: str) -> str:
    vault, env_file, repo, t = setup(tmp_path)
    line = {"type": "assistant", "message": {"id": "z1", "role": "assistant",
                                             "content": [{"type": "text", "text": text}]}}
    with t.open("a") as f:
        f.write(json.dumps(line) + "\n")
    run(env_file, repo, t, tmp_path)
    return checkpoint(vault, "demo")


def test_redacts_known_token_formats(tmp_path):
    raw = ("key AKIA" + "ABCDEFGHIJKLMNOP, then st." + "0123456789abcdef0123456789abcdef.x"
           " and tk_" + "abcdefghijklmnopqrstuvwxyz012 done")
    assert "> key ***, then *** and *** done" in redacted(tmp_path, raw)


def test_keeps_lookalike_text(tmp_path):
    raw = ("AKIA akiaabcdefghijklmnop st.louis tk_short 3ccff5338ea700537839b21900aa5358a0402c98 "
           "skills/obsidian-cli/")
    assert "> " + raw in redacted(tmp_path, raw)


def test_existing_patterns_still_redact(tmp_path):
    raw = "a " + "gh" + "p_" + "A" * 36 + " b " + "s" + "k-" + "B" * 24 + " c"
    assert "> a *** b *** c" in redacted(tmp_path, raw)
