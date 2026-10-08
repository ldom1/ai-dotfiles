#!/usr/bin/env bash
# Install act v0.2.89 into ~/.local/bin after a checksum check.
set -euo pipefail
VERSION=0.2.89
ASSET=act_Linux_x86_64.tar.gz
TMP=$(mktemp -d); trap 'rm -rf "$TMP"' EXIT
BASE="https://github.com/nektos/act/releases/download/v$VERSION"
curl -fsSL -o "$TMP/$ASSET" "$BASE/$ASSET"
curl -fsSL -o "$TMP/checksums.txt" "$BASE/checksums.txt"
(cd "$TMP" && grep " $ASSET\$" checksums.txt | sha256sum -c -)
tar -xzf "$TMP/$ASSET" -C "$TMP" act
mkdir -p "$HOME/.local/bin"
install -m 755 "$TMP/act" "$HOME/.local/bin/act"
"$HOME/.local/bin/act" --version
