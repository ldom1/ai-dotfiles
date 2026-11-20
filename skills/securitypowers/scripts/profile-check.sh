#!/usr/bin/env bash
# Is the project's .agents/security-profile.md present and fresh?
# Usage: profile-check.sh [--hash] <project_dir>
#   prints ok | missing | stale: <reason>   (exit 0 | 1 | 2)
#   --hash prints the sha256 of the files listed under `sources:` (to write into sources_sha256)
# Env: PROFILE_MAX_AGE_DAYS (default 90), TODAY (YYYY-MM-DD, default today).
set -euo pipefail

hash_only=0
if [[ "${1:-}" == "--hash" ]]; then hash_only=1; shift; fi
project="${1:?usage: profile-check.sh [--hash] <project_dir>}"
profile="$project/.agents/security-profile.md"
max_age="${PROFILE_MAX_AGE_DAYS:-90}"
today="${TODAY:-$(date -u +%F)}"

if [[ ! -f "$profile" ]]; then echo "missing"; exit 1; fi

# Front matter only: lines between the first two `---`.
front=$(awk 'NR==1 && $0!="---"{exit} NR>1 && $0=="---"{exit} NR>1{print}' "$profile")
field() { sed -n "s/^$1:[[:space:]]*//p" <<<"$front" | head -n1; }
mapfile -t sources < <(awk '/^sources:/{on=1; next} on && /^[[:space:]]*-[[:space:]]/{sub(/^[[:space:]]*-[[:space:]]*/, ""); print; next} on{on=0}' <<<"$front")

current_hash() {
  local s
  for s in "${sources[@]}"; do
    if [[ ! -f "$project/$s" ]]; then echo "missing:$s"; return; fi
  done
  for s in "${sources[@]}"; do cat "$project/$s"; done | sha256sum | cut -d' ' -f1
}

digest=$(current_hash)
if (( hash_only )); then
  if [[ "$digest" == missing:* ]]; then echo "source missing ${digest#missing:}" >&2; exit 2; fi
  echo "$digest"; exit 0
fi

reviewed=$(field reviewed)
if [[ -z "$reviewed" ]]; then echo "stale: no reviewed date"; exit 2; fi
if [[ ! "$reviewed" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || ! reviewed_s=$(date -u -d "$reviewed" +%s 2>/dev/null); then
  echo "stale: bad reviewed date '$reviewed'"; exit 2
fi
age=$(( ( $(date -u -d "$today" +%s) - reviewed_s ) / 86400 ))
if (( age > max_age )); then echo "stale: reviewed $age days ago"; exit 2; fi
if [[ "$digest" == missing:* ]]; then echo "stale: source missing ${digest#missing:}"; exit 2; fi
if [[ "$digest" != "$(field sources_sha256)" ]]; then echo "stale: sources changed"; exit 2; fi
echo "ok"
