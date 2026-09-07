#!/usr/bin/env bash
set -euo pipefail
export BRAIN_AGENT_HOOKS=1
exec agent "$@"
