#!/bin/bash
# Config loader for brain-route — source this to get BRAIN_PATH

set -euo pipefail

# Determine BRAIN_PATH from three possible sources
_load_brain_path() {
    # Priority 1: BRAIN_ENV_FILE environment variable
    if [[ -n "${BRAIN_ENV_FILE:-}" && -f "$BRAIN_ENV_FILE" ]]; then
        # shellcheck disable=SC1090
        source "$BRAIN_ENV_FILE"
        if [[ -z "${BRAIN_PATH:-}" ]]; then
            echo "[brain-route] BRAIN_ENV_FILE set but BRAIN_PATH not defined in $BRAIN_ENV_FILE" >&2
            return 1
        fi
        return 0
    fi

    # Priority 2: brain.env beside this script
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    local brain_env_local="$script_dir/../reference/brain.env"
    if [[ -f "$brain_env_local" ]]; then
        # shellcheck disable=SC1090
        source "$brain_env_local"
        if [[ -z "${BRAIN_PATH:-}" ]]; then
            echo "[brain-route] brain.env found but BRAIN_PATH not defined" >&2
            return 1
        fi
        return 0
    fi

    # Priority 3: config/brain.env at ai-dotfiles root
    local ai_dotfiles_root="${HOME}/ai-dotfiles"
    local brain_env_config="$ai_dotfiles_root/config/brain.env"
    if [[ -f "$brain_env_config" ]]; then
        # shellcheck disable=SC1090
        source "$brain_env_config"
        if [[ -z "${BRAIN_PATH:-}" ]]; then
            echo "[brain-route] config/brain.env found but BRAIN_PATH not defined" >&2
            return 1
        fi
        return 0
    fi

    echo "[brain-route] BRAIN_PATH not found. Set BRAIN_ENV_FILE, create brain.env, or configure config/brain.env" >&2
    return 1
}

_load_brain_path
