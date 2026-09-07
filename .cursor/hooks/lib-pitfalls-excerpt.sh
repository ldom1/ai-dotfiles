#!/usr/bin/env bash
# sourced by session-*.sh — do not execute alone
brain_hooks_pitfalls_excerpt() {
  local file="$1"
  local max=12288
  [[ -f "$file" ]] || return 0
  # Newest-first registry: pack up to 3 newest full entries first, then fill
  # remaining budget with a truncated ## heading index (never full 279KB file).
  python3 - "$file" "$max" <<'PY'
import sys
path, max_b = sys.argv[1], int(sys.argv[2])
text = open(path, encoding="utf-8", errors="replace").read()
lines = text.splitlines()
headings = [ln for ln in lines if ln.startswith("## ")]
parts = []
cur = []
for ln in lines:
    if ln.startswith("## ") and cur:
        parts.append("\n".join(cur))
        cur = [ln]
    else:
        cur.append(ln)
if cur:
    parts.append("\n".join(cur))
# File is newest-first → first parts are newest
recent = parts[:3] if parts else []
recent_block = "\n\n".join(recent)
header_recent = "--- RECENT ENTRIES (up to 3, newest) ---\n"
header_index = "--- PITFALLS HEADING INDEX (bounded) ---\n"
# Reserve space for recent entries first
prefix = header_recent + recent_block
prefix_b = prefix.encode("utf-8", errors="replace")
if len(prefix_b) >= max_b:
    sys.stdout.buffer.write(prefix_b[:max_b])
    raise SystemExit(0)
remain = max_b - len(prefix_b) - 2  # newlines between sections
index = "\n".join(headings)
index_b = index.encode("utf-8", errors="replace")
index_hdr = header_index.encode("utf-8")
budget = max(0, remain - len(index_hdr) - 1)
index_trunc = index_b[:budget]
out = prefix_b + b"\n\n" + index_hdr + index_trunc
sys.stdout.buffer.write(out[:max_b])
PY
}
