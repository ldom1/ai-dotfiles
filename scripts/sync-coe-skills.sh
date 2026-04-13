#!/bin/bash
set -e

REMOTE_URL="git@gitlab.artelys.lan:crystaloptimizationengine/coe-skills.git"
CACHE_DIR="${HOME}/ai-dotfiles/tmp/coe-skills"
SKILLS_DIR="${HOME}/ai-dotfiles/skills"

mkdir -p "$CACHE_DIR"

if [ -d "$CACHE_DIR/.git" ]; then
  cd "$CACHE_DIR"
  git pull origin main
else
  git clone "$REMOTE_URL" "$CACHE_DIR"
fi

# Copy skills to ai-dotfiles
cp -r "$CACHE_DIR"/skills/* "$SKILLS_DIR/"
echo "✓ Synced coe-skills to skills/"
