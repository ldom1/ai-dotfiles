#!/usr/bin/env python3
"""Count distinct session logs per pitfall id from '**Pitfall hit:**' lines.

Usage: count-pitfall-hits.py BRAIN_PATH [--days N]   (default 30)
An id with >= 2 sessions is a candidate, unless it has a sensor draft in
inbox/sensors/ or a '(sensor: ...)' suffix on its rule. Read-only.

--open-drafts: list the drafts in inbox/sensors/ that still need an owner decision
(one '<file>\t<open|accepted|reject-only>' line each, then 'N open drafts'). A draft
is closed by a '**Decision:** installed|rejected' line, a '**Status:** shipped' line,
or a '(sensor: ...)' suffix on the rule of its 'pitfall:' id.
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


def has_sensor(i: str, rules: list) -> bool:
    return any(re.search(rf"\(sensor:[^)]*\)\s*\^{i}\s*$", l) for l in rules)


def load_rules(vault: Path) -> list:
    rule_files = [vault / "resources/operational/ai-agents/pitfalls.md",
                  *(vault / "resources/knowledge/patterns").glob("*-patterns.md")]
    return [l for f in rule_files if f.exists() for l in f.read_text().splitlines()]


def open_drafts(vault: Path) -> int:
    rules = load_rules(vault)
    n = 0
    for f in sorted((vault / "inbox/sensors").glob("*.md")):
        text = f.read_text()
        pid = re.search(r"^pitfall:\s*\^([a-z]\d+)\s*$", text, re.M)
        if (re.search(r"^\*\*Decision:\*\* (installed|rejected)", text, re.M)
                or re.search(r"^\*\*Status:\*\* shipped", text, re.M)
                or (pid and has_sensor(pid.group(1), rules))):
            continue
        if re.search(r"^\*\*Kind:\*\*.*not mechanizable", text, re.M):
            state = "reject-only"
        elif re.search(r"^\*\*Decision:\*\* accepted", text, re.M):
            state = "accepted"
        else:
            state = "open"
        print(f"{f.name}\t{state}")
        n += 1
    print(f"{n} open drafts")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("brain_path", type=Path)
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--open-drafts", action="store_true")
    a = ap.parse_args()
    vault = a.brain_path
    if a.open_drafts:
        return open_drafts(vault)
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

    rules = load_rules(vault)
    drafts = "\n".join(f.read_text() for f in (vault / "inbox/sensors").glob("*.md")) \
        if (vault / "inbox/sensors").is_dir() else ""

    candidates = 0
    for i, logs in sorted(sessions.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        n = len(logs)
        status = ""
        if n >= 2:
            if re.search(rf"\^{i}\b", drafts):
                status = " -- skip: draft exists"
            elif has_sensor(i, rules):
                status = " -- skip: has sensor"
            else:
                status, candidates = " -- candidate", candidates + 1
        print(f"^{i} {n} session{'s' * (n != 1)}: {', '.join(sorted(logs))}{status}")
    print(f"{candidates} candidates")
    return 0


if __name__ == "__main__":
    sys.exit(main())
