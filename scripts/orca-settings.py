#!/usr/bin/env python3
"""Versioned Orca settings (config/orca/settings.json) in and out of Orca's profile db. Linux only.

Usage: orca-settings.py {apply,export,seed} [--config PATH] [--orca-home PATH]
  apply   merge the versioned keys into the active profile's settings (Orca must be closed;
          backs up profile-state.db first; does nothing when the values are already there)
  export  rewrite the config file from the live settings (same keys and sub-keys)
  seed    before Orca's first launch: write orca-data.json, which Orca imports into a new db
Exit: 0 done or nothing to do, 2 usage, 3 Orca is running (nothing written), 4 no profile db yet.
stdout carries only a command a human must run next; logs go to stderr.

Orca 1.4.256 stores settings in profiles/<id>/profile-state.db, table profile_state_documents,
row domain='settings': payload JSON, content_hash = sha256 hex of payload, revision, updated_at
(epoch ms); profile_state_meta holds a global revision. Orca has no settings CLI (upstream #21767).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
DEFAULT_PROFILE = "local-default"
# One-time Orca migrations reset these two keys on a legacy-JSON import unless their flags are set
# (spike 2026-11-11): claudeCodeThemeSync and terminalRightClickToPaste.
SEED_FLAGS = {"claudeCodeThemeSyncOffer": "settled", "terminalRightClickToPasteDefaultedForPlatform": True}


def log(msg: str) -> None:
    print(f"orca-settings: {msg}", file=sys.stderr)


def profile_dir(orca_home: Path) -> Path:
    try:
        active = json.loads((orca_home / "orca-profile-index.json").read_text())["activeProfileId"]
    except (OSError, ValueError, KeyError, TypeError):
        active = DEFAULT_PROFILE
    return orca_home / "profiles" / str(active)


def orca_running(proc: Path | None = None) -> bool:
    """True when an Orca main process runs. Every Orca process runs the orca-ide executable
    (/proc/<pid>/exe); Electron rewrites the main title into one string, so argv0 is not reliable.
    Main = no --type= (Chromium children) and no .js entry (daemon, file watcher: they do not hold
    the db). Processes of other users are skipped (no access to exe). An apt upgrade while Orca
    runs leaves exe as `.../orca-ide (deleted)`. ORCA_PROC_DIR replaces /proc (tests)."""
    proc = proc or Path(os.environ.get("ORCA_PROC_DIR") or "/proc")
    for exe in proc.glob("[0-9]*/exe"):
        try:
            if Path(str(exe.readlink()).removesuffix(" (deleted)")).name != "orca-ide":
                continue
            cmdline = (exe.parent / "cmdline").read_bytes().replace(b"\0", b" ").decode(errors="replace")
        except OSError:
            continue
        words = cmdline.split()
        if not any(w.startswith("--type=") or w.endswith(".js") for w in words):
            return True
    return False


def deep_merge(live: object, wanted: object) -> object:
    if isinstance(live, dict) and isinstance(wanted, dict):
        out = dict(live)
        for k, v in wanted.items():
            out[k] = deep_merge(live.get(k), v)
        return out
    return copy.deepcopy(wanted)


def pick(live: object, shape: object) -> object:
    """Live value restricted to the keys of shape (shape's value when live lacks one)."""
    if isinstance(shape, dict) and isinstance(live, dict):
        return {k: pick(live[k], v) if k in live else v for k, v in shape.items()}
    return live


def read_config(path: Path) -> dict:
    return json.loads(path.read_text())


def apply(config: Path, orca_home: Path) -> int:
    db = profile_dir(orca_home) / "profile-state.db"
    if not db.exists():
        print(f"Orca has no profile yet: open Orca once, close it, then run: bash {REPO}/scripts/install.sh")
        return 4
    if orca_running():
        log("Orca is running: close it first (nothing written)")
        return 3
    wanted = read_config(config)
    con = sqlite3.connect(db)
    try:
        payload, revision = con.execute(
            "SELECT payload, revision FROM profile_state_documents WHERE domain = 'settings'").fetchone()
        live = json.loads(payload)
        merged = deep_merge(live, wanted)
        if merged == live:
            log(f"{db}: settings already up to date")
            return 0
        backup = db.with_name(f"{db.name}.bak-{time.strftime('%Y%m%d-%H%M%S')}")
        con.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        shutil.copy2(db, backup)
        new = json.dumps(merged, separators=(",", ":"))
        with con:
            con.execute("UPDATE profile_state_documents SET payload = ?, content_hash = ?, revision = ?,"
                        " updated_at = ? WHERE domain = 'settings'",
                        (new, hashlib.sha256(new.encode()).hexdigest(), revision + 1, int(time.time() * 1000)))
            meta = int(con.execute("SELECT value FROM profile_state_meta WHERE key = 'revision'").fetchone()[0])
            con.execute("UPDATE profile_state_meta SET value = ? WHERE key = 'revision'", (str(meta + 1),))
    finally:
        con.close()
    changed = sorted(k for k in wanted if live.get(k) != merged.get(k))
    log(f"{db}: applied {', '.join(changed)} (backup {backup.name})")
    return 0


def export(config: Path, orca_home: Path) -> int:
    db = profile_dir(orca_home) / "profile-state.db"
    if not db.exists():
        log(f"no profile db at {db}")
        return 4
    con = sqlite3.connect(db)
    try:
        live = json.loads(con.execute(
            "SELECT payload FROM profile_state_documents WHERE domain = 'settings'").fetchone()[0])
    finally:
        con.close()
    shape = read_config(config)
    for k in shape:
        if k not in live:
            log(f"warning: {k} is not in Orca's live settings, kept as is")
    out = {k: pick(live[k], v) if k in live else v for k, v in shape.items()}
    config.write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    log(f"{config} updated from {db}")
    return 0


def seed(config: Path, orca_home: Path) -> int:
    pdir = profile_dir(orca_home)
    db, legacy = pdir / "profile-state.db", pdir / "orca-data.json"
    if db.exists() or legacy.exists():
        log(f"{pdir}: Orca profile already exists, no seed")
        return 0
    pdir.mkdir(parents=True, exist_ok=True)
    index = orca_home / "orca-profile-index.json"
    if not index.exists():
        now = int(time.time() * 1000)
        index.write_text(json.dumps({
            "schemaVersion": 1, "activeProfileId": pdir.name,
            "profiles": [{"id": pdir.name, "name": "Personal",
                          "avatar": {"kind": "initials", "initials": "P", "color": "neutral"},
                          "kind": "local", "createdAt": now, "updatedAt": now, "lastOpenedAt": now}],
        }, indent=2) + "\n")
    legacy.write_text(json.dumps({"settings": {**read_config(config), **SEED_FLAGS}}, indent=2) + "\n")
    log(f"{legacy} written: Orca imports it on first launch")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("command", choices=["apply", "export", "seed"])
    ap.add_argument("--config", type=Path, default=REPO / "config" / "orca" / "settings.json")
    xdg = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    ap.add_argument("--orca-home", type=Path, default=Path(xdg) / "orca")
    a = ap.parse_args()
    return {"apply": apply, "export": export, "seed": seed}[a.command](a.config, a.orca_home)


if __name__ == "__main__":
    sys.exit(main())
