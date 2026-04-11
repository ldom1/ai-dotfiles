#!/usr/bin/env bash
set -euo pipefail
python3 - "$1" <<'PY'
import json, shlex, subprocess, sys

cfg = json.load(open(sys.argv[1], encoding="utf-8"))
git_cfg = cfg.get("git", {})
ssh = cfg.get("ssh", {})
target = git_cfg.get("target", "local")
repos = git_cfg.get("repo_paths", [])

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

result = {"check":"git","status":"pass","severity":"info","findings":[],"evidence":[],"suggested_fixes":[],"meta":{"target":target}}

if not repos:
    result["status"] = "warn"
    result["severity"] = "low"
    result["findings"].append("No git.repo_paths configured.")
    result["suggested_fixes"].append("Set git.repo_paths in targets.json for repo integrity checks.")
    print(json.dumps(result, indent=2))
    raise SystemExit(0)

dirty = []
embedded = []
for path in repos:
    cmd = (
        f"if [ -d {shlex.quote(path)}/.git ]; then "
        f"cd {shlex.quote(path)} && "
        "echo '---STATUS---' && git status --porcelain && "
        "echo '---EMBED---' && git submodule status --recursive 2>/dev/null || true; "
        "else echo '__NOT_REPO__'; fi"
    )
    r = run(wrap(cmd))
    out = (r.stdout or "").strip()
    if "__NOT_REPO__" in out:
        result["status"] = "warn"
        result["severity"] = "medium"
        result["findings"].append(f"Path is not a git repo: {path}")
        continue
    parts = out.split("---EMBED---")
    status_block = parts[0].split("---STATUS---")[-1].strip() if parts else ""
    embed_block = parts[1].strip() if len(parts) > 1 else ""
    if status_block:
        dirty.append(path)
        result["evidence"].append(f"{path}: dirty entries present")
    if "fatal: no submodule mapping found" in embed_block.lower():
        embedded.append(path)
        result["evidence"].append(f"{path}: embedded-repo warning detected")

if dirty or embedded:
    result["status"] = "warn"
    result["severity"] = "high" if embedded else "medium"
    if dirty:
        result["findings"].append(f"Dirty git repos: {', '.join(dirty)}")
        result["suggested_fixes"].append("Commit/stash/discard local changes before deploy operations.")
    if embedded:
        result["findings"].append(f"Embedded repo/submodule mapping warnings: {', '.join(embedded)}")
        result["suggested_fixes"].append("Fix nested repo boundaries or .gitmodules mappings.")
else:
    result["findings"].append("All configured git repos are clean with no embedded-repo warnings.")

print(json.dumps(result, indent=2))
PY
