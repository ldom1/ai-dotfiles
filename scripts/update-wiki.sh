#!/usr/bin/env bash
# Sync docs/wiki/ into the GitHub wiki repo (separate .wiki.git).
# Tokens: prefer WIKI_PUSH_TOKEN (PAT with repo scope); else GITHUB_TOKEN in Actions.
set -euo pipefail

_script_dir=""
_script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT=""
REPO_ROOT="$(cd "$_script_dir/.." && pwd)"
DOCS="$REPO_ROOT/docs/wiki"
WIKI_TMP="${WIKI_TMPDIR:-$(mktemp -d)}"
CLONE_DIR="$WIKI_TMP/wiki-checkout"

cleanup() {
  rm -rf "$WIKI_TMP"
}
trap cleanup EXIT

if [[ -n "${GITHUB_ACTIONS:-}" && "${GITHUB_REPOSITORY:-ldom1/ai-dotfiles}" != "ldom1/ai-dotfiles" ]]; then
  echo "[update-wiki] skip: wiki sync only runs on upstream ldom1/ai-dotfiles"
  exit 0
fi

if [[ ! -d "$DOCS/Skills" || ! -f "$DOCS/Skills.md" ]]; then
  echo "[update-wiki] missing $DOCS/Skills or Skills.md" >&2
  exit 1
fi

TOKEN="${WIKI_PUSH_TOKEN:-${GITHUB_TOKEN:-}}"
if [[ -z "$TOKEN" ]]; then
  echo "[update-wiki] set WIKI_PUSH_TOKEN (PAT) or run in GitHub Actions with GITHUB_TOKEN" >&2
  exit 1
fi

REPO_FULL="${GITHUB_REPOSITORY:-ldom1/ai-dotfiles}"
CLONE_URL="https://x-access-token:${TOKEN}@github.com/${REPO_FULL}.wiki.git"

git clone --depth 1 "$CLONE_URL" "$CLONE_DIR"
cp "$DOCS/Skills.md" "$CLONE_DIR/Skills.md"
mkdir -p "$CLONE_DIR/Skills"
cp "$DOCS/Skills/"*.md "$CLONE_DIR/Skills/"

cd "$CLONE_DIR"
git add -A
if git diff --staged --quiet; then
  echo "[update-wiki] no changes to publish"
  exit 0
fi

if [[ -n "${GITHUB_ACTIONS:-}" ]]; then
  git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
  git config user.name "github-actions[bot]"
else
  git config user.email "${GIT_AUTHOR_EMAIL:-$(git -C "$REPO_ROOT" config user.email 2>/dev/null || true)}"
  git config user.name "${GIT_AUTHOR_NAME:-$(git -C "$REPO_ROOT" config user.name 2>/dev/null || true)}"
  if [[ -z "$(git config user.email)" || -z "$(git config user.name)" ]]; then
    echo "[update-wiki] set git user.name / user.email or GIT_AUTHOR_*" >&2
    exit 1
  fi
fi

MSG="sync: docs/wiki (${GITHUB_SHA:-$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo local)})"
git commit -m "$MSG"
if ! git push origin HEAD; then
  echo "[update-wiki] git push failed — GitHub Actions often cannot push the wiki with GITHUB_TOKEN alone." >&2
  echo "[update-wiki] Add repo secret WIKI_PUSH_TOKEN (PAT with repo scope) or push from your machine: bash scripts/update-wiki.sh" >&2
  exit 1
fi

echo "[update-wiki] pushed to wiki"
