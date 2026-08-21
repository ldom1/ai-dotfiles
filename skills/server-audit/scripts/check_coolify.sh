#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys, urllib.request

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
co = cfg.get("coolify", {})
ssh = cfg.get("ssh", {})
target = co.get("target", "local")
required = co.get("required_containers", ["coolify", "coolify-proxy", "coolify-db", "coolify-redis", "coolify-realtime"])
health_url = co.get("health_url", "")  # optional, probed from the host (e.g. http://localhost:8000/api/health)

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

result = {"check":"coolify","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target}}

ps = run(wrap("docker ps -a --format '{{.Names}}|{{.Status}}|{{.State}}'"))
if ps.returncode != 0:
    result.update(status="error", severity="high")
    result["findings"].append("Unable to query Docker for Coolify containers.")
    result["evidence"].append((ps.stderr or ps.stdout).strip()[:400])
    result["suggested_fixes"].append("Verify Docker daemon access and SSH target connectivity.")
else:
    lines = [x for x in ps.stdout.splitlines() if x.strip()]
    names = {}
    for line in lines:
        parts = line.split("|")
        if len(parts) < 3:
            continue
        n, status, state = parts[0], parts[1].lower(), parts[2].lower()
        names[n] = (status, state)

    missing = [c for c in required if c not in names]
    unhealthy = [c for c in required if c in names and ("unhealthy" in names[c][0] or names[c][1] != "running")]

    if len(missing) == len(required):
        result["findings"].append("Coolify not detected on this host — skipped (not an error).")
        json.dump(result, sys.stdout, indent=2)
        raise SystemExit(0)

    if missing:
        result["status"] = "warn"
        result["severity"] = "high"
        result["findings"].append(f"Missing Coolify containers: {', '.join(missing)}")
        result["suggested_fixes"].append("Check the Coolify install/upgrade — a missing control-plane container usually means an interrupted upgrade or manual `docker rm`.")
    if unhealthy:
        result["status"] = "warn"
        result["severity"] = "high"
        result["findings"].append(f"Unhealthy/non-running Coolify containers: {', '.join(unhealthy)}")
        result["suggested_fixes"].append("Inspect `docker logs <container>` for the affected Coolify service and redeploy if needed.")
    if not missing and not unhealthy:
        result["findings"].append(f"All {len(required)} required Coolify containers are running and healthy.")

    result["evidence"].append("\n".join(f"{n} => {s}/{st}" for n, (s, st) in names.items() if n in required))

if health_url:
    try:
        probe = run(wrap(f"curl -s -o /dev/null -w '%{{http_code}}' --max-time 8 {shlex.quote(health_url)}"))
        code = probe.stdout.strip()
        result["evidence"].append(f"health_url {health_url} => status={code}")
        if not code.startswith("2"):
            result["status"] = "warn"
            result["severity"] = "medium" if result["severity"] == "info" else result["severity"]
            result["findings"].append(f"Coolify health endpoint returned status {code}.")
            result["suggested_fixes"].append("Check the Coolify app container logs for startup/health errors.")
    except Exception as exc:
        result["findings"].append("Coolify health endpoint probe failed.")
        result["evidence"].append(str(exc))

json.dump(result, sys.stdout, indent=2)
PY
