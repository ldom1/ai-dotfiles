"""scripts/orca-settings.py: versioned Orca settings into Orca's SQLite profile db (Linux).

The fixture db uses the schema of Orca 1.4.256 (profile_state_meta + profile_state_documents);
content_hash is the sha256 hex of the payload, updated_at is epoch ms.
"""
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
SCRIPT = REPO / "scripts" / "orca-settings.py"

LIVE = {
    "theme": "system",
    "defaultTuiAgent": "claude",
    "notifications": {"enabled": True, "agentNeedsInput": False, "customSoundId": "system"},
    "voice": {"enabled": False, "dictationMode": "auto", "dictationHoldToRecord": True},
    "terminalFontSize": 13,
}
CONFIG = {
    "theme": "dark",
    "notifications": {"enabled": True, "agentNeedsInput": True},
    "voice": {"enabled": True, "dictationMode": "toggle"},
    "terminalRightClickToPaste": True,
}


def make_db(path: Path, payload: dict, revision: int = 4, meta_revision: int = 8) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    p = json.dumps(payload)
    c = sqlite3.connect(path)
    c.execute("CREATE TABLE profile_state_meta (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL)")
    c.execute("CREATE TABLE profile_state_documents (domain TEXT PRIMARY KEY NOT NULL, payload TEXT NOT NULL,"
              " domain_version INTEGER NOT NULL, revision INTEGER NOT NULL, updated_at INTEGER NOT NULL,"
              " content_hash TEXT NOT NULL)")
    c.executemany("INSERT INTO profile_state_meta VALUES (?, ?)",
                  [("profile_id", "local-default"), ("revision", str(meta_revision))])
    c.execute("INSERT INTO profile_state_documents VALUES ('settings', ?, 1, ?, 1000, ?)",
              (p, revision, hashlib.sha256(p.encode()).hexdigest()))
    c.commit()
    c.close()


def row(db: Path) -> tuple[dict, int, int, str, str, int]:
    c = sqlite3.connect(db)
    p, rev, upd, h = c.execute("SELECT payload, revision, updated_at, content_hash FROM profile_state_documents"
                               " WHERE domain = 'settings'").fetchone()
    meta = int(c.execute("SELECT value FROM profile_state_meta WHERE key = 'revision'").fetchone()[0])
    c.close()
    return json.loads(p), rev, upd, h, p, meta


@pytest.fixture
def orca(tmp_path):
    home = tmp_path / "orca"
    db = home / "profiles" / "local-default" / "profile-state.db"
    cfg = tmp_path / "settings.json"
    cfg.write_text(json.dumps(CONFIG, indent=2, sort_keys=True) + "\n")
    return home, db, cfg


def run(cmd: str, home: Path, cfg: Path, proc_dir: Path | None = None, real_proc: bool = False):
    """ORCA_PROC_DIR for the script: an empty dir by default, so a real Orca on the test machine
    (always running on the target Ubuntu) never turns apply into exit 3; real_proc=True keeps /proc."""
    env = dict(os.environ)
    env.pop("ORCA_PROC_DIR", None)
    if not real_proc:
        proc_dir = proc_dir or home.parent / "no-proc"
        proc_dir.mkdir(parents=True, exist_ok=True)
        env["ORCA_PROC_DIR"] = str(proc_dir)
    return subprocess.run([sys.executable, str(SCRIPT), cmd, "--config", str(cfg), "--orca-home", str(home)],
                          capture_output=True, text=True, timeout=30, env=env)


def fake_proc(root: Path, *procs: tuple[str, list[str]]) -> Path:
    """A /proc tree: one <pid>/exe symlink (target text as given) and <pid>/cmdline per process."""
    for pid, (exe, argv) in enumerate(procs, start=100):
        d = root / str(pid)
        d.mkdir(parents=True)
        (d / "exe").symlink_to(exe)
        (d / "cmdline").write_bytes(b"\0".join(a.encode() for a in argv) + b"\0")
    return root


def fake_process(tmp_path: Path, *args: str, title: str | None = None) -> subprocess.Popen:
    """A process whose executable is named orca-ide (a copy of bash) and whose cmdline is
    `<tmp>/orca-ide -c ... <args>`. title replaces argv0, as Electron rewrites its main process
    title into one string (`/opt/Orca/orca-ide --no-sandbox`, seen on Orca 1.4.256)."""
    exe = tmp_path / "orca-ide"
    if not exe.exists():
        shutil.copy("/bin/bash", exe)
    return subprocess.Popen([title or str(exe), "-c", "sleep 30; :", *args], executable=str(exe))


def test_apply_merges_keys_and_rehashes(orca):
    home, db, cfg = orca
    make_db(db, LIVE)
    r = run("apply", home, cfg)
    assert r.returncode == 0, r.stderr
    s, rev, upd, h, p, meta = row(db)
    assert s["theme"] == "dark"
    assert s["terminalFontSize"] == 13 and s["defaultTuiAgent"] == "claude"
    assert h == hashlib.sha256(p.encode()).hexdigest()
    assert (rev, meta) == (5, 9)
    assert upd > 1000


def test_apply_deep_merges_objects(orca):
    home, db, cfg = orca
    make_db(db, LIVE)
    run("apply", home, cfg)
    s = row(db)[0]
    assert s["notifications"] == {"enabled": True, "agentNeedsInput": True, "customSoundId": "system"}
    assert s["voice"] == {"enabled": True, "dictationMode": "toggle", "dictationHoldToRecord": True}


def test_apply_backs_up_first(orca):
    home, db, cfg = orca
    make_db(db, LIVE)
    before = db.read_bytes()
    run("apply", home, cfg)
    backups = list(db.parent.glob("profile-state.db.bak-*"))
    assert len(backups) == 1
    assert backups[0].read_bytes() == before


def test_apply_noop_when_equal(orca):
    home, db, cfg = orca
    make_db(db, LIVE)
    run("apply", home, cfg)
    after_first = db.read_bytes()
    time.sleep(1.1)  # a second backup would get another name
    r = run("apply", home, cfg)
    assert r.returncode == 0
    assert db.read_bytes() == after_first
    assert len(list(db.parent.glob("profile-state.db.bak-*"))) == 1


def test_apply_sets_key_missing_from_live(orca):
    home, db, cfg = orca
    make_db(db, LIVE)
    run("apply", home, cfg)
    assert row(db)[0]["terminalRightClickToPaste"] is True


def test_apply_uses_active_profile(orca):
    home, _, cfg = orca
    db = home / "profiles" / "work" / "profile-state.db"
    make_db(db, LIVE)
    (home / "orca-profile-index.json").write_text(json.dumps({"schemaVersion": 1, "activeProfileId": "work"}))
    assert run("apply", home, cfg).returncode == 0
    assert row(db)[0]["theme"] == "dark"


def test_apply_without_db_prints_followup(orca):
    home, db, cfg = orca
    r = run("apply", home, cfg)
    assert r.returncode == 4
    lines = r.stdout.strip().splitlines()
    assert len(lines) == 1 and "open Orca once" in lines[0] and "install.sh" in lines[0]
    assert not db.exists()


def test_apply_refuses_when_orca_runs(orca, tmp_path):
    home, db, cfg = orca
    make_db(db, LIVE)
    before = db.read_bytes()
    proc = fake_process(tmp_path, "--no-sandbox")
    try:
        time.sleep(0.3)
        r = run("apply", home, cfg, real_proc=True)
    finally:
        proc.kill()
    assert r.returncode == 3
    assert db.read_bytes() == before
    assert not list(db.parent.glob("profile-state.db.bak-*"))


def test_apply_refuses_when_electron_rewrote_the_title(orca, tmp_path):
    home, db, cfg = orca
    make_db(db, LIVE)
    before = db.read_bytes()
    proc = fake_process(tmp_path, title=f"{tmp_path}/orca-ide --no-sandbox")
    try:
        time.sleep(0.3)
        r = run("apply", home, cfg, real_proc=True)
    finally:
        proc.kill()
    assert r.returncode == 3
    assert db.read_bytes() == before


def test_apply_ignores_other_programs_named_like_orca(orca, tmp_path):
    home, db, cfg = orca
    make_db(db, LIVE)
    proc = fake_proc(tmp_path / "proc", ("/usr/bin/bash", [f"{tmp_path}/orca-ide --no-sandbox"]))
    assert run("apply", home, cfg, proc_dir=proc).returncode == 0

def test_apply_reads_processes_from_orca_proc_dir(orca, tmp_path):
    """ORCA_PROC_DIR isolates the other tests from a real Orca (the target machine always runs one)."""
    home, db, cfg = orca
    make_db(db, LIVE)
    proc = fake_process(tmp_path, "--no-sandbox")
    try:
        time.sleep(0.3)
        r = run("apply", home, cfg, proc_dir=tmp_path / "empty-proc")
    finally:
        proc.kill()
    assert r.returncode == 0, r.stderr


def test_apply_refuses_when_the_orca_binary_was_replaced(orca, tmp_path):
    """An apt upgrade while Orca runs: /proc/<pid>/exe reads `.../orca-ide (deleted)`."""
    home, db, cfg = orca
    make_db(db, LIVE)
    before = db.read_bytes()
    proc = fake_process(tmp_path, "--no-sandbox")
    try:
        time.sleep(0.3)
        (tmp_path / "orca-ide").unlink()
        r = run("apply", home, cfg, real_proc=True)
    finally:
        proc.kill()
    assert r.returncode == 3
    assert db.read_bytes() == before


def test_versioned_config_has_no_machine_specific_keys():
    """Deep merge keeps live sub-keys absent from the file: device ids, model paths and lists that
    differ per machine must not be versioned, or apply resets them on every install.sh run."""
    cfg = json.loads((REPO / "config" / "orca" / "settings.json").read_text())
    machine = {"notifications": {"customSoundPath", "mutedNotificationSourceIds"},
               "voice": {"microphoneDeviceId", "microphoneDeviceLabel", "modelsDir", "openAiApiKeyConfigured",
                         "sttModel", "userModels"}}
    for key, subs in machine.items():
        assert not subs & set(cfg[key]), (key, sorted(subs & set(cfg[key])))


def test_apply_ignores_daemon_and_children(orca, tmp_path):
    home, db, cfg = orca
    make_db(db, LIVE)
    exe = "/opt/Orca/orca-ide"
    proc = fake_proc(tmp_path / "proc",
                     (exe, [exe, "--max-semi-space-size=4", "/opt/Orca/resources/app.asar.unpacked/out/main/daemon-entry.js"]),
                     (exe, [exe, "/opt/Orca/resources/app.asar.unpacked/out/main/parcel-watcher-process-entry.js"]),
                     (exe, [f"{exe} --type=zygote --no-sandbox"]))
    r = run("apply", home, cfg, proc_dir=proc)
    assert r.returncode == 0, r.stderr
    assert row(db)[0]["theme"] == "dark"


def test_apply_refuses_on_a_main_process_in_a_fake_proc(orca, tmp_path):
    home, db, cfg = orca
    make_db(db, LIVE)
    proc = fake_proc(tmp_path / "proc", ("/opt/Orca/orca-ide (deleted)", ["/opt/Orca/orca-ide --no-sandbox"]))
    assert run("apply", home, cfg, proc_dir=proc).returncode == 3

def test_export_roundtrip(orca):
    home, db, cfg = orca
    make_db(db, {**LIVE, "notifications": {"enabled": False, "agentNeedsInput": True, "customSoundId": "x"}})
    r = run("export", home, cfg)
    assert r.returncode == 0
    out = json.loads(cfg.read_text())
    assert set(out) == set(CONFIG)
    assert out["theme"] == "system"
    assert out["notifications"] == {"enabled": False, "agentNeedsInput": True}  # config's subkeys only
    assert out["terminalRightClickToPaste"] is True  # absent live: kept, warned
    assert "terminalRightClickToPaste" in r.stderr
    assert cfg.read_text().endswith("}\n")


def test_seed_writes_legacy_json_when_absent(orca):
    home, db, cfg = orca
    r = run("seed", home, cfg)
    assert r.returncode == 0, r.stderr
    data = json.loads((db.parent / "orca-data.json").read_text())
    assert data == {"settings": {**CONFIG, "claudeCodeThemeSyncOffer": "settled",
                                 "terminalRightClickToPasteDefaultedForPlatform": True}}
    index = json.loads((home / "orca-profile-index.json").read_text())
    assert index["activeProfileId"] == "local-default"
    assert [p["id"] for p in index["profiles"]] == ["local-default"]
    assert not db.exists()


def test_seed_noop_when_db_exists(orca):
    home, db, cfg = orca
    make_db(db, LIVE)
    before = db.read_bytes()
    assert run("seed", home, cfg).returncode == 0
    assert db.read_bytes() == before
    assert not (db.parent / "orca-data.json").exists()


def test_seed_noop_when_json_exists(orca):
    home, db, cfg = orca
    j = db.parent / "orca-data.json"
    j.parent.mkdir(parents=True)
    j.write_text('{"settings": {"theme": "light"}}')
    assert run("seed", home, cfg).returncode == 0
    assert json.loads(j.read_text()) == {"settings": {"theme": "light"}}
