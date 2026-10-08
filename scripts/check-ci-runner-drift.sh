#!/usr/bin/env bash
# Report (never fix) drift between docker/ci-runner.manifest and the latest ubuntu24 runner image release.
# Cached 7 days. Fail-open: any error, or gh taking over 5 s, prints nothing.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GH="${LOCAL_CI_GH:-gh}"
CACHE="${LOCAL_CI_HOME:-$HOME/.cache/local-ci}/drift-check"
if [[ -f "$CACHE" && -n "$(find "$CACHE" -mtime -7 2>/dev/null)" ]]; then cat "$CACHE"; exit 0; fi
pinned=$(grep '^RUNNER_IMAGE_TAG=' "$ROOT/docker/ci-runner.manifest" | head -1 | cut -d= -f2)
latest=$(timeout 5 "$GH" api 'repos/actions/runner-images/releases?per_page=30' \
  -q '[.[]|select(.tag_name|startswith("ubuntu24/"))][0].tag_name' 2>/dev/null) || exit 0
mkdir -p "$(dirname "$CACHE")"
if [[ -n "$latest" && "$latest" != "$pinned" ]]; then
  echo "WARNING: local-ci runner manifest copies $pinned; latest ubuntu24 release is $latest (update the manifest in a commit, rebuild, re-run parity)" | tee "$CACHE"
else
  : > "$CACHE"
fi
