#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
ts = cfg.get("tailscale", {})
ssh = cfg.get("ssh", {})
target = ts.get("target", "local")
peers = ts.get("peer_hosts", [])

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

result = {"check":"tailscale","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target}}

st = run(wrap("tailscale status --json"))
if st.returncode != 0:
    result.update(status="error", severity="high")
    result["findings"].append("tailscale status unavailable.")
    result["evidence"].append((st.stderr or st.stdout).strip()[:400])
    result["suggested_fixes"].append("Verify tailscaled is running and node is authenticated.")
    print(json.dumps(result, indent=2))
    raise SystemExit(0)

try:
    payload = json.loads(st.stdout or "{}")
except Exception:
    payload = {}
peermap = payload.get("Peer", {}) if isinstance(payload, dict) else {}
offline = []
missing = []
for host in peers:
    matched = None
    for _, peer in peermap.items():
        if peer.get("HostName") == host or peer.get("DNSName", "").startswith(host + "."):
            matched = peer
            break
    if not matched:
        missing.append(host)
        continue
    if not matched.get("Online", False):
        offline.append(host)

if missing or offline:
    result["status"] = "warn"
    result["severity"] = "high" if offline else "medium"
    if missing:
        result["findings"].append(f"Configured peers not found in tailscale network: {', '.join(missing)}")
        result["suggested_fixes"].append("Confirm peer hostnames and ACL visibility.")
    if offline:
        result["findings"].append(f"Tailscale peers offline: {', '.join(offline)}")
        result["suggested_fixes"].append("Bring peers online and verify tunnels/routes.")
else:
    result["findings"].append("All configured Tailscale peers are visible and online.")

result["evidence"].append(f"Peer count observed: {len(peermap)}")
print(json.dumps(result, indent=2))
PY
