#!/usr/bin/env bash
# Run sync_dev_projects.py with secrets from the notion-pilot Infisical project (env prod),
# authenticated by a machine identity (Universal Auth). Credentials: CLIENT_ID and CLIENT_SECRET
# in $INFISICAL_IDENTITY_FILE (default ~/.config/infisical/sync-dev-projects.env, mode 600).
# The access token goes through INFISICAL_TOKEN, never on a command line.
set -euo pipefail
IDENTITY_FILE=${INFISICAL_IDENTITY_FILE:-$HOME/.config/infisical/sync-dev-projects.env}
DOMAIN=https://infisical.dombot.tech
PROJECT_ID=71e743d9-5a88-4125-8703-bd75de5fee23
set -a; . "$IDENTITY_FILE"; set +a
INFISICAL_TOKEN=$(infisical login --method=universal-auth --client-id="$CLIENT_ID" \
  --client-secret="$CLIENT_SECRET" --domain "$DOMAIN" --silent --plain)
unset CLIENT_ID CLIENT_SECRET
export INFISICAL_TOKEN
exec infisical run --domain "$DOMAIN" --projectId "$PROJECT_ID" --env prod --silent -- \
  "$(dirname "$(readlink -f "$0")")/sync_dev_projects.py" "$@"
