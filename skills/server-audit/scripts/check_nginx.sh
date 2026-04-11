#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys, urllib.request

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
ng = cfg.get("nginx", {})
ssh = cfg.get("ssh", {})
target = ng.get("target", "local")
endpoints = ng.get("test_endpoints", [])
required_directives = ng.get("require_buffering_directives", [])

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

result = {"check":"nginx","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target}}

rt = run(wrap("nginx -T 2>&1"))
if rt.returncode != 0:
    result.update(status="error", severity="high")
    result["findings"].append("nginx -T failed.")
    result["evidence"].append((rt.stdout + "\n" + rt.stderr).strip()[:500])
    result["suggested_fixes"].append("Fix nginx syntax/runtime issues and rerun nginx -T.")
else:
    blob = rt.stdout.lower()
    missing = [d for d in required_directives if d.lower() not in blob]
    if missing:
        result["status"] = "warn"
        result["severity"] = "medium"
        result["findings"].append(f"Missing buffering directives in nginx config: {', '.join(missing)}")
        result["suggested_fixes"].append("Define the missing proxy buffering directives in active server/location blocks.")
    result["evidence"].append("\n".join(rt.stdout.splitlines()[:30]))

for ep in endpoints:
    url = ep.get("url")
    if not url:
        continue
    expected = int(ep.get("expected_status", 200))
    contains = ep.get("contains")
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read(2048).decode("utf-8", errors="ignore")
            code = int(resp.getcode())
        ok = (code == expected) and (contains in body if contains else True)
        result["evidence"].append(f"{ep.get('name', url)} => status={code}, expected={expected}")
        if not ok:
            result["status"] = "warn"
            result["severity"] = "high"
            result["findings"].append(f"Endpoint check failed: {ep.get('name', url)}")
            result["suggested_fixes"].append("Validate upstream target, proxy pass, auth middleware, and expected response body.")
    except Exception as exc:
        result["status"] = "error"
        result["severity"] = "high"
        result["findings"].append(f"Endpoint unreachable: {ep.get('name', url)}")
        result["evidence"].append(str(exc))
        result["suggested_fixes"].append("Check DNS/TLS/upstream reachability and nginx server_name mapping.")

if not result["findings"]:
    result["findings"].append("All nginx endpoint and buffering checks passed.")

json.dump(result, sys.stdout, indent=2)
PY
