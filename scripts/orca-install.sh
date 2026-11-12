#!/usr/bin/env bash
# orca-install.sh — Orca (the agent cockpit) for ai-dotfiles. Called by install.sh.
#   1. Native Ubuntu only, Orca not installed: download the .deb of the latest stablyai/orca release,
#      check its sha256 against the GitHub asset digest, print the `sudo apt install` line.
#      On WSL, Orca runs on Windows: nothing to install here.
#   2. Native Linux: config/orca/settings.json into Orca's profile (scripts/orca-settings.py):
#      seed before the first launch, apply afterwards (Orca closed).
#   3. Checks the Orca CLI (`orca-ide skills get orca-cli`) and the Orca skills links.
# stdout: one line per thing to do by hand (install.sh repeats them at the end); stderr: log.
# Always exits 0 (2: bad usage). Env overrides (tests): AIF_OS_RELEASE, AIF_PLATFORM, ORCA_OPT,
# ORCA_RELEASE_API, ORCA_DL_DIR.
set -uo pipefail
(( $# == 0 )) || { echo "usage: orca-install.sh" >&2; exit 2; }

DOTFILES=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
OPT=${ORCA_OPT:-/opt/Orca}
API=${ORCA_RELEASE_API:-https://api.github.com/repos/stablyai/orca/releases/latest}
DL=${ORCA_DL_DIR:-${XDG_CACHE_HOME:-$HOME/.cache}/ai-dotfiles/orca}
SETTINGS=(python3 "$DOTFILES/scripts/orca-settings.py")

log()  { echo "✓ Orca: $*" >&2; }
note() { echo "! Orca: $*" >&2; }
todo() { echo "$*"; }

platform=$("$DOTFILES/bin/aif-platform" name)
# shellcheck source=/dev/null
os_id=$(. "${AIF_OS_RELEASE:-/etc/os-release}" 2>/dev/null; echo "${ID:-unknown}")

# Never `command -v orca-ide` to decide: under WSL it finds the Windows-managed CLI.
installed_version() {
  local st
  st=$(dpkg-query -W -f='${Status}\t${Version}' orca-ide 2>/dev/null) || st=""
  if [[ ${st%%$'\t'*} == "install ok installed" ]]; then echo "${st#*$'\t'}"; return 0; fi
  [[ -e $OPT/orca-ide ]] && { echo "(found in $OPT)"; return 0; }
  return 1
}

install_deb() {
  if [[ $platform != linux || $os_id != ubuntu ]]; then
    if [[ $platform == wsl ]]; then
      log "install skipped (WSL: install Orca on Windows; its CLI reaches WSL)"
    else
      log "install skipped (not Ubuntu: ID=$os_id)"
    fi
    return 0
  fi
  local v
  if v=$(installed_version); then log "$v already installed, updates come from Orca"; return 0; fi
  local asset name digest url file sum
  if ! asset=$(curl -fsSL "$API" 2>/dev/null | jq -r 'first(.assets[] | select(.name | endswith("_amd64.deb")))
        | [.name, (.digest // "none"), .browser_download_url] | @tsv' 2>/dev/null) || [[ -z $asset ]]; then
    note "cannot read the latest release from $API: install Orca later, then re-run install.sh"
    return 0
  fi
  IFS=$'\t' read -r name digest url <<<"$asset"
  if [[ ! $name =~ ^orca-ide_[0-9][0-9A-Za-z.+~-]*_amd64\.deb$ || $digest != sha256:* ]]; then
    note "unexpected release asset ($name, digest '${digest:-none}'): nothing downloaded"
    return 0
  fi
  digest=${digest#sha256:}
  mkdir -p "$DL"
  file=$DL/$name
  sum=$( [[ -f $file ]] && sha256sum "$file" | cut -d' ' -f1)
  if [[ $sum != "$digest" ]]; then
    curl -fsSL -o "$file.part" "$url" 2>/dev/null && mv "$file.part" "$file" \
      || { rm -f "$file.part"; note "download failed: $url"; return 0; }
    sum=$(sha256sum "$file" | cut -d' ' -f1)
  fi
  if [[ $sum != "$digest" ]]; then
    rm -f "$file"
    note "sha256 mismatch for $name (got $sum, release says $digest): file deleted"
    return 0
  fi
  log "$name downloaded, sha256 checked"
  todo "sudo apt install $file"
}

settings() {
  [[ $platform == linux ]] || return 0
  "${SETTINGS[@]}" seed || note "settings seed failed"
  local out rc
  out=$("${SETTINGS[@]}" apply); rc=$?
  case $rc in
    0) ;;
    3) todo "Orca is running: close it, then run: python3 $DOTFILES/scripts/orca-settings.py apply" ;;
    4) log "settings seeded: Orca imports them on its first launch" ;;  # seed wrote orca-data.json
    *) todo "Orca settings not applied (exit $rc): python3 $DOTFILES/scripts/orca-settings.py apply" ;;
  esac
  [[ $rc == 4 || -z $out ]] || todo "$out"
}

check_cli() {
  local cli err
  if ! cli=$(command -v orca-ide); then
    if [[ $platform == wsl ]]; then
      todo "orca-ide not on PATH: install Orca on Windows and open it once (it installs its WSL CLI), then open a new terminal"
    elif installed_version >/dev/null; then
      todo "orca-ide not on PATH although Orca is installed: check /usr/bin/orca-ide (deb postinst link)"
    fi
    return 0
  fi
  if err=$(timeout 60 "$cli" skills get orca-cli 2>&1 >/dev/null); then
    log "CLI ok: $cli ($(timeout 60 "$cli" --version 2>/dev/null | head -1))"
  else
    todo "Orca CLI failed: $cli skills get orca-cli: $(head -1 <<<"$err")"
  fi
}

check_skills() {
  local tool s missing=()
  for tool in .claude .cursor .vibe; do
    for s in orca-cli orca-computer-use orchestration; do
      [[ -f $DOTFILES/$tool/skills/$s/SKILL.md ]] || missing+=("$tool/skills/$s")
    done
  done
  if (( ${#missing[@]} )); then
    todo "Orca skills missing: ${missing[*]} (re-run install.sh from the main checkout)"
  else
    log "skills orca-cli, orca-computer-use, orchestration linked for Claude Code, Cursor, Vibe"
  fi
}

install_deb
settings
check_cli
check_skills
exit 0
