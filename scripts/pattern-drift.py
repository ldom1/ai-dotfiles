#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["ruamel.yaml==0.19.1", "loguru==0.7.3", "pydantic-settings==2.7.1"]
# ///
"""pattern-drift.py: keep the rule ids of the vault pattern notes consistent.

  check [--vault V] [--rules R]   print FAIL <file>: <reason> per problem (exit 1), or OK <n> rules (exit 0)

V defaults to $BRAIN_PATH. R defaults to skills/brain-audit/reference/pitfall-rules.md (the declared letters).

A rule is a bullet at column 0, outside a code fence, under `## Rules` and its `###` subsections. It ends with its
id (`^p4`). A link `[[note#^v5]]` is not an id. `→ ^p9` after the id says a rule of a `-superseded` note moved to
the active rule `^p9`.
"""
import re
import sys
from dataclasses import dataclass
from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings

PATTERNS = "resources/knowledge/patterns"
SUPERSEDED = "-superseded"
ID = re.compile(r"(?<![#\w])\^([a-z])(\d+)\b")
TARGET = re.compile(r"→\s*\^([a-z]\d+)\b")
LETTER = re.compile(r"`([a-z])` [\w-]+")
FENCE = re.compile(r"^\s*(```|~~~)")
H2 = re.compile(r"^## (.*?)\s*$")


class Settings(BaseSettings):
    brain_path: Path | None = None
    lab_root: Path = Path.home() / "lab_perso"
    active_days: int = 60
    rules_file: Path = Path.home() / "ai-dotfiles/skills/brain-audit/reference/pitfall-rules.md"


@dataclass
class Rule:
    id: str
    note: Path
    line: int
    text: str
    superseded: bool
    target: str | None = None


def parse_rules(note: Path) -> tuple[list[Rule], list[str]]:
    """The rules of one pattern note, and the FAIL lines for its structure."""
    fails: list[str] = []
    rules: list[Rule] = []
    superseded = note.stem.endswith(SUPERSEDED)
    in_rules = has_rules = False
    fence_line = 0
    for number, line in enumerate(note.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            fence_line = 0 if fence_line else number
            continue
        if fence_line:
            continue
        heading = H2.match(line)
        if heading:
            in_rules = heading.group(1) == "Rules"
            has_rules = has_rules or in_rules
            continue
        if not (in_rules and line.startswith("- ")):
            continue
        target = TARGET.search(line)
        own = list(ID.finditer(TARGET.sub("", line)))
        if not own:
            fails.append(f"FAIL {note.name}: rule without id at line {number}")
            continue
        rules.append(Rule(f"{own[-1].group(1)}{own[-1].group(2)}", note, number, line[2:].strip(), superseded,
                          target.group(1) if target else None))
    if fence_line:
        fails.append(f"FAIL {note.name}: unclosed code fence at line {fence_line}")
    if not has_rules:
        fails.append(f"FAIL {note.name}: no ## Rules")
    return rules, fails


def declared_letters(rules_file: Path) -> dict[str, str]:
    """Letter -> note name, as written in `pitfall-rules.md` (`p` python-patterns)."""
    text = rules_file.read_text(encoding="utf-8")
    return {m.group(1): m.group(0).split("` ", 1)[1] for m in LETTER.finditer(text)}


def check(vault: Path, rules_file: Path) -> list[str]:
    """FAIL lines for the pattern notes of the vault. Empty when all is consistent."""
    letters = declared_letters(rules_file)
    fails: list[str] = []
    rules: list[Rule] = []
    for note in sorted((vault / PATTERNS).glob("*.md")):
        found, problems = parse_rules(note)
        rules += found
        fails += problems
    seen: dict[str, Rule] = {}
    for rule in rules:
        if rule.id[0] not in letters:
            fails.append(f"FAIL {rule.note.name}: letter {rule.id[0]} not in {rules_file.name}")
        if rule.id in seen:
            fails.append(f"FAIL {rule.note.name}: duplicate id {rule.id} at line {rule.line}"
                         f" (also {seen[rule.id].note.name}:{seen[rule.id].line})")
        seen.setdefault(rule.id, rule)
    active = {r.id for r in rules if not r.superseded}
    for rule in rules:
        if rule.target and rule.target not in active:
            fails.append(f"FAIL {rule.note.name}: ^{rule.id} supersede target ^{rule.target} is not an active rule"
                         f" at line {rule.line}")
    return list(dict.fromkeys(fails))


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] != "check":
        print(__doc__, file=sys.stderr)
        return 2
    settings = Settings()
    vault, rules_file = settings.brain_path, settings.rules_file
    rest = args[1:]
    while rest:
        if rest[0] in ("--vault", "--rules") and len(rest) >= 2:
            if rest[0] == "--vault":
                vault = Path(rest[1])
            else:
                rules_file = Path(rest[1])
            rest = rest[2:]
        else:
            print(__doc__, file=sys.stderr)
            return 2
    if vault is None or not (vault / PATTERNS).is_dir():
        logger.error("no vault with {} (give --vault or set BRAIN_PATH)", PATTERNS)
        return 2
    if not rules_file.is_file():
        logger.error("no rules file {}", rules_file)
        return 2
    fails = check(vault, rules_file)
    if fails:
        print("\n".join(fails))
        return 1
    total = sum(len(parse_rules(n)[0]) for n in (vault / PATTERNS).glob("*.md"))
    print(f"OK {total} rules")
    return 0


if __name__ == "__main__":
    sys.exit(main())
