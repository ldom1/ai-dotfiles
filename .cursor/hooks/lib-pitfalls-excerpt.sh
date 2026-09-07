#!/usr/bin/env bash
# sourced by session-*.sh — do not execute alone
brain_hooks_pitfalls_excerpt() {
  local file="$1"
  local max=12288
  [[ -f "$file" ]] || return 0
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
recent = parts[-3:] if parts else []
index = "\n".join(headings)
chunks = ["--- PITFALLS HEADING INDEX (bounded) ---", index, "--- RECENT ENTRIES (up to 3) ---", "\n\n".join(recent)]
out = "\n".join(chunks)
sys.stdout.buffer.write(out.encode("utf-8", errors="replace")[:max_b])
PY
}
