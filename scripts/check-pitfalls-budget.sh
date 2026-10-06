#!/usr/bin/env bash
# Write-time budget gate for pitfalls.md: size cap + stable rule ids (^v3).
# Usage: check-pitfalls-budget.sh [FILE] [MAX_BYTES]   defaults: vault pitfalls.md, 6000
# Exit 0 ok · 1 over budget or id problem · 2 file missing. /capture and compile run it.
set -euo pipefail

AI_DOTFILES="${AI_DOTFILES:-$HOME/ai-dotfiles}"
if [[ -z "${BRAIN_PATH:-}" ]]; then
  BRAIN_PATH=$(grep '^BRAIN_PATH=' "$AI_DOTFILES/config/brain.env" 2>/dev/null | head -1 | cut -d= -f2)
fi
FILE="${1:-${BRAIN_PATH:-}/resources/operational/ai-agents/pitfalls.md}"
MAX="${2:-6000}"
[[ -f "$FILE" ]] || { echo "no such file: $FILE" >&2; exit 2; }

exec python3 - "$FILE" "$MAX" <<'PY'
import re, sys
path, cap = sys.argv[1], int(sys.argv[2])
size = len(open(path, "rb").read())
lines = open(path, encoding="utf-8").read().replace("\r\n", "\n").split("\n")

sections, title, used = [], "(preamble)", 0
for line in lines:
    if line.startswith("## "):
        sections.append((title, used))
        title, used = line[3:].strip(), 0
    used += len(line.encode()) + 1
sections.append((title, used))

ID = re.compile(r"\s\^([a-z]\d+)\s*$")
problems, seen, retired = [], {}, set()
in_front, in_retired = lines[:1] == ["---"], False
for n, line in enumerate(lines[1:] if in_front else lines, 2 if in_front else 1):
    if in_front:
        in_front = line != "---"
        continue
    if line.startswith("## "):
        in_retired = line[3:].strip() == "Retired ids"
    elif in_retired:
        retired.update(re.findall(r"\^([a-z]\d+)→", line))
    elif line.startswith("- "):
        m = ID.search(line)
        if m:
            seen.setdefault(m.group(1), []).append(n)
        else:
            problems.append(f"rule without id (line {n}): {line[:80]}")
for rid, at in seen.items():
    if len(at) > 1:
        problems.append(f"duplicate id ^{rid} (lines {', '.join(map(str, at))})")
    if rid in retired:
        problems.append(f"retired id reused ^{rid} (line {at[0]})")

name = path.rsplit("/", 1)[-1]
if size > cap:
    rows = [f"  {b:>6,}  {t}" for t, b in sorted(sections, key=lambda s: -s[1])]
    problems[:0] = [f"{name}: {size:,} / {cap:,} B — OVER by {size - cap:,} B. "
                    "Merge rules, or move a stack section to resources/knowledge/patterns/. "
                    "Sections, largest first:"] + rows
if problems:
    print("\n".join(problems))
    sys.exit(1)
print(f"{name}: {size:,} / {cap:,} B — ok ({len(seen)} rules)")
PY
