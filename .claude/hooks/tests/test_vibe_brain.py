"""bin/vibe-brain (sync start, context file, vibe, sync end), scripts/brain-context.sh (size budget) and the
Cursor prewarm that uses it. Stubs stand in for sync.sh, brain-context.sh and vibe; HOME is a tmp dir."""
import os
import signal
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
VIBE_BRAIN = REPO / "bin" / "vibe-brain"
CONTEXT = REPO / "scripts" / "brain-context.sh"
PREWARM = REPO / "scripts" / "brain-hooks-prewarm.sh"
BUDGET = 9500
STUB_CONTEXT = "echo note; echo '--- AI-AGENTS PITFALLS (constraints) ---'; echo rule; echo '--- END PITFALLS ---'"


def exe(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("#!/usr/bin/env bash\n" + body + "\n")
    path.chmod(0o755)


def setup(tmp_path: Path, sync: str = "", context: str = STUB_CONTEXT, vibe: str = "") -> dict:
    """A fake ai-dotfiles with stub sync.sh and brain-context.sh, a stub `vibe` on PATH. Every call is logged."""
    dot, home, bin_dir = tmp_path / "dot", tmp_path / "home", tmp_path / "bin"
    home.mkdir()
    log = tmp_path / "log"
    exe(dot / "skills/brain-sync/scripts/sync.sh", f'echo "sync $1" >>{log}\n{sync}')
    exe(dot / "scripts/brain-context.sh", f"echo context >>{log}\n{context}")
    exe(bin_dir / "vibe", f'echo "vibe $*" >>{log}\necho "BRAIN_PATH=$BRAIN_PATH" >>{log}\n{vibe}')
    env_file = tmp_path / "brain.env"
    env_file.write_text("BRAIN_PATH=/the/vault\n")
    return {"PATH": f"{bin_dir}:/usr/bin:/bin", "HOME": str(home), "AI_DOTFILES": str(dot),
            "BRAIN_ENV_FILE": str(env_file)}


def run(env: dict, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(VIBE_BRAIN), *args], env=env, capture_output=True, text=True, timeout=30)


def log_of(tmp_path: Path) -> list[str]:
    return (tmp_path / "log").read_text().splitlines()


def ctx_file(env: dict) -> Path:
    return Path(env["HOME"]) / ".vibe" / "brain-context.md"


def test_runs_start_context_vibe_end_in_order(tmp_path):
    env = setup(tmp_path)
    r = run(env, "--resume", "x")
    assert r.returncode == 0, r.stderr
    assert log_of(tmp_path) == ["sync start", "context", "vibe --resume x", "BRAIN_PATH=/the/vault", "sync end"]
    assert "--- AI-AGENTS PITFALLS" in ctx_file(env).read_text()


def test_runs_end_once_and_returns_vibes_code_on_failure(tmp_path):
    r = run(setup(tmp_path, vibe="exit 3"))
    assert r.returncode == 3
    assert log_of(tmp_path).count("sync end") == 1


def test_skips_end_when_start_fails(tmp_path):
    r = run(setup(tmp_path, sync='[ "$1" = start ] && exit 1\nexit 0', vibe="exit 4"))
    assert r.returncode == 4
    assert any(line.startswith("vibe") for line in log_of(tmp_path))
    assert "sync end" not in log_of(tmp_path)
    assert "sync.sh start" in r.stderr


def test_keeps_no_partial_context(tmp_path):
    env = setup(tmp_path, context="echo half a block; exit 1")
    r = run(env)
    assert r.returncode == 0
    assert not ctx_file(env).exists()
    assert not list(ctx_file(env).parent.glob("brain-context*"))
    assert any(line.startswith("vibe") for line in log_of(tmp_path))
    assert log_of(tmp_path).count("sync end") == 1


def test_term_runs_end_once_and_exits_143(tmp_path):
    marker = tmp_path / "started"
    env = setup(tmp_path, vibe=f"touch {marker}\nexec sleep 30")
    p = subprocess.Popen(["bash", str(VIBE_BRAIN)], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    try:
        deadline = time.monotonic() + 10
        while not marker.exists() and time.monotonic() < deadline:
            time.sleep(0.05)
        assert marker.exists(), "the stub vibe never started"
        p.send_signal(signal.SIGTERM)
        assert p.wait(timeout=10) == 143
    finally:
        if p.poll() is None:
            os.killpg(p.pid, signal.SIGKILL)
    assert log_of(tmp_path).count("sync end") == 1


def test_keeps_vibes_code_when_end_fails(tmp_path):
    r = run(setup(tmp_path, sync='[ "$1" = end ] && exit 1\nexit 0'))
    assert r.returncode == 0
    assert "sync.sh end" in r.stderr


def pitfalls(target: int) -> str:
    text, i = "---\ntitle: pitfalls\n---\n\nIntro.\n\n", 0
    while True:
        sec = f"## Section {i}\n" + "".join(f"- rule {i}.{j} {'r' * 80} ^r{i * 5 + j}\n" for j in range(5))
        if len((text + sec).encode()) > target:
            return text
        text, i = text + sec, i + 1


def vault(tmp_path: Path, pitfalls_size: int) -> dict:
    v = tmp_path / "vault"
    (v / "projects").mkdir(parents=True)
    (v / "projects/proj.md").write_text("".join(f"note line {i:03d} {'n' * 60}\n" for i in range(100)))  # 7.4 KB
    p = v / "resources/operational/ai-agents/pitfalls.md"
    p.parent.mkdir(parents=True)
    p.write_text(pitfalls(pitfalls_size))
    (tmp_path / "proj").mkdir()
    env_file = tmp_path / "brain.env"
    env_file.write_text(f"BRAIN_PATH={v}\n")
    return {"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"), "BRAIN_ENV_FILE": str(env_file),
            "AI_DOTFILES": str(REPO)}


@pytest.mark.parametrize("size, note_kept", [(1000, True), (6000, True), (8700, False), (12000, False)])
def test_brain_context_stays_within_budget_and_pitfalls_win(tmp_path, size, note_kept):
    env = vault(tmp_path, size)
    out = subprocess.run(["bash", str(CONTEXT)], env=env, cwd=tmp_path / "proj", capture_output=True, text=True,
                         check=True).stdout
    assert len(out.encode()) <= BUDGET
    assert "--- AI-AGENTS PITFALLS (constraints) ---" in out and "--- END PITFALLS ---" in out
    assert ("note line 000" in out) == note_kept
    if size <= 8700:  # whole whenever they fit
        assert "[truncated" not in out
        assert Path(env["BRAIN_ENV_FILE"]).parent.joinpath("vault/resources/operational/ai-agents/pitfalls.md") \
            .read_text().splitlines()[-1] in out


def test_prewarm_injects_pitfalls_inline(tmp_path):
    env = vault(tmp_path, 3000)
    dot = tmp_path / "dot"
    for rel in ("scripts/brain-context.sh", "scripts/brain-context-lib.sh", "scripts/fit-sections.py",
                ".cursor/hooks/lib-inject-rule.sh", "skills/brain-load/scripts/load.sh",
                "skills/brain-load/scripts/_brain_env.sh"):
        (dot / rel).parent.mkdir(parents=True, exist_ok=True)
        (dot / rel).symlink_to(REPO / rel)
    env |= {"AI_DOTFILES": str(dot), "BRAIN_HOOKS_LOG_DIR": str(tmp_path / "logs")}
    subprocess.run(["bash", str(PREWARM)], env=env, cwd=tmp_path / "proj", capture_output=True, text=True, check=True)
    sidecar = (tmp_path / "logs/brain-hooks-last-context.md").read_text()
    assert "--- AI-AGENTS PITFALLS (constraints) ---" in sidecar
    assert "rule 0.0 " in sidecar
    assert "note line 000" in sidecar
    assert "Read that file" not in sidecar
