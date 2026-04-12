#!/usr/bin/env bash
set -euo pipefail

# Load configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/_config.sh"

# Default flags
OUTPUT_FORMAT="markdown"  # markdown, json, both
QUIET=false

# Parse CLI arguments
while [[ $# -gt 0 ]]; do
  case "$1" in
    --json)
      OUTPUT_FORMAT="json"
      shift
      ;;
    --both)
      OUTPUT_FORMAT="both"
      shift
      ;;
    --quiet)
      QUIET=true
      shift
      ;;
    *)
      echo "Unknown flag: $1" >&2
      exit 1
      ;;
  esac
done

# Placeholder for main logic (tasks below will fill this in)
echo "finops-audit: format=$OUTPUT_FORMAT quiet=$QUIET"
