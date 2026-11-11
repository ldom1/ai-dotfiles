"""scripts/orca-install.sh: Orca on native Ubuntu (.deb, guarded), settings, CLI and skills checks.

stdout lines are what the human must do (install.sh repeats them as end warnings); logs go to stderr.
`curl`, `dpkg-query` and `orca-ide` are stubs on PATH; the API JSON has the shape of the GitHub
release API for stablyai/orca v1.4.256 (asset `digest` = "sha256:<hex>").
"""
import hashlib
import json
import shutil
import sqlite3
import subprocess
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
DEB = "orca-ide_1.4.256_amd64.deb"
SKILLS = ("orca-cli", "orca-computer-use", "orchestration")

CURL = """#!/bin/bash
echo "$*" >> "$STUB_LOG/curl"
[[ -n ${CURL_FAIL:-} ]] && exit 22
out=""; while (( $# )); do [[ $1 == -o ]] && { out=$2; shift; }; shift; done
if [[ -n $out ]]; then cp "$STUB_DIR/fake.deb" "$out"; else cat "$STUB_DIR/api.json"; fi
"""
DPKG = """#!/bin/bash
[[ -n ${DPKG_INSTALLED:-} ]] || { echo "dpkg-query: no packages found matching orca-ide" >&2; exit 1; }
printf 'install ok installed\\t1.4.256'
"""
ORCA = """#!/bin/bash
echo "$*" >> "$STUB_LOG/orca-ide"
[[ $1 == --version ]] && { echo 1.4.256; exit 0; }
[[ -n ${ORCA_CLI_FAIL:-} ]] && { echo "Error: cannot reach Orca runtime" >&2; exit 1; }
echo "---"; echo "name: orca-cli"
"""


@pytest.fixture
def env(tmp_path):
    d = tmp_path / "dotfiles"
    for rel in ("scripts/orca-install.sh", "scripts/orca-settings.py", "bin/aif-platform",
                "config/orca/settings.json"):
        (d / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, d / rel)
    for tool in (".claude", ".cursor", ".vibe"):
        for s in SKILLS:
            (d / tool / "skills" / s).mkdir(parents=True)
            (d / tool / "skills" / s / "SKILL.md").write_text(f"---\nname: {s}\n---\n")
    stub, logs, home = tmp_path / "stub", tmp_path / "logs", tmp_path / "home"
    for p in (stub, logs, home):
        p.mkdir()
    (stub / "fake.deb").write_bytes(b"not really a deb")
    digest = hashlib.sha256(b"not really a deb").hexdigest()
    (stub / "api.json").write_text(json.dumps({"tag_name": "v1.4.256", "assets": [
        {"name": "orca-ide-1.4.256.AppImage", "digest": "sha256:" + "0" * 64, "browser_download_url": "u1"},
        {"name": DEB, "digest": f"sha256:{digest}",
         "browser_download_url": f"https://github.com/stablyai/orca/releases/download/v1.4.256/{DEB}"},
    ]}))
    bin_ = tmp_path / "bin"
    bin_.mkdir()
    for name, body in (("curl", CURL), ("dpkg-query", DPKG), ("orca-ide", ORCA)):
        (bin_ / name).write_text(body)
        (bin_ / name).chmod(0o755)
    osr = tmp_path / "os-release"
    osr.write_text('NAME="Ubuntu"\nID=ubuntu\nVERSION_ID="26.04"\n')
    return {"d": d, "stub": stub, "logs": logs, "home": home, "bin": bin_, "osr": osr,
            "dl": tmp_path / "dl", "opt": tmp_path / "opt"}


def run(e, platform="linux", **extra):
    env = {"PATH": f"{e['bin']}:/usr/bin:/bin", "HOME": str(e["home"]), "AIF_PLATFORM": platform,
           "AIF_OS_RELEASE": str(e["osr"]), "ORCA_OPT": str(e["opt"]), "ORCA_DL_DIR": str(e["dl"]),
           "STUB_DIR": str(e["stub"]), "STUB_LOG": str(e["logs"]), **extra}
    return subprocess.run(["bash", str(e["d"] / "scripts" / "orca-install.sh")], capture_output=True,
                          text=True, env=env, timeout=120)


def curl_calls(e) -> list[str]:
    f = e["logs"] / "curl"
    return f.read_text().splitlines() if f.exists() else []


def test_wsl_skips_install(env):
    r = run(env, platform="wsl")
    assert r.returncode == 0, r.stderr
    assert "sudo apt" not in r.stdout
    assert "skipped" in r.stderr and "Windows" in r.stderr
    assert curl_calls(env) == []


def test_non_ubuntu_skips_install(env):
    env["osr"].write_text("ID=fedora\n")
    r = run(env)
    assert r.returncode == 0
    assert "sudo apt" not in r.stdout and "skipped" in r.stderr
    assert curl_calls(env) == []


def test_installed_logs_version(env):
    r = run(env, DPKG_INSTALLED="1")
    assert "sudo apt" not in r.stdout
    assert "1.4.256 already installed" in r.stderr
    assert curl_calls(env) == []


def test_opt_present_skips_install(env):
    env["opt"].mkdir()
    (env["opt"] / "orca-ide").write_text("")
    r = run(env)
    assert "sudo apt" not in r.stdout
    assert curl_calls(env) == []


def test_fresh_ubuntu_prints_apt_line(env):
    r = run(env)
    assert r.returncode == 0, r.stderr
    assert f"sudo apt install {env['dl']}/{DEB}" in r.stdout.splitlines()
    assert (env["dl"] / DEB).read_bytes() == b"not really a deb"


def test_cached_deb_is_not_downloaded_again(env):
    run(env)
    run(env)
    assert sum(" -o " in c for c in curl_calls(env)) == 1


def test_digest_mismatch_deletes_the_file(env):
    (env["stub"] / "fake.deb").write_bytes(b"tampered")
    r = run(env)
    assert r.returncode == 0
    assert "sudo apt" not in r.stdout
    assert not (env["dl"] / DEB).exists()
    assert "sha256 mismatch" in r.stderr


def test_api_failure_continues(env):
    r = run(env, CURL_FAIL="1")
    assert r.returncode == 0
    assert "sudo apt" not in r.stdout
    assert "release" in r.stderr


def test_settings_seeded_on_fresh_linux(env):
    run(env)
    data = json.loads((env["home"] / ".config/orca/profiles/local-default/orca-data.json").read_text())
    assert data["settings"]["theme"] == "dark"


def test_settings_not_touched_on_wsl(env):
    run(env, platform="wsl")
    assert not (env["home"] / ".config" / "orca").exists()


def test_settings_followup_when_orca_runs(env, tmp_path):
    db = env["home"] / ".config/orca/profiles/local-default/profile-state.db"
    db.parent.mkdir(parents=True)
    c = sqlite3.connect(db)
    c.execute("CREATE TABLE profile_state_meta (key TEXT PRIMARY KEY NOT NULL, value TEXT NOT NULL)")
    c.execute("CREATE TABLE profile_state_documents (domain TEXT PRIMARY KEY NOT NULL, payload TEXT NOT NULL,"
              " domain_version INTEGER NOT NULL, revision INTEGER NOT NULL, updated_at INTEGER NOT NULL,"
              " content_hash TEXT NOT NULL)")
    c.execute("INSERT INTO profile_state_meta VALUES ('revision', '1')")
    c.execute("INSERT INTO profile_state_documents VALUES ('settings', '{}', 1, 1, 1, 'x')")
    c.commit()
    c.close()
    p = subprocess.Popen([str(tmp_path / "orca-ide"), "-c", "sleep 30; :"], executable="/bin/bash")
    try:
        time.sleep(0.3)
        r = run(env, DPKG_INSTALLED="1")
    finally:
        p.kill()
    assert any("orca-settings.py apply" in line and "close" in line.lower() for line in r.stdout.splitlines())


def test_cli_check_logs_ok(env):
    r = run(env, DPKG_INSTALLED="1")
    assert "CLI ok" in r.stderr and "1.4.256" in r.stderr
    assert "skills get orca-cli" in (env["logs"] / "orca-ide").read_text()
    assert "orca-ide" not in r.stdout


def test_cli_check_warns_on_failure(env):
    r = run(env, DPKG_INSTALLED="1", ORCA_CLI_FAIL="1")
    assert r.returncode == 0
    assert any("cannot reach Orca runtime" in line for line in r.stdout.splitlines())


def test_cli_missing_on_wsl_warns(env):
    (env["bin"] / "orca-ide").unlink()
    r = run(env, platform="wsl")
    assert any("orca-ide" in line and "Windows" in line for line in r.stdout.splitlines())


def test_orca_skills_linked(env):
    r = run(env, DPKG_INSTALLED="1")
    assert "skill" not in r.stdout
    shutil.rmtree(env["d"] / ".cursor" / "skills" / "orchestration")
    r = run(env, DPKG_INSTALLED="1")
    assert any("orchestration" in line and ".cursor" in line for line in r.stdout.splitlines())
