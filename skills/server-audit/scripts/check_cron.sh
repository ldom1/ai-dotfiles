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

# Fallback: many modern hosts schedule jobs via systemd timers instead of crontab.
timers = run(wrap("systemctl list-timers --all --no-legend 2>/dev/null || true"))
timer_lines = [x for x in timers.stdout.splitlines() if x.strip()]

missing = [p for p in required if not any(p in line for line in lines) and not any(p.replace(".sh", "") in line or p in line for line in timer_lines)]
if missing:
    result["status"] = "warn"
    result["severity"] = "medium"
    result["findings"].append(f"Missing expected cron/systemd-timer patterns: {', '.join(missing)}")
    result["suggested_fixes"].append("Register required cron entries or systemd timers for these jobs.")

journal = run(wrap(f"journalctl --since '{max_age_hours} hour ago' -u cron -u crond --no-pager 2>/dev/null || true"))
hits = [x for x in journal.stdout.splitlines() if "CMD" in x or "cron" in x.lower()]
if not hits and not timer_lines:
    result["status"] = "warn" if result["status"] == "pass" else result["status"]
    result["severity"] = "medium" if result["severity"] == "info" else result["severity"]
    result["findings"].append(f"No recent cron execution logs or active systemd timers found in last {max_age_hours}h.")
    result["suggested_fixes"].append("Check cron/systemd-timer service status, logging config, and schedule frequency.")
elif hits:
    result["evidence"].append(f"Recent cron log lines: {len(hits)}")

result["evidence"].append("\n".join(lines[:20]) if lines else "No crontab entries returned.")
result["evidence"].append("\n".join(timer_lines[:20]) if timer_lines else "No systemd timers returned.")
if not result["findings"]:
    result["findings"].append("Cron jobs are registered and recent activity is present.")

print(json.dumps(result, indent=2))
PY
