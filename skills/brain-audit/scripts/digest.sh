#!/bin/bash
# brain-audit:digest — reset the maintenance clock (meta/last-maintenance.md).
# The SessionStart hook reads "Epoch Seconds" from that file to print "maintenance due".
# It writes nothing else and does not commit: brain-sync end commits the vault.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$script_dir/_brain_env.sh"

if [[ ! -d "$BRAIN_PATH" ]]; then
    echo "[digest] [ERROR] BRAIN_PATH does not exist: $BRAIN_PATH" >&2
    exit 1
fi

mkdir -p "$BRAIN_PATH/meta"

now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
now_epoch=$(date +%s)

cat > "$BRAIN_PATH/meta/last-maintenance.md" << EOF
$(date -u +"%Y-%m-%d %H:%M:%S")
# Last Maintenance Timestamp

**Timestamp (ISO):** $now
**Epoch Seconds:** $now_epoch

*Updated by digest.sh (brain-audit:digest)*
EOF

echo "[digest] maintenance clock reset: meta/last-maintenance.md ($now)"
