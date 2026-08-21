#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
sd = cfg.get("systemd", {})
ssh = cfg.get("ssh", {})
target = sd.get("target", "local")
required_services = sd.get("required_services", [])

def run(cmd):
    return subprocess.run(cmd, shell=True, text=True, capture_output=True)

def wrap(cmd):
    if target != "remote":
        return cmd
    user = ssh.get("user", "")
    host = ssh.get("host", "")
    port = int(ssh.get("port", 22))
    remote = f"{user}@{host}" if user else host
    return f"ssh -o BatchMode=yes -o ConnectTimeout=8 -p {port} {shlex.quote(remote)} {shlex.quote('bash -lc ' + shlex.quote(cmd))}"

result = {"check":"systemd","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target}}

failed = run(wrap("systemctl --failed --no-legend --plain"))
if failed.returncode != 0 and not failed.stdout.strip():
    result.update(status="error", severity="high")
    result["findings"].append("Unable to query systemd for failed units.")
    result["evidence"].append((failed.stderr or failed.stdout).strip()[:400])
    result["suggested_fixes"].append("Verify systemd access and SSH target connectivity.")
else:
    failed_units = [x.split()[0] for x in failed.stdout.splitlines() if x.strip()]
    if failed_units:
        result["status"] = "warn"
        result["severity"] = "high"
        result["findings"].append(f"Failed systemd units: {', '.join(failed_units)}")
        result["suggested_fixes"].append("Run `journalctl -u <unit> -p err` on each failed unit to diagnose.")
        result["evidence"].append("\n".join(failed_units))
    else:
        result["findings"].append("No failed systemd units.")
        result["evidence"].append("systemctl --failed: none")

inactive = []
for svc in required_services:
    r = run(wrap(f"systemctl is-active {shlex.quote(svc)} 2>/dev/null || true"))
    state = r.stdout.strip()
    result["evidence"].append(f"{svc} => {state or 'unknown'}")
    if state != "active":
        inactive.append(f"{svc} ({state or 'unknown'})")

if inactive:
    result["status"] = "warn"
    result["severity"] = "high"
    result["findings"].append(f"Required services not active: {', '.join(inactive)}")
    result["suggested_fixes"].append("Start/enable the affected services and check their unit logs.")

json.dump(result, sys.stdout, indent=2)
PY
