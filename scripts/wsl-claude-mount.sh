#!/usr/bin/env bash
# wsl-claude-mount.sh — WSL only: replace the ~/.claude symlink with a bind mount of ai-dotfiles/.claude.
# Windows apps (Orca's agent session history) read ~/.claude/projects over \\wsl.localhost,
# and Windows cannot follow a WSL symlink there; it can cross a mount point.
# Usage: bash ~/ai-dotfiles/scripts/wsl-claude-mount.sh   (main checkout; asks for sudo)
# Close Claude sessions first: ~/.claude is missing for a moment during the switch.
# AIF_FSTAB overrides /etc/fstab (tests).
set -euo pipefail

DOTFILES="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$DOTFILES/.claude"
DST="$HOME/.claude"
FSTAB="${AIF_FSTAB:-/etc/fstab}"
LINE="$SRC $DST none bind 0 0"

as_root() { if (( EUID == 0 )); then "$@"; else sudo "$@"; fi; }

[[ $("$DOTFILES/bin/aif-platform" name) == wsl ]] || { echo "Not WSL: ~/.claude stays a symlink."; exit 0; }
if [[ $(git -C "$DOTFILES" rev-parse --absolute-git-dir) != "$(cd "$DOTFILES" && cd "$(git rev-parse --git-common-dir)" && pwd)" ]]; then
  echo "wsl-claude-mount.sh: $DOTFILES is a linked git worktree. Run it from the main checkout." >&2
  exit 2
fi

# The skill links in .claude/skills are relative (../../skills/<name>, tracked in git). Through the
# bind mount they resolve from ~/.claude/skills, so ../../ is $HOME: link $HOME/skills and
# $HOME/private to the repo, or every skill link is broken.
for name in skills private; do
  [[ -d "$DOTFILES/$name" ]] || continue
  if [[ -L "$HOME/$name" || ! -e "$HOME/$name" ]]; then
    ln -sfn "$DOTFILES/$name" "$HOME/$name"
  elif ! [[ "$HOME/$name" -ef "$DOTFILES/$name" ]]; then
    echo "wsl-claude-mount.sh: $HOME/$name exists and is not a link: skill links under ~/.claude stay broken." >&2
  fi
done

if mountpoint -q "$DST" && [[ "$DST" -ef "$SRC" ]]; then
  echo "✓ $DST is already a bind mount of $SRC"
  exit 0
fi
if grep -qE "^[^#]*[[:space:]]${DST}[[:space:]]" "$FSTAB" && ! grep -qxF "$LINE" "$FSTAB"; then
  echo "wsl-claude-mount.sh: $FSTAB already mounts something else on $DST. Fix it by hand." >&2
  exit 1
fi
if [[ -L "$DST" ]]; then
  rm "$DST"
elif [[ -e "$DST" && -n $(ls -A "$DST") ]]; then
  echo "wsl-claude-mount.sh: $DST is a non-empty directory. Move it away first." >&2
  exit 1
fi

grep -qxF "$LINE" "$FSTAB" || echo "$LINE" | as_root tee -a "$FSTAB" >/dev/null
mkdir -p "$DST"
as_root mount --bind "$SRC" "$DST"
echo "✓ $DST is a bind mount of $SRC (line in $FSTAB: mounted again at boot)"
