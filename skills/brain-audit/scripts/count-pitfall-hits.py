#!/usr/bin/env python3
"""Count distinct session logs per pitfall id from '**Pitfall hit:**' lines.

Usage: count-pitfall-hits.py BRAIN_PATH [--days N]   (default 30)
An id with >= 2 sessions is a candidate, unless it has a sensor draft in
inbox/sensors/ or a '(sensor: ...)' suffix on its rule. Read-only.
"""
import argparse
import re
import sys
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

ID = r"\^([a-z]\d+)"


def retired_map(pitfalls: Path) -> dict:
    """'^g7→^g2' pairs after '## Retired ids', resolved through chains."""
    m = {}
    if pitfalls.exists():
        tail = re.split(r"^## Retired ids\s*$", pitfalls.read_text(), flags=re.M)[1:]
        m = dict(re.findall(ID + "→" + ID, "".join(tail)))
    def current(i):
        for _ in range(len(m) + 1):
            if i not in m:
                break
            i = m[i]
        return i
    return {old: current(old) for old in m}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("brain_path", type=Path)
    ap.add_argument("--days", type=int, default=30)
    a = ap.parse_args()
    vault = a.brain_path
    cutoff = (date.today() - timedelta(days=a.days)).isoformat()
    retired = retired_map(vault / "resources/operational/ai-agents/pitfalls.md")

    sessions = defaultdict(set)  # id -> {log stem}
    for f in sorted((vault / "inbox/daily/implementation").glob("**/*.md")):
        if f.name[:10] < cutoff:  # logs are named YYYY-MM-DD-<topic>.md
            continue
        for line in f.read_text().splitlines():
            if line.startswith("**Pitfall hit:**"):
                for i in re.findall(ID, line):
                    sessions[retired.get(i, i)].add(f.stem)

    rule_files = [vault / "resources/operational/ai-agents/pitfalls.md",
                  *(vault / "resources/knowledge/patterns").glob("*-patterns.md")]
    rules = [l for f in rule_files if f.exists() for l in f.read_text().splitlines()]
    drafts = "\n".join(f.read_text() for f in (vault / "inbox/sensors").glob("*.md")) \
        if (vault / "inbox/sensors").is_dir() else ""

    candidates = 0
    for i, logs in sorted(sessions.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        n = len(logs)
        status = ""
        if n >= 2:
            if re.search(rf"\^{i}\b", drafts):
                status = " -- skip: draft exists"
            elif any(re.search(rf"\(sensor:[^)]*\)\s*\^{i}\s*$", l) for l in rules):
                status = " -- skip: has sensor"
            else:
                status, candidates = " -- candidate", candidates + 1
        print(f"^{i} {n} session{'s' * (n != 1)}: {', '.join(sorted(logs))}{status}")
    print(f"{candidates} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
