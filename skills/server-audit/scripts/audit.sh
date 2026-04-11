#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRIPTS_DIR="$ROOT_DIR/scripts"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
OUT_DIR="$ROOT_DIR/out/$RUN_ID"
CHECKS_DIR="$OUT_DIR/checks"
REPORT_PATH="$OUT_DIR/report.json"
RUNTIME_CONFIG="$OUT_DIR/runtime-config.json"

mkdir -p "$CHECKS_DIR"

ask() {
  local prompt="$1" default="${2:-}"
  if [[ -n "$default" ]]; then
    read -r -p "$prompt [$default]: " v
    echo "${v:-$default}"
  else
    read -r -p "$prompt: " v
    echo "$v"
  fi
}

yn() {
  local prompt="$1" default="${2:-y}"
  local d="y/N"
  [[ "$default" == "y" ]] && d="Y/n"
  read -r -p "$prompt ($d): " v
  v="${v:-$default}"
  [[ "$v" =~ ^[Yy]$ ]]
}

build_interactive_config() {
  local host user port
  host="$(ask "SSH host (empty for local-only checks)" "")"
  user="$(ask "SSH user" "$USER")"
  port="$(ask "SSH port" "22")"

  local use_docker use_nginx use_tailscale use_authelia use_cron use_git
  yn "Run Docker check?" "y" && use_docker=true || use_docker=false
  yn "Run nginx check?" "y" && use_nginx=true || use_nginx=false
  yn "Run Tailscale check?" "y" && use_tailscale=true || use_tailscale=false
  yn "Run Authelia check?" "y" && use_authelia=true || use_authelia=false
  yn "Run cron check?" "y" && use_cron=true || use_cron=false
  yn "Run git repo check?" "y" && use_git=true || use_git=false

  local endpoint1 endpoint2 authelia_portal authelia_protected
  local tailscale_peer1 git_repo1 cron_pattern1
  endpoint1="$(ask "nginx endpoint #1 URL (optional)" "")"
  endpoint2="$(ask "nginx endpoint #2 URL (optional)" "")"
  authelia_portal="$(ask "Authelia portal URL (optional)" "")"
  authelia_protected="$(ask "Authelia protected URL (optional)" "")"
  tailscale_peer1="$(ask "Tailscale peer hostname/IP (optional)" "")"
  cron_pattern1="$(ask "Cron required pattern (optional, e.g. backup.sh)" "")"
  git_repo1="$(ask "Git repo path to validate (optional)" "")"

  python3 - "$RUNTIME_CONFIG" <<PY
import json, sys
out = sys.argv[1]
cfg = {
  "ssh": {"user": "$user", "host": "$host", "port": int("$port")},
  "docker": {"target": "remote" if "$host" else "local", "required_containers": [], "health_required": True},
  "nginx": {
    "target": "remote" if "$host" else "local",
    "test_endpoints": [],
    "require_buffering_directives": ["proxy_buffering", "proxy_buffers", "proxy_busy_buffers_size"]
  },
  "tailscale": {"target": "local", "peer_hosts": []},
  "authelia": {
    "target": "local",
    "portal_url": "$authelia_portal",
    "protected_url": "$authelia_protected",
    "expect_redirect_when_unauthenticated": True,
    "user_env": "AUTHELIA_USER",
    "password_env": "AUTHELIA_PASS"
  },
  "cron": {"target": "remote" if "$host" else "local", "required_patterns": [], "max_age_hours": 24},
  "git": {"target": "remote" if "$host" else "local", "repo_paths": []}
}
if "$endpoint1": cfg["nginx"]["test_endpoints"].append({"name":"endpoint-1","url":"$endpoint1","expected_status":200})
if "$endpoint2": cfg["nginx"]["test_endpoints"].append({"name":"endpoint-2","url":"$endpoint2","expected_status":200})
if "$tailscale_peer1": cfg["tailscale"]["peer_hosts"].append("$tailscale_peer1")
if "$cron_pattern1": cfg["cron"]["required_patterns"].append("$cron_pattern1")
if "$git_repo1": cfg["git"]["repo_paths"].append("$git_repo1")
json.dump(cfg, open(out, "w", encoding="utf-8"), indent=2)
PY

  local checks=()
  [[ "$use_docker" == true ]] && checks+=("docker")
  [[ "$use_nginx" == true ]] && checks+=("nginx")
  [[ "$use_tailscale" == true ]] && checks+=("tailscale")
  [[ "$use_authelia" == true ]] && checks+=("authelia")
  [[ "$use_cron" == true ]] && checks+=("cron")
  [[ "$use_git" == true ]] && checks+=("git")
  printf '%s\n' "${checks[@]}"
}

if [[ -n "${1:-}" ]]; then
  CONFIG_PATH="$1"
  if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "Config not found: $CONFIG_PATH" >&2
    echo "Copy and customize: $ROOT_DIR/config/targets.json.example" >&2
    exit 2
  fi
  mapfile -t checks < <(printf '%s\n' docker nginx tailscale authelia cron git)
elif [[ -t 0 ]]; then
  echo "No config provided: starting interactive setup..."
  mapfile -t checks < <(build_interactive_config)
  CONFIG_PATH="$RUNTIME_CONFIG"
else
  CONFIG_PATH="$ROOT_DIR/config/targets.json"
  if [[ ! -f "$CONFIG_PATH" ]]; then
    echo "Config not found: $CONFIG_PATH" >&2
    echo "Run interactively or copy: $ROOT_DIR/config/targets.json.example" >&2
    exit 2
  fi
  mapfile -t checks < <(printf '%s\n' docker nginx tailscale authelia cron git)
fi

if [[ ${#checks[@]} -eq 0 ]]; then
  echo "No checks selected; nothing to run."
  exit 0
fi

run_check() {
  local name="$1"
  local script="$SCRIPTS_DIR/check_${name}.sh"
  local out="$CHECKS_DIR/${name}.json"

  if [[ ! -x "$script" ]]; then
    python3 - "$name" "$out" <<'PY'
import json, sys
name, out = sys.argv[1], sys.argv[2]
payload = {
    "check": name,
    "status": "error",
    "severity": "high",
    "findings": [f"Check script missing or not executable: check_{name}.sh"],
    "evidence": [],
    "suggested_fixes": [f"chmod +x skills/server-audit/scripts/check_{name}.sh"],
    "meta": {}
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
PY
    return 1
  fi

  if ! "$script" "$CONFIG_PATH" > "$out"; then
    python3 - "$name" "$out" <<'PY'
import json, sys
name, out = sys.argv[1], sys.argv[2]
payload = {
    "check": name,
    "status": "error",
    "severity": "high",
    "findings": [f"Check script failed unexpectedly: check_{name}.sh"],
    "evidence": [],
    "suggested_fixes": ["Inspect script stderr and command prerequisites."],
    "meta": {}
}
with open(out, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
PY
    return 1
  fi
}

for c in "${checks[@]}"; do
  run_check "$c" &
done
wait

python3 "$SCRIPTS_DIR/aggregate.py" "$CHECKS_DIR" "$REPORT_PATH"
echo "Saved report: $REPORT_PATH"
