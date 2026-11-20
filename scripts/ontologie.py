#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["ruamel.yaml==0.19.1"]
# ///
"""ontologie.py: keep the `ontologie/` folder of the Local Brain consistent.

  activity [VAULT]   write `project_activity: YYYY-MM` on each technologie and sujet
  check [VAULT]      print FAIL <file>: <reason> per problem (exit 1), WARN lines, or OK <n> elements (exit 0)

VAULT defaults to $BRAIN_PATH.

A project uses an element when the last section `## Ontologie` of its note in `projects/` links it.
`project_activity` is the month of the latest session log (`inbox/daily/implementation/<project>/YYYY-MM-DD-*.md`)
among those projects. It is a proxy: the log can be about another element. A project with no log gives no date.
The script never writes `level`: only the owner states a level of mastery.
"""
import io
import os
import re
import sys
from pathlib import Path

from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

LEVELS = ("concepts", "sujets", "technologies")
ASKED_BY = ("moi", "clients", "prospects")
MASTERY = ("maîtrise", "pratique", "notion")
FRONTMATTER = re.compile(r"\A---\n(.*?\n)---\n", re.S)
WIKILINK = re.compile(r"\[\[([^\]|#]+)")
SECTION = re.compile(r"^## Ontologie[ \t]*\n(.*?)(?=^## |\Z)", re.S | re.M)
LOG_MONTH = re.compile(r"(\d{4}-\d{2})-\d{2}")
SKIPPED_DIRS = {".git", ".obsidian", ".trash", "archive"}


def _yaml() -> YAML:
    """Round-trip YAML that writes a note header back as Obsidian and the generator wrote it."""
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.width = 4096
    yaml.indent(mapping=2, sequence=4, offset=2)
    return yaml


def frontmatter(text: str):
    """The header of a note as a mapping, or None when the note has no valid header."""
    match = FRONTMATTER.match(text)
    if not match:
        return None
    try:
        data = _yaml().load(match.group(1))
    except YAMLError:
        return None
    return data if isinstance(data, dict) else None


def links(value) -> list[str]:
    """Wikilink targets in a property value (a string, a list of strings, or nothing)."""
    items = value if isinstance(value, list) else [value]
    return [target.strip() for item in items if isinstance(item, str) for target in WIKILINK.findall(item)]


def elements(vault: Path) -> dict[str, dict[str, Path]]:
    """For each level, the note of each element by file name."""
    return {level: {p.stem: p for p in sorted((vault / "ontologie" / level).glob("*.md"))} for level in LEVELS}


def project_links(vault: Path) -> dict[str, list[str]]:
    """For each project note, the links of its `## Ontologie` section."""
    found = {}
    for path in sorted((vault / "projects").glob("*.md")):
        section = SECTION.search(path.read_text(encoding="utf-8"))
        if section:
            found[path.stem] = list(dict.fromkeys(target.strip() for target in WIKILINK.findall(section.group(1))))
    return found


def latest_month(vault: Path, project: str) -> str | None:
    """The month of the latest dated session log of a project."""
    months = [m.group(1) for p in (vault / "inbox/daily/implementation" / project).glob("*.md")
              if (m := LOG_MONTH.match(p.name))]
    return max(months, default=None)


def activity(vault: Path) -> int:
    users: dict[str, list[str]] = {}
    for project, targets in project_links(vault).items():
        for target in targets:
            users.setdefault(target, []).append(project)
    months = {project: latest_month(vault, project) for projects in users.values() for project in projects}
    notes = [p for level in ("technologies", "sujets") for p in elements(vault)[level].values()]
    changed = 0
    for path in notes:
        text = path.read_text(encoding="utf-8")
        data = frontmatter(text)
        if data is None:
            continue
        month = max((months[p] for p in users.get(path.stem, []) if months[p]), default=None)
        if data.get("project_activity") == month:
            continue
        if month is None:
            del data["project_activity"]
        else:
            data["project_activity"] = month
        header = io.StringIO()
        _yaml().dump(data, header)
        path.write_text("---\n" + header.getvalue() + "---\n" + FRONTMATTER.sub("", text, count=1), encoding="utf-8")
        changed += 1
    print(f"OK {len(notes)} notes, {changed} changed")
    return 0


def check(vault: Path) -> int:
    by_level = elements(vault)
    names: dict[str, list[Path]] = {}
    for path in vault.rglob("*.md"):
        if not SKIPPED_DIRS & set(path.relative_to(vault).parts):
            names.setdefault(path.stem, []).append(path)
    known = {stem for level in LEVELS for stem in by_level[level]}
    linked: set[str] = set()
    fails, warns = [], []

    def fail(path: Path, reason: str) -> None:
        fails.append(f"FAIL {path.relative_to(vault).as_posix()}: {reason}")

    for project, targets in project_links(vault).items():
        linked.update(targets)
        for target in targets:
            if target not in known:
                fail(vault / "projects" / f"{project}.md", f"link [[{target}]] in ## Ontologie has no note in ontologie/")
    for level in LEVELS:
        for stem, path in by_level[level].items():
            for other in names.get(stem, []):
                if other != path:
                    fail(path, f"file name also exists at {other.relative_to(vault).as_posix()}")
            data = frontmatter(path.read_text(encoding="utf-8"))
            if data is None:
                fail(path, "no frontmatter block")
                continue
            for key, target_level in (("concepts", "concepts"), ("sujets", "sujets"), ("broader", "concepts")):
                for target in links(data.get(key)):
                    linked.add(target)
                    if target not in by_level[target_level]:
                        fail(path, f"{key} link [[{target}]] is not a note in ontologie/{target_level}/")
            for key in ("project", "rules"):
                for target in links(data.get(key)):
                    if target not in names:
                        fail(path, f"{key} link [[{target}]] has no note in the vault")
            if level == "sujets":
                if not links(data.get("concepts")):
                    fail(path, "a sujet needs at least one concept")
                asked = data.get("asked_by") or []
                if not asked:
                    fail(path, "asked_by is empty")
                for value in asked if isinstance(asked, list) else [asked]:
                    if value not in ASKED_BY:
                        fail(path, f"asked_by value {str(value)!r} is not one of {', '.join(ASKED_BY)}")
            if data.get("level") is not None and data["level"] not in MASTERY:
                fail(path, f"level value {str(data['level'])!r} is not one of {', '.join(MASTERY)}")
    for level in LEVELS:
        for stem, path in by_level[level].items():
            if stem not in linked:
                warns.append(f"WARN {path.relative_to(vault).as_posix()}: no project and no ontologie note links it")
    print("\n".join(sorted(fails) + warns + ([] if fails else [f"OK {len(known)} elements"])))
    return 1 if fails else 0


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in ("activity", "check") or len(args) > 2:
        print(__doc__, file=sys.stderr)
        return 2
    root = args[1] if len(args) == 2 else os.environ.get("BRAIN_PATH")
    if not root or not Path(root).is_dir():
        print("ontologie.py: no vault (give VAULT or set BRAIN_PATH)", file=sys.stderr)
        return 2
    if not (Path(root) / "ontologie").is_dir():
        print(f"ontologie.py: no ontologie/ folder in {root}", file=sys.stderr)
        return 2
    return activity(Path(root)) if args[0] == "activity" else check(Path(root))


if __name__ == "__main__":
    sys.exit(main())
