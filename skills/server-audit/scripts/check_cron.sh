#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
cr = cfg.get("cron", {})
ssh = cfg.get("ssh", {})
target = cr.get("target", "local")
required = cr.get("required_patterns", [])
max_age_hours = int(cr.get("max_age_hours", 24))

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

result = {"check":"cron","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target,"max_age_hours":max_age_hours}}

cron = run(wrap("crontab -l 2>/dev/null || true"))
lines = [x for x in cron.stdout.splitlines() if x.strip() and not x.strip().startswith("#")]
missing = [p for p in required if not any(p in line for line in lines)]
if missing:
    result["status"] = "warn"
    result["severity"] = "medium"
    result["findings"].append(f"Missing expected cron patterns: {', '.join(missing)}")
    result["suggested_fixes"].append("Register required cron entries and deploy crontab.")

journal = run(wrap(f"journalctl --since '{max_age_hours} hour ago' -u cron -u crond --no-pager 2>/dev/null || true"))
hits = [x for x in journal.stdout.splitlines() if "CMD" in x or "cron" in x.lower()]
if not hits:
    result["status"] = "warn" if result["status"] == "pass" else result["status"]
    result["severity"] = "medium" if result["severity"] == "info" else result["severity"]
    result["findings"].append(f"No recent cron execution logs found in last {max_age_hours}h.")
    result["suggested_fixes"].append("Check cron service status, logging config, and schedule frequency.")
else:
    result["evidence"].append(f"Recent cron log lines: {len(hits)}")

result["evidence"].append("\n".join(lines[:20]) if lines else "No crontab entries returned.")
if not result["findings"]:
    result["findings"].append("Cron jobs are registered and recent activity is present.")

print(json.dumps(result, indent=2))
PY
