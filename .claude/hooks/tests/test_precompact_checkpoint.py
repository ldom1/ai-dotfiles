"""precompact-checkpoint.sh appends a breadcrumb to the vault before each compaction."""
import json
import subprocess
from datetime import date
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "precompact-checkpoint.sh"


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
                   env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "BRAIN_ENV_FILE": str(env_file)})


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
