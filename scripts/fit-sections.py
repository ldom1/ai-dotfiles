#!/usr/bin/env python3
"""Print a Markdown file within MAX_BYTES: preamble + leading '## ' sections, whole, in file order.

Last-resort read-time cut for SessionStart. The write-time gate is scripts/check-pitfalls-budget.sh.
Usage: fit-sections.py FILE MAX_BYTES
"""
import re
import sys

NOTE_RESERVE = 400


def main(path: str, cap: int) -> None:
    text = open(path, encoding="utf-8").read().replace("\r\n", "\n")
    if len(text.encode()) <= cap:
        sys.stdout.write(text)
        return
    room, used, kept, dropped = cap - NOTE_RESERVE, 0, [], []
    for block in re.split(r"(?m)^(?=## )", text):
        size = len(block.encode())
        if not dropped and used + size <= room:
            kept.append(block)
            used += size
        else:
            dropped.append(block)
    names = [b.split("\n", 1)[0][3:].strip() if b.startswith("## ") else "(preamble)" for b in dropped]
    omitted = sum(len(b.encode()) for b in dropped)
    sys.stdout.write("".join(kept))
    print(f"[truncated: {omitted:,} B omitted, sections dropped: {', '.join(names)}"
          f" — run scripts/check-pitfalls-budget.sh; full file: {path}]")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
