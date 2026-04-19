#!/usr/bin/env python3
"""Inspect Claude Code JSONL for duplicate assistant message ids (streaming)."""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("jsonl", type=Path, help="Path to a *.jsonl transcript")
    args = p.parse_args()
    path = args.jsonl
    if not path.is_file():
        print(f"not a file: {path}", file=sys.stderr)
        return 1

    by_mid: dict[str, list[tuple[int, tuple]]] = defaultdict(list)
    n_assistant = 0
    for i, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except json.JSONDecodeError:
            continue
        if o.get("type") != "assistant":
            continue
        msg = o.get("message") or {}
        u = msg.get("usage")
        if not u:
            continue
        mid = msg.get("id")
        if not mid:
            continue
        n_assistant += 1
        tup = (
            u.get("input_tokens"),
            u.get("cache_creation_input_tokens"),
            u.get("cache_read_input_tokens"),
            u.get("output_tokens"),
        )
        by_mid[str(mid)].append((i, tup))

    dups = {k: v for k, v in by_mid.items() if len(v) > 1}
    print(f"assistant lines with usage+id: {n_assistant}")
    print(f"unique message ids: {len(by_mid)}")
    print(f"ids with 2+ lines (streaming duplicates): {len(dups)}")
    if dups:
        k, lines = next(iter(dups.items()))
        same = len({t for _, t in lines}) == 1
        print(f"example id {k[:20]}… lines={len(lines)} identical_usage_tuples={same}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
