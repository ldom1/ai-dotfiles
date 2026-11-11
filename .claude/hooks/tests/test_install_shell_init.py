"""install.sh blocks run alone: terminal init (~/.zshenv for Orca's login shells) and the statusLine
migration (drop the aif-statusline wrapper of the removed ai-dotdeck).

Each block starts at its comment line and ends at the first blank line, as in install.sh.
"""
import json
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PRELUDE = "log() { echo \"$*\"; }; warn() { echo \"$*\"; }\n"


def block(start: str) -> str:
    lines = (REPO / "scripts" / "install.sh").read_text().splitlines()
    i = next(n for n, line in enumerate(lines) if line.startswith(start))
    out = []
    for line in lines[i:]:
        if not line.strip():
            break
        out.append(line)
    return "\n".join(out) + "\n"


def run_block(start: str, home: Path, dotfiles: Path = REPO, shell: str = "/bin/zsh"):
    return subprocess.run(["bash", "-c", PRELUDE + block(start)], capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(home), "DOTFILES": str(dotfiles),
                               "SHELL": shell})


def test_terminal_init_adds_the_zshenv_line_once(tmp_path):
    for _ in range(2):
        r = run_block("# Terminal init:", tmp_path)
        assert r.returncode == 0, r.stderr
    lines = [line for line in (tmp_path / ".zshenv").read_text().splitlines() if "config/shell-init.sh" in line]
    assert len(lines) == 1
    assert f'. "{REPO}/config/shell-init.sh"' in lines[0]


def test_terminal_init_keeps_the_rc_files(tmp_path):
    (tmp_path / ".bashrc").write_text("# mine\n")
    run_block("# Terminal init:", tmp_path)
    assert "config/shell-init.sh" in (tmp_path / ".bashrc").read_text()


def statusline(tmp_path: Path, command: str | None) -> dict:
    d = tmp_path / "dotfiles"
    (d / ".claude").mkdir(parents=True)
    settings = {"model": "opus"}
    if command is not None:
        settings["statusLine"] = {"type": "command", "command": command}
    (d / ".claude" / "settings.json").write_text(json.dumps(settings))
    r = run_block("# statusLine:", tmp_path, dotfiles=d)
    assert r.returncode == 0, r.stderr
    return json.loads((d / ".claude" / "settings.json").read_text())


def test_statusline_wrapper_is_stripped(tmp_path):
    s = statusline(tmp_path, f"{tmp_path}/.local/bin/aif-statusline {tmp_path}/.local/bin/ccstatusline --config x.json")
    assert s["statusLine"] == {"type": "command", "command": f"{tmp_path}/.local/bin/ccstatusline --config x.json"}
    assert s["model"] == "opus"


def test_statusline_wrapper_alone_is_removed(tmp_path):
    s = statusline(tmp_path, f"{tmp_path}/.local/bin/aif-statusline")
    assert "statusLine" not in s


def test_statusline_without_wrapper_is_untouched(tmp_path):
    before = f"{tmp_path}/.local/bin/ccstatusline --config x.json"
    s = statusline(tmp_path, before)
    assert s["statusLine"]["command"] == before
    assert not (tmp_path / "dotfiles" / ".claude" / "settings.json.bak").exists()
