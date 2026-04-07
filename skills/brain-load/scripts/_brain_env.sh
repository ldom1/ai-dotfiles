# brain-load — resolve BRAIN_PATH (source from load.sh / instantiate.sh)
# shellcheck shell=bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE=""
if [[ -n "${BRAIN_ENV_FILE:-}" ]]; then
  ENV_FILE="${BRAIN_ENV_FILE}"
elif [[ -f "$SCRIPT_DIR/brain.env" ]]; then
  ENV_FILE="$SCRIPT_DIR/brain.env"
else
  ENV_FILE="$(cd "$SCRIPT_DIR/../../.." && pwd)/config/brain.env"
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "[brain-load] ERROR: brain config not found." >&2
  echo "[brain-load] Set BRAIN_ENV_FILE, or add brain.env beside this script, or use ai-dotfiles (config/brain.env)." >&2
  return 1 2>/dev/null || exit 1
fi
# shellcheck source=/dev/null
source "$ENV_FILE"
if [[ -z "${BRAIN_PATH:-}" ]]; then
  echo "[brain-load] ERROR: BRAIN_PATH is not set in $ENV_FILE" >&2
  return 1 2>/dev/null || exit 1
fi
