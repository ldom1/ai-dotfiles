#!/usr/bin/env bash
# Point this repo at versioned hooks (pre-commit: secrets + Cursor runtime dirs).
# Usage: bash scripts/install-git-hooks.sh   (from repo root or any cwd)
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
git -C "$ROOT" config core.hooksPath "$ROOT/git-hooks"
echo "Set core.hooksPath=$ROOT/git-hooks"
