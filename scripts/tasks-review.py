#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["pyyaml==6.0.2"]
# ///
"""tasks-review.py: check the review items of the Local Brain and print a one-line summary.

  check [DIR]                      print FAIL <file>: <reason> per problem (exit 1), or OK <n> items (exit 0)
  summary --project SLUG [DIR]     print one line (<= 300 bytes), or nothing when the project has
                                   no open item and no answer in the last 7 days

DIR defaults to $BRAIN_PATH/inbox/review. The vault is two levels above DIR.
An item is one note with YAML frontmatter. The script reads the frontmatter block only.
It prints names, counts and enum values. It never prints the body of an item.
"""
import argparse
import os
import re
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import yaml

TYPES = ("geste", "arbitrage")
STATUSES = ("ouvert", "répondu", "fait", "écarté")
TOOLS = ("claude", "cursor", "vibe")
REQUIRED = ("type", "project", "tool", "status", "created")
FRONTMATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---[ \t]*(?:\r?\n|\Z)", re.S)
SLUG_LINK = re.compile(r"\A\[\[([^\[\]|#/\\]+)\]\]\Z")
ANSWER_DAYS = 7


def load_items(directory: Path) -> list[dict]:
    """One dict per `*.md` file: the frontmatter keys, plus `_file`, `_mtime` and, on a parse error, `_error`."""
    items = []
    if not directory.is_dir():
        return items
    for path in sorted(directory.glob("*.md")):
        item: dict = {}
        try:
            match = FRONTMATTER.match(path.read_text(encoding="utf-8"))
            if not match:
                item["_error"] = "no frontmatter block"
            else:
                data = yaml.safe_load(match.group(1))
                if isinstance(data, dict):
                    item.update(data)
                else:
                    item["_error"] = "frontmatter is not a mapping"
        except UnicodeDecodeError:
            item["_error"] = "not UTF-8"
        except (yaml.YAMLError, ValueError):  # a bad date like 2026-13-45 raises ValueError
            item["_error"] = "frontmatter is not valid YAML"
        item["_file"] = path.name
        item["_mtime"] = datetime.fromtimestamp(path.stat().st_mtime).date()
        items.append(item)
    return items


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def slug_of(item: dict) -> str | None:
    """The slug of `project: "[[slug]]"`, or None when the value is not that form."""
    match = SLUG_LINK.match(_text(item.get("project")))
    return match.group(1) if match else None


def problems(item: dict, vault: Path) -> list[str]:
    if "_error" in item:
        return [item["_error"]]
    out = [f"missing {key}" for key in REQUIRED if item.get(key) in (None, "")]
    for key, allowed in (("type", TYPES), ("status", STATUSES), ("tool", TOOLS)):
        value = item.get(key)
        if value not in (None, "") and value not in allowed:
            out.append(f"{key} {value!r} not in {', '.join(allowed)}")
    project = item.get("project")
    if project not in (None, ""):
        slug = slug_of(item)
        if isinstance(project, list):
            out.append('project must be a quoted link: "[[slug]]"')
        elif slug is None:
            out.append(f"project {project!r} must be \"[[slug]]\", not a path")
        elif not (vault / "projects" / f"{slug}.md").is_file():
            out.append(f"no projects/{slug}.md")
    created = item.get("created")
    if created not in (None, ""):
        try:
            if not isinstance(created, date):
                date.fromisoformat(str(created))
        except ValueError:
            out.append(f"created {created!r} is not a date (YYYY-MM-DD)")
    if item.get("type") == "geste" and not _text(item.get("why_not_agent")):
        out.append("geste needs why_not_agent")
    if item.get("type") == "arbitrage":
        options = item.get("options")
        if not isinstance(options, list) or len([o for o in options if o not in (None, "")]) < 2:
            out.append("arbitrage needs 2 options")
    if item.get("status") == "répondu" and not _text(item.get("answer")):
        out.append("répondu needs answer")
    return out


def summary_line(items: list[dict], slug: str, today: date) -> str:
    mine = [i for i in items if "_error" not in i and slug_of(i) == slug]
    opened = [i for i in mine if i.get("status") == "ouvert"]
    cutoff = today - timedelta(days=ANSWER_DAYS)
    answered = [i for i in mine if i.get("status") == "répondu" and i["_mtime"] > cutoff]
    parts = []
    if opened:
        gestes = sum(i.get("type") == "geste" for i in opened)
        arbitrages = sum(i.get("type") == "arbitrage" for i in opened)
        kinds = []
        if gestes:
            kinds.append(f"{gestes} geste{'s' if gestes > 1 else ''}")
        if arbitrages:
            kinds.append(f"{arbitrages} arbitrage{'s' if arbitrages > 1 else ''}")
        parts.append(f"{len(opened)} ouvert{'s' if len(opened) > 1 else ''} ({', '.join(kinds)})")
    if answered:
        parts.append(f"{len(answered)} répondu{'s' if len(answered) > 1 else ''} < {ANSWER_DAYS} j")
    if not parts:
        return ""
    return f"[review] {slug}: {', '.join(parts)} → TASKS_REVIEW"


def default_dir() -> Path | None:
    brain = os.environ.get("BRAIN_PATH")
    return Path(brain) / "inbox" / "review" if brain else None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    check = sub.add_parser("check")
    check.add_argument("dir", nargs="?", type=Path)
    summary = sub.add_parser("summary")
    summary.add_argument("--project", required=True)
    summary.add_argument("dir", nargs="?", type=Path)
    args = parser.parse_args(argv)
    directory = args.dir or default_dir()
    if directory is None:
        print("BRAIN_PATH is not set and no DIR given", file=sys.stderr)
        return 2
    items = load_items(directory)
    if args.cmd == "check":
        vault = directory.parent.parent
        found = [(i["_file"], reason) for i in items for reason in problems(i, vault)]
        for name, reason in found:
            print(f"FAIL {name}: {reason}")
        if found:
            return 1
        print(f"OK {len(items)} items")
        return 0
    line = summary_line(items, args.project, date.today())
    if line:
        print(line)
    return 0


if __name__ == "__main__":
    sys.exit(main())
