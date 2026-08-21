#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys, urllib.error, urllib.request

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
net = cfg.get("network", {})
ssh = cfg.get("ssh", {})
target = net.get("target", "local")
endpoints = net.get("test_endpoints", [])
required_directives = net.get("require_buffering_directives", [])
traefik_container = net.get("traefik_container", "")

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

result = {"check":"network","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target}}

# --- nginx: check only if the binary is present on this host, skip gracefully otherwise ---
has_nginx = run(wrap("command -v nginx")).returncode == 0
if not has_nginx:
    result["findings"].append("nginx not present on this host — skipped (not an error).")
elif required_directives:
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
else:
    result["evidence"].append("nginx present; no buffering directives configured to check.")

# --- Traefik: check only if a matching container is present, skip gracefully otherwise ---
ps = run(wrap("docker ps --format '{{.Names}}|{{.Image}}|{{.Status}}'"))
traefik_line = None
if ps.returncode == 0:
    for line in ps.stdout.splitlines():
        parts = line.split("|")
        if len(parts) < 3:
            continue
        name, image, status = parts[0], parts[1], parts[2]
        if traefik_container:
            if name == traefik_container:
                traefik_line = (name, image, status)
                break
        elif "traefik" in name.lower() or "traefik" in image.lower():
            traefik_line = (name, image, status)
            break

if traefik_line:
    name, image, status = traefik_line
    result["evidence"].append(f"Traefik container: {name} ({image}) => {status}")
    if "unhealthy" not in status.lower() and ("up" in status.lower()):
        result["findings"].append(f"Traefik container '{name}' is running.")
    else:
        result["status"] = "warn"
        result["severity"] = "high" if result["severity"] in ("info",) else result["severity"]
        result["findings"].append(f"Traefik container '{name}' is not healthy/running: {status}")
        result["suggested_fixes"].append(f"Inspect `docker logs {name}` and redeploy the proxy stack.")
else:
    result["findings"].append("Traefik not present on this host — skipped (not an error).")

if not has_nginx and not traefik_line:
    result["findings"].append("No reverse proxy (nginx or Traefik) detected on this host.")

# --- endpoint reachability (independent of which proxy is in front, if any) ---
_no_redirect_handler = urllib.request.HTTPRedirectHandler()
_no_redirect_handler.redirect_request = lambda *a, **k: None
no_redirect_opener = urllib.request.build_opener(_no_redirect_handler)

for ep in endpoints:
    url = ep.get("url")
    if not url:
        continue
    expected = int(ep.get("expected_status", 200))
    contains = ep.get("contains")
    try:
        req = urllib.request.Request(url, method="GET")
        try:
            with no_redirect_opener.open(req, timeout=10) as resp:
                body = resp.read(2048).decode("utf-8", errors="ignore")
                code = int(resp.getcode())
        except urllib.error.HTTPError as redirect_exc:
            code = redirect_exc.code
            body = redirect_exc.read(2048).decode("utf-8", errors="ignore")
        ok = (code == expected) and (contains in body if contains else True)
        result["evidence"].append(f"{ep.get('name', url)} => status={code}, expected={expected}")
        if not ok:
            result["status"] = "warn"
            result["severity"] = "high"
            result["findings"].append(f"Endpoint check failed: {ep.get('name', url)}")
            result["suggested_fixes"].append("Validate upstream target, proxy routing, auth middleware, and expected response body.")
    except Exception as exc:
        result["status"] = "error"
        result["severity"] = "high"
        result["findings"].append(f"Endpoint unreachable: {ep.get('name', url)}")
        result["evidence"].append(str(exc))
        result["suggested_fixes"].append("Check DNS/TLS/upstream reachability and reverse-proxy routing rules.")

json.dump(result, sys.stdout, indent=2)
PY
