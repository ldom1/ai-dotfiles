#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
docker = cfg.get("docker", {})
ssh = cfg.get("ssh", {})
target = docker.get("target", "local")
required = docker.get("required_containers", [])
health_required = bool(docker.get("health_required", True))

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

result = {"check":"docker","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target}}
r = run(wrap("docker ps -a --format '{{.Names}}|{{.Status}}|{{.State}}'"))
if r.returncode != 0:
    result.update(status="error", severity="high")
    result["findings"].append("Unable to query Docker containers.")
    result["evidence"].append((r.stderr or r.stdout).strip()[:400])
    result["suggested_fixes"].append("Verify Docker daemon access and SSH target connectivity.")
else:
    lines = [x for x in r.stdout.splitlines() if x.strip()]
    names = []
    unhealthy = 0
    stopped = 0
    for line in lines:
        parts = line.split("|")
        if len(parts) < 3:
            continue
        n, status, state = parts[0], parts[1].lower(), parts[2].lower()
        names.append(n)
        if state != "running":
            stopped += 1
        if health_required and ("unhealthy" in status or "health: starting" in status):
            unhealthy += 1
    missing = [c for c in required if c not in names]
    if missing or stopped or unhealthy:
        result["status"] = "warn"
        result["severity"] = "high" if missing or unhealthy else "medium"
        if missing:
            result["findings"].append(f"Missing required containers: {', '.join(missing)}")
            result["suggested_fixes"].append("Start missing services and verify compose/systemd units.")
        if stopped:
            result["findings"].append(f"Non-running containers detected: {stopped}")
            result["suggested_fixes"].append("Restart failing containers and inspect their logs.")
        if unhealthy:
            result["findings"].append(f"Unhealthy containers detected: {unhealthy}")
            result["suggested_fixes"].append("Fix healthcheck endpoints/commands and redeploy.")
    else:
        result["findings"].append(f"All {len(lines)} containers are running and healthy.")
    result["evidence"].append("\n".join(lines[:20]))

json.dump(result, sys.stdout, indent=2)
PY
