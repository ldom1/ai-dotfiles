#!/usr/bin/env bash
set -euo pipefail

TARGET="${1:-}"
PORT="${2:-22}"
SSH_OPTS=(-o BatchMode=yes -o ConnectTimeout=8 -o ServerAliveInterval=5 -o ServerAliveCountMax=2 -p "$PORT")

run_remote() {
  local cmd="$1"
  if [[ -n "$TARGET" ]]; then
    ssh "${SSH_OPTS[@]}" "$TARGET" "bash -lc '$cmd'" 2>&1 || true
  else
    bash -lc "$cmd" 2>&1 || true
  fi
}

declare -a OUT=()
c_critical=0; c_high=0; c_medium=0; c_low=0; c_info=0; i=0

add() {
  local sev="$1" msg="$2"
  i=$((i + 1))
  OUT+=("$i. [$sev] $msg")
  case "$sev" in
    CRITICAL) c_critical=$((c_critical + 1)) ;;
    HIGH) c_high=$((c_high + 1)) ;;
    MEDIUM) c_medium=$((c_medium + 1)) ;;
    LOW) c_low=$((c_low + 1)) ;;
    INFO) c_info=$((c_info + 1)) ;;
  esac
}

docker_out="$(run_remote "command -v docker >/dev/null && docker ps -a --format '{{.Names}} {{.Status}}' || echo '__NO_DOCKER__'")"
if [[ "$docker_out" == *"__NO_DOCKER__"* ]]; then
  add LOW "Docker not installed or unavailable."
else
  exited_count="$(printf '%s\n' "$docker_out" | grep -Eci "exited|dead" || true)"
  restarting_count="$(printf '%s\n' "$docker_out" | grep -Eci "restarting" || true)"
  (( restarting_count > 0 )) && add HIGH "Docker containers restarting: $restarting_count."
  (( exited_count > 0 )) && add MEDIUM "Stopped/dead Docker containers: $exited_count."
  (( restarting_count == 0 && exited_count == 0 )) && add INFO "Docker containers look healthy."
fi

nginx_out="$(run_remote "command -v nginx >/dev/null && nginx -T 2>&1 | head -50 || echo '__NO_NGINX__'")"
if [[ "$nginx_out" == *"__NO_NGINX__"* ]]; then
  add LOW "nginx not installed."
elif [[ "$nginx_out" == *"emerg"* || "$nginx_out" == *"failed"* ]]; then
  add HIGH "nginx reports config/runtime errors. Inspect nginx -T output."
else
  add INFO "nginx config dump succeeded."
fi

failed_units="$(run_remote "command -v systemctl >/dev/null && systemctl --failed --no-legend --plain || echo '__NO_SYSTEMD__'")"
if [[ "$failed_units" == *"__NO_SYSTEMD__"* ]]; then
  add LOW "systemd not available."
else
  n_failed="$(printf '%s\n' "$failed_units" | grep -Ec "failed" || true)"
  (( n_failed > 0 )) && add HIGH "Failed systemd units: $n_failed."
  (( n_failed == 0 )) && add INFO "No failed systemd units."
fi

df_out="$(run_remote "df -h --output=pcent,target 2>/dev/null || df -h")"
critical_fs="$(printf '%s\n' "$df_out" | grep -En "([9][5-9]%|100%)" || true)"
high_fs="$(printf '%s\n' "$df_out" | grep -En "([9][0-4]%)" || true)"
if [[ -n "$critical_fs" ]]; then
  add CRITICAL "Filesystem usage >=95% detected."
elif [[ -n "$high_fs" ]]; then
  add HIGH "Filesystem usage >=90% detected."
else
  add INFO "Disk usage below 90%."
fi

journal_out="$(run_remote "command -v journalctl >/dev/null && journalctl --since '1 hour ago' -p err --no-pager || echo '__NO_JOURNAL__'")"
if [[ "$journal_out" == *"__NO_JOURNAL__"* ]]; then
  add LOW "journalctl not available."
else
  err_count="$(printf '%s\n' "$journal_out" | grep -Ec "." || true)"
  (( err_count > 20 )) && add HIGH "journalctl has many recent errors ($err_count lines)."
  (( err_count > 0 && err_count <= 20 )) && add MEDIUM "journalctl has recent errors ($err_count lines)."
  (( err_count == 0 )) && add INFO "No error-level journal entries in the last hour."
fi

printf '%s\n' "${OUT[@]}"
echo
echo "Summary: CRITICAL=$c_critical HIGH=$c_high MEDIUM=$c_medium LOW=$c_low INFO=$c_info"
