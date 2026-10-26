#!/usr/bin/env python3
"""Check a /capture session log against the capture skill format.

Usage: check_log.py <log.md> [--vault <BRAIN_PATH>]
Prints one `FAIL <check>: <detail>` line per problem, or `OK`.
Exit 0 = OK, 1 = at least one FAIL, 2 = usage error.
"""
from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

LOOKUP_ONLY = "Lookup/Q&A only. No files modified."
ORDER = ["Goal", "Changes", "Commands/tests", "Follow-ups", "Harness changes", "Metrics"]
REQUIRED = {"Changes", "Follow-ups"}
REPEATABLE = {"Pitfall hit"}
NAME_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-[a-z0-9.]+(?:-[a-z0-9.]+)*\.md$")
LABEL_RE = re.compile(r"^\*\*([^*]+?):\*\*")
QUALIFIER_RE = re.compile(r"\s*\(.*\)$")
LINK_RE = re.compile(r"\[\[([^\]|#]+)(?:#[^\]|]*)?(?:\|[^\]]*)?\]\]")
FENCE_RE = re.compile(r"^```.*?^```", re.M | re.S)
CODE_RE = re.compile(r"`[^`\n]*`")
# Same row regex as scripts/harness-metrics.py (separate plugins, no shared import): keep both in sync.
ROW_RE = re.compile(r"^- (.+?) · (.+?) · expected: (.+?) · check: (.+?)(?: · (verdict: .+))?$")


def vault_stems(vault: Path) -> set[str]:
    stems: set[str] = set()
    for _root, dirs, files in os.walk(vault):
        dirs[:] = [d for d in dirs if not d.startswith(".")]
        stems.update(f[:-3] for f in files if f.endswith(".md"))
    return stems


def bad_harness_rows(text: str) -> list[str]:
    """FAIL lines for `- ` rows under `**Harness changes:**` that `harness-metrics.py changes` cannot parse."""
    fails, topic, in_rows, fenced = [], "", False, False
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("```"):
            fenced = not fenced
        elif fenced:
            continue
        elif line.startswith("## "):
            topic, in_rows = line[3:].strip(), False
        elif line.startswith("**Harness changes:**"):
            in_rows = True
        elif LABEL_RE.match(line):
            in_rows = False
        elif in_rows and line.startswith("- ") and not ROW_RE.match(line):
            fails.append(f"harness row: {topic}: line {n}")
    return fails


def check(path: Path, vault: Path | None = None) -> list[str]:
    fails: list[str] = []
    if not NAME_RE.match(path.name):
        fails.append(f"filename: {path.name} is not YYYY-MM-DD-<topic>.md")
    text = path.read_text(encoding="utf-8")
    if text.strip() == LOOKUP_ONLY:
        return fails
    prose = CODE_RE.sub("", FENCE_RE.sub("", text))
    blocks = re.split(r"^## ", prose, flags=re.M)[1:]
    if not blocks:
        fails.append("structure: no '## <topic>' block")
    for block in blocks:
        topic = block.splitlines()[0].strip()
        labels = [
            QUALIFIER_RE.sub("", m.group(1).strip()) for line in block.splitlines() if (m := LABEL_RE.match(line))
        ]
        for label in labels:
            if label not in ORDER and label not in REPEATABLE:
                fails.append(f"extra section: '{label}' in '{topic}'")
        found = [label for label in labels if label in ORDER]
        for label in ORDER:
            count = found.count(label)
            if count > 1 or (count == 0 and label in REQUIRED):
                fails.append(f"section: '{label}' appears {count} times in '{topic}'")
        if found != sorted(found, key=ORDER.index):
            fails.append(f"order: '{topic}' has {', '.join(found)}; expected order {', '.join(ORDER)}")
    fails.extend(bad_harness_rows(text))
    stems = vault_stems(vault) if vault else None
    for target in (t.strip() for t in LINK_RE.findall(prose)):
        if "/" in target or target.endswith(".md"):
            fails.append(f"folder link: [[{target}]]; use [[<filename>]]")
        elif stems is not None and target not in stems:
            fails.append(f"broken link: [[{target}]] matches no vault note")
    return list(dict.fromkeys(fails))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check a capture session log.")
    parser.add_argument("log", type=Path)
    parser.add_argument("--vault", type=Path, help="vault root: also check that wikilinks resolve")
    args = parser.parse_args(argv)
    if not args.log.is_file():
        print(f"error: {args.log} is not a file", file=sys.stderr)
        return 2
    if args.vault and not args.vault.is_dir():
        print(f"error: {args.vault} is not a directory", file=sys.stderr)
        return 2
    fails = check(args.log, args.vault)
    for fail in fails:
        print(f"FAIL {fail}")
    if not fails:
        print("OK")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
