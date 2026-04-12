#!/usr/bin/env bash
# Push local .wiki/ repository when needed.
set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
wiki_dir="$repo_root/.wiki"

if [[ ! -d "$wiki_dir" || ! -d "$wiki_dir/.git" ]]; then
  echo "[update-wiki] missing .wiki/ git repo at $wiki_dir" >&2
  echo "[update-wiki] clone it once: git clone https://github.com/ldom1/ai-dotfiles.wiki.git .wiki" >&2
  exit 1
fi

if ! git -C "$wiki_dir" remote get-url origin >/dev/null 2>&1; then
  echo "[update-wiki] .wiki has no origin remote configured" >&2
  exit 1
fi

git -C "$wiki_dir" add -A
if git -C "$wiki_dir" diff --staged --quiet; then
  echo "[update-wiki] no wiki changes to publish"
  exit 0
fi

if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
  git -C "$wiki_dir" config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git -C "$wiki_dir" config user.name "github-actions[bot]"
else
  wiki_email="${GIT_AUTHOR_EMAIL:-$(git -C "$repo_root" config user.email 2>/dev/null || true)}"
  wiki_name="${GIT_AUTHOR_NAME:-$(git -C "$repo_root" config user.name 2>/dev/null || true)}"
  if [[ -z "$wiki_email" || -z "$wiki_name" ]]; then
    echo "[update-wiki] set git user.name / user.email or GIT_AUTHOR_*" >&2
    exit 1
  fi
  git -C "$wiki_dir" config user.email "$wiki_email"
  git -C "$wiki_dir" config user.name "$wiki_name"
fi

msg="sync: wiki (${GITHUB_SHA:-$(git -C "$repo_root" rev-parse --short HEAD 2>/dev/null || echo local)})"
git -C "$wiki_dir" commit -m "$msg"
git -C "$wiki_dir" push origin HEAD

echo "[update-wiki] pushed .wiki changes"
