#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["ruamel.yaml==0.19.1", "loguru==0.7.3", "pydantic-settings==2.7.1"]
# ///
"""ontologie.py: keep the `ontologie/` folder of the Local Brain consistent.

  activity [VAULT]   write `project_activity: YYYY-MM` on each technologie and sujet
  check [VAULT]      print FAIL <file>: <reason> per problem (exit 1), WARN lines, or OK <n> elements (exit 0)
  mentions [VAULT]   write the last section `## Dans le vault` of each element

VAULT defaults to $BRAIN_PATH. $ONTOLOGIE_SHOWN sets how many notes a group of `## Dans le vault` shows (10).

A project uses an element when the last section `## Ontologie` of its note in `projects/` links it.
`project_activity` is the month of the latest session log (`inbox/daily/implementation/<project>/YYYY-MM-DD-*.md`)
among those projects. It is a proxy: the log can be about another element. A project with no log gives no date.
The script never writes `level`: only the owner states a level of mastery.

`## Dans le vault` lists the projects that use the element, then the notes that name it, by group. A concept takes
the projects of its technologies and sujets. A note names an element when its text holds the title or an alias as
a whole word (case ignored), or a link to the element. The property `match` (a list of regular expressions, case
kept) replaces the title and the aliases. A link to another note is not a mention. Each group shows the ten notes
with the most matches. The section is derived: the command writes it again on each run; write your own text above it.
"""
import io
import re
import sys
from collections import Counter
from pathlib import Path

from loguru import logger
from pydantic_settings import BaseSettings
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
ANY_LINK = re.compile(r"\[\[[^\]]*\]\]")
VAULT_SECTION = re.compile(r"\n*^## Dans le vault[ \t]*\n.*\Z", re.S | re.M)
GROUPS = (("Notes d'implémentation", ("inbox/daily/implementation",)),
          ("Specs et plans", ("inbox/daily/specs", "inbox/daily/plans")),
          ("Ressources", ("resources",)))


class Settings(BaseSettings):
    brain_path: Path | None = None
    ontologie_shown: int = 10


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


def unique_names(vault: Path) -> dict[str, list[Path]]:
    """Every note of the vault by file name, outside the skipped folders."""
    names: dict[str, list[Path]] = {}
    for path in vault.rglob("*.md"):
        if not SKIPPED_DIRS & set(path.relative_to(vault).parts):
            names.setdefault(path.stem, []).append(path)
    return names


def as_list(value) -> list[str]:
    return [item for item in (value if isinstance(value, list) else [value]) if isinstance(item, str) and item]


def matchers(stem: str, data: dict) -> list[re.Pattern]:
    """The expressions that find an element in a text. Raises re.error on a bad `match` value."""
    custom = as_list(data.get("match"))
    if custom:
        return [re.compile(term) for term in custom]
    terms = as_list(data.get("title")) + as_list(data.get("aliases")) or [stem]
    return [re.compile(r"(?<!\w)(?:" + "|".join(re.escape(term) for term in terms) + r")(?!\w)", re.I)]


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


def mentions(vault: Path, shown: int = 10) -> int:
    by_level = elements(vault)
    notes = {stem: path for level in LEVELS for stem, path in by_level[level].items()}
    texts = {stem: path.read_text(encoding="utf-8") for stem, path in notes.items()}
    data = {stem: frontmatter(text) or {} for stem, text in texts.items()}
    find = {stem: matchers(stem, data[stem]) for stem in notes}

    users: dict[str, set[str]] = {}
    for project, targets in project_links(vault).items():
        for target in targets:
            users.setdefault(target, set()).add(project)
    for level in ("technologies", "sujets"):  # a concept takes the projects of what is attached to it
        for stem in by_level[level]:
            for concept in links(data[stem].get("concepts")):
                if concept in by_level["concepts"]:
                    users.setdefault(concept, set()).update(users.get(stem, set()))

    names = unique_names(vault)
    found: dict[str, dict[str, Counter]] = {stem: {} for stem in notes}
    for label, folders in GROUPS:
        for folder in folders:
            for path in sorted((vault / folder).rglob("*.md")):
                if SKIPPED_DIRS & set(path.relative_to(vault).parts) or len(names.get(path.stem, [])) != 1:
                    continue
                raw = path.read_text(encoding="utf-8", errors="replace")
                linked = Counter(target.strip() for target in WIKILINK.findall(raw))
                text = ANY_LINK.sub(" ", raw)
                for stem in notes:
                    count = linked[stem] + sum(len(rx.findall(text)) for rx in find[stem])
                    if count:
                        found[stem].setdefault(label, Counter())[path.stem] = count

    changed = 0
    for stem, path in notes.items():
        lines = []
        if users.get(stem):
            projects = sorted(users[stem])
            lines.append(f"- Projets ({len(projects)}) : " + " · ".join(f"[[{p}]]" for p in projects))
        for label, _ in GROUPS:
            counts = found[stem].get(label)
            if counts:
                best = sorted(counts, key=lambda name: (counts[name], name), reverse=True)[:shown]
                more = " · …" if len(counts) > shown else ""
                lines.append(f"- {label} ({len(counts)}) : " + " · ".join(f"[[{n}]]" for n in best) + more)
        old = texts[stem]
        if not lines and not VAULT_SECTION.search(old):
            continue
        new = VAULT_SECTION.sub("", old).rstrip("\n") + "\n"
        if lines:
            new += "\n## Dans le vault\n" + "\n".join(lines) + "\n"
        if new != old:
            path.write_text(new, encoding="utf-8")
            changed += 1
    print(f"OK {len(notes)} notes, {changed} changed")
    return 0


def check(vault: Path) -> int:
    by_level = elements(vault)
    names = unique_names(vault)
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
            for term in as_list(data.get("match")):
                try:
                    re.compile(term)
                except re.error:
                    fail(path, f"match value {term!r} is not a regular expression")
            if data.get("level") is not None and data["level"] not in MASTERY:
                fail(path, f"level value {str(data['level'])!r} is not one of {', '.join(MASTERY)}")
    for level in LEVELS:
        for stem, path in by_level[level].items():
            if stem not in linked:
                warns.append(f"WARN {path.relative_to(vault).as_posix()}: no project and no ontologie note links it")
    print("\n".join(sorted(fails) + warns + ([] if fails else [f"OK {len(known)} elements"])))
    return 1 if fails else 0


COMMANDS = {"activity": activity, "check": check, "mentions": mentions}


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in COMMANDS or len(args) > 2:
        print(__doc__, file=sys.stderr)
        return 2
    settings = Settings()
    root = Path(args[1]) if len(args) == 2 else settings.brain_path
    if root is None or not root.is_dir():
        logger.error("no vault (give VAULT or set BRAIN_PATH)")
        return 2
    if not (root / "ontologie").is_dir():
        logger.error("no ontologie/ folder in {}", root)
        return 2
    if args[0] == "mentions":
        return mentions(root, settings.ontologie_shown)
    return COMMANDS[args[0]](root)


if __name__ == "__main__":
    sys.exit(main())
