"""scripts/merge-settings.py merges the template into a live settings.json and fails closed on conflicts."""
import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
MERGE = REPO / "scripts" / "merge-settings.py"
HOOK = REPO / ".claude" / "hooks" / "brain-session-start.sh"


def hook(event, command, matcher=None, timeout=None):
    entry = {"type": "command", "command": command}
    if timeout is not None:
        entry["timeout"] = timeout
    group = {"hooks": [entry]}
    if matcher is not None:
        group["matcher"] = matcher
    return {event: [group]}


TEMPLATE = {
    "model": "opus",
    "permissions": {"deny": ["Bash(rm -rf *)"], "ask": ["Bash(git push *)"]},
    "env": {"TPL_VAR": "1"},
    "hooks": hook("PreToolUse", "__HOME__/.claude/hooks/check.sh", matcher="Bash", timeout=30),
    "enabledPlugins": {"p@m": True},
    "extraKnownMarketplaces": {"m": {"source": {"source": "github", "repo": "o/m"}}},
}


def write(d: Path, tpl: dict, live: dict | None) -> tuple[Path, Path]:
    d.mkdir(parents=True, exist_ok=True)
    (d / "settings.json.tpl").write_text(json.dumps(tpl, indent=2))
    if live is not None:
        (d / "settings.json").write_text(json.dumps(live, indent=2))
    return d / "settings.json.tpl", d / "settings.json"


def merge(tmp_path: Path, tpl: dict, live: dict | None, *args: str):
    t, s = write(tmp_path / "c", tpl, live)
    r = subprocess.run(["python3", str(MERGE), *args, str(t), str(s)], capture_output=True, text=True,
                       env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    return r, s


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(root: Path) -> dict:
    return {str(p.relative_to(root)): (sha(p) if p.is_file() and not p.is_symlink() else "dir/link")
            for p in root.rglob("*")}


def test_compatible_merge_adds_template_entries_keeps_local_and_is_idempotent(tmp_path):
    live = {"permissions": {"allow": ["Read(*)"], "deny": ["Bash(sudo *)"]}, "env": {"LOCAL": "x"},
            "hooks": hook("Stop", "/local.sh"), "effortLevel": "high"}
    r, s = merge(tmp_path, TEMPLATE, live)
    assert r.returncode == 0, r.stdout + r.stderr
    out = json.loads(s.read_text())
    assert out["permissions"] == {"allow": ["Read(*)"], "deny": ["Bash(sudo *)", "Bash(rm -rf *)"],
                                  "ask": ["Bash(git push *)"]}
    assert out["env"] == {"LOCAL": "x", "TPL_VAR": "1"}
    assert out["hooks"]["Stop"] == live["hooks"]["Stop"]
    assert out["hooks"]["PreToolUse"] == hook("PreToolUse", f"{tmp_path}/.claude/hooks/check.sh", "Bash", 30)["PreToolUse"]
    assert out["effortLevel"] == "high" and out["enabledPlugins"] == {"p@m": True}
    assert "model" not in out
    assert (s.parent / "settings.json.bak").exists()
    before = sha(s)
    r2 = subprocess.run(["python3", str(MERGE), str(s.parent / "settings.json.tpl"), str(s)],
                        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path)})
    assert r2.returncode == 0 and sha(s) == before
    assert "add " not in r2.stdout and "no changes:" in r2.stdout


CMD = "__HOME__/.claude/hooks/check.sh"
CONFLICTS = {
    "env": ({"env": {"TPL_VAR": "2"}}, "env.TPL_VAR", ['"2"', '"1"']),
    "hook matcher": ({"hooks": hook("PreToolUse", CMD, "Edit", 30)}, "hooks.PreToolUse", ["Edit", "Bash"]),
    "hook timeout": ({"hooks": hook("PreToolUse", CMD, "Bash", 5)}, "hooks.PreToolUse", ["timeout=5", "timeout=30"]),
    "hook event": ({"hooks": hook("PostToolUse", CMD, "Bash", 30)}, "hooks.PreToolUse", ["PostToolUse", "PreToolUse"]),
    "disableAllHooks": ({"disableAllHooks": True}, "disableAllHooks", ["live=true"]),
}


@pytest.mark.parametrize("name", CONFLICTS)
def test_semantic_conflict_exits_3_and_writes_nothing(tmp_path, name):
    live, path, values = CONFLICTS[name]
    live = json.loads(json.dumps(live).replace("__HOME__", str(tmp_path)))
    r, s = merge(tmp_path, TEMPLATE, live)
    before = (s.parent / "settings.json").read_bytes()
    assert r.returncode == 3, r.stdout + r.stderr
    assert s.read_bytes() == before == json.dumps(live, indent=2).encode()
    assert sorted(p.name for p in s.parent.iterdir()) == ["settings.json", "settings.json.tpl"]
    line = next(ln for ln in r.stdout.splitlines() if ln.startswith(f"CONFLICT {path}"))
    assert all(v in line for v in values), line


def test_template_ask_rule_in_live_allow_is_added_with_a_note(tmp_path):
    r, s = merge(tmp_path, TEMPLATE, {"permissions": {"allow": ["Bash(git push *)"]}})
    assert r.returncode == 0
    assert json.loads(s.read_text())["permissions"]["ask"] == ["Bash(git push *)"]
    assert "note: Bash(git push *) is also in live allow; the template rule wins" in r.stdout


def test_dry_run_prints_planned_changes_and_writes_nothing(tmp_path):
    r, s = merge(tmp_path, TEMPLATE, {"effortLevel": "high"}, "--dry-run")
    assert r.returncode == 0
    assert "add permissions.deny: Bash(rm -rf *)" in r.stdout and "add env.TPL_VAR" in r.stdout
    assert sorted(p.name for p in s.parent.iterdir()) == ["settings.json", "settings.json.tpl"]
    assert json.loads(s.read_text()) == {"effortLevel": "high"}


def test_missing_settings_is_created_from_rendered_template(tmp_path):
    r, s = merge(tmp_path, TEMPLATE, None)
    assert r.returncode == 0
    assert json.loads(s.read_text()) == json.loads(json.dumps(TEMPLATE).replace("__HOME__", str(tmp_path)))


def fake_dotfiles(tmp_path: Path, live: dict) -> Path:
    d = tmp_path / "dotfiles"
    (d / "scripts").mkdir(parents=True)
    shutil.copy(REPO / "scripts" / "install.sh", d / "scripts" / "install.sh")
    if MERGE.exists():
        shutil.copy(MERGE, d / "scripts" / "merge-settings.py")
    write(d / ".claude", TEMPLATE, live)
    (tmp_path / "home").mkdir()
    return d


@pytest.mark.parametrize("live, code", [({"effortLevel": "high"}, 0), ({"env": {"TPL_VAR": "2"}}, 3)])
def test_install_dry_run_settings_changes_no_file(tmp_path, live, code):
    d = fake_dotfiles(tmp_path, live)
    before = tree(tmp_path)
    r = subprocess.run(["bash", str(d / "scripts" / "install.sh"), "--dry-run-settings"], capture_output=True,
                       text=True, env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home")})
    assert tree(tmp_path) == before
    assert r.returncode == code, r.stdout + r.stderr
    assert ("add permissions.deny: Bash(rm -rf *)" if code == 0 else "CONFLICT env.TPL_VAR") in r.stdout


def run_hook(tmp_path: Path, d: Path, install_body: str) -> str:
    (d / "scripts" / "install.sh").write_text(f"touch {tmp_path}/installed\n{install_body}\n")
    return subprocess.run(["bash", str(HOOK)], input='{"source": "clear"}', capture_output=True, text=True,
                          env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path / "home"), "AI_DOTFILES": str(d),
                               "BRAIN_ENV_FILE": "/nonexistent", "BRAIN_LOAD_SLIM": "1"}).stdout


def test_session_start_reports_new_key_drift_without_running_install(tmp_path):
    live = {"enabledPlugins": {"p@m": True}, "extraKnownMarketplaces": TEMPLATE["extraKnownMarketplaces"]}
    d = fake_dotfiles(tmp_path, live)
    out = run_hook(tmp_path, d, "exit 0")
    assert "[install-check] template adds: permissions.deny, permissions.ask, env.TPL_VAR, hooks.PreToolUse" \
           " — run scripts/install.sh" in out
    assert not (tmp_path / "installed").exists()


def test_session_start_prints_conflicts_when_auto_install_exits_3(tmp_path):
    live = {k: v for k, v in TEMPLATE.items() if k != "enabledPlugins"}
    live = json.loads(json.dumps(live).replace("__HOME__", str(tmp_path / "home")))
    d = fake_dotfiles(tmp_path, live)
    out = run_hook(tmp_path, d, 'echo "CONFLICT env.X: live=\\"a\\" template=\\"b\\""; exit 3')
    assert (tmp_path / "installed").exists()
    assert 'CONFLICT env.X: live="a" template="b"' in out
