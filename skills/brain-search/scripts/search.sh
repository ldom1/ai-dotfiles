#!/usr/bin/env bash
# brain-search/search.sh — semantic and keyword search over the Local Brain vault
# Usage: search.sh [--mode search|vsearch|query] [--limit N] "<query>"
#
# Modes:
#   search   BM25 keyword search  — instant, no models (default)
#   vsearch  Vector similarity    — semantic, downloads reranker on first use (~600MB)
#   query    Hybrid + LLM expand  — best quality, downloads expansion model on first use (~1.3GB)
#
# Environment (auto-loaded from brain.env if not set):
#   QMD_INDEX_PATH   path to vault SQLite index
#   BRAIN_PATH       path to vault root
set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
_CYN='\033[0;36m'; _YLW='\033[0;33m'; _RED='\033[0;31m'
_DIM='\033[2m'; _BLD='\033[1m'; _RST='\033[0m'
_info() { printf "${_CYN}▸${_RST} %s\n" "$*" >&2; }
_warn() { printf "${_YLW}⚠${_RST}  %s\n" "$*" >&2; }
_err()  { printf "${_RED}✗${_RST}  %s\n" "$*" >&2; exit 1; }

# ── Load brain.env if vars not already exported ───────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../../../config/brain.env"
if [[ -z "${QMD_INDEX_PATH:-}" && -f "$ENV_FILE" ]]; then
  # shellcheck source=/dev/null
  source "$ENV_FILE"
fi

# ── Validate ──────────────────────────────────────────────────────────────────
if ! command -v qmd &>/dev/null; then
  _err "qmd not found — install with: npm install -g @tobilu/qmd"
fi
if [[ -z "${QMD_INDEX_PATH:-}" ]]; then
  _err "QMD_INDEX_PATH is not set. Add it to ~/ai-dotfiles/config/brain.env"
fi
if [[ ! -f "$QMD_INDEX_PATH" ]]; then
  _err "Index not found at $QMD_INDEX_PATH. Run: qmd collection add \"\$BRAIN_PATH\" --name brain"
fi

# ── Parse args ────────────────────────────────────────────────────────────────
MODE="search"
LIMIT=""
QUERY=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --mode)   MODE="$2";  shift 2 ;;
    --limit)  LIMIT="$2"; shift 2 ;;
    --search|--vsearch|--query)
              MODE="${1#--}"; shift ;;
    -*)       _err "Unknown flag: $1" ;;
    *)        QUERY="$*"; break ;;
  esac
done

if [[ -z "$QUERY" ]]; then
  printf "Usage: %s [--mode search|vsearch|query] [--limit N] \"<query>\"\n" "$(basename "$0")" >&2
  exit 1
fi

# ── Build command ─────────────────────────────────────────────────────────────
QMD_ARGS=("$MODE" "$QUERY" "-c" "brain")
if [[ -n "$LIMIT" ]]; then
  QMD_ARGS+=("--limit" "$LIMIT")
fi

_info "brain-search · mode=${MODE} · index=$(basename "$QMD_INDEX_PATH")"
if [[ "$MODE" != "search" ]]; then
  _warn "First run downloads ML models locally (~600MB for vsearch, ~1.3GB for query). Subsequent runs are fast."
fi

export INDEX_PATH="$QMD_INDEX_PATH"
exec qmd "${QMD_ARGS[@]}"
