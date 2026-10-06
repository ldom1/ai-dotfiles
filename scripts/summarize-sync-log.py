#!/usr/bin/env python3
"""Summarize brain-sync-end.log for SessionStart: one [last exit] line, then at most 5 notable lines.

The full log is kept as brain-sync-end.log.prev by the hook. Usage: summarize-sync-log.py LOG
"""
import re
import sys

ANSI = re.compile(r"\x1b\[[0-9;]*m")
VAULT = re.compile(r"^\s*[✓✗⚠▸]?\s*brain\s+(.+)$")
SUMMARIZED = re.compile(r"\[sync-project\]|^\s*[✓✗⚠▸]?\s*brain\s")
NOTABLE = re.compile(r"[✗⚠]|ERROR|failed|rejected")
MAX_NOTABLE, MAX_LEN = 5, 160


def main(path: str) -> None:
    try:
        lines = [ANSI.sub("", line).rstrip() for line in open(path, encoding="utf-8", errors="replace")]
    except FileNotFoundError:
        return
    text = "\n".join(lines)
    vault = [m.group(1) for line in lines if (m := VAULT.match(line))]
    synced = re.findall(r"\[sync-project\] (\S+): done\.", text)
    missing = [p.rstrip("/").rsplit("/", 1)[-1] for p in re.findall(r"WARNING: (\S+) does not exist, skipping\.", text)]

    status = " · ".join(vault) if vault else "no status line (sync did not finish?)"
    head = f"[last exit] brain: {status} | projects: {len(synced)} synced"
    if missing:
        head += f", {len(missing)} missing ({', '.join(missing)})"
    print(head)

    notable = [line.strip() for line in lines if NOTABLE.search(line) and not SUMMARIZED.search(line)]
    for line in notable[:MAX_NOTABLE]:
        print(line[:MAX_LEN])
    if len(notable) > MAX_NOTABLE:
        print(f"(+{len(notable) - MAX_NOTABLE} more: ~/.claude/logs/brain-sync-end.log.prev)")


if __name__ == "__main__":
    main(sys.argv[1])
