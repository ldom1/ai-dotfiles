#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["ruamel.yaml==0.19.1", "loguru==0.7.3", "pydantic==2.14.4", "pydantic-settings==2.7.1"]
# ///
"""pattern-drift.py: keep the rule ids of the vault pattern notes consistent.

  check [--vault V] [--rules R]   print FAIL <file>: <reason> per problem (exit 1), or OK <n> rules (exit 0)
  scan [--vault V] [--lab-root L] open or close a migration task in the ROADMAP.md of each active repo, print a summary

V defaults to $BRAIN_PATH. R defaults to skills/brain-audit/reference/pitfall-rules.md (the declared letters).

A rule is a bullet at column 0, outside a code fence, under `## Rules` and its `###` subsections. It ends with its
id (`^p4`). A link `[[note#^v5]]` is not an id. `→ ^p9` after the id says a rule of a `-superseded` note moved to
the active rule `^p9`.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tomllib
from collections import Counter
from dataclasses import dataclass
from datetime import date, timedelta
from io import StringIO
from pathlib import Path
from typing import Literal

from loguru import logger
from pydantic import BaseModel, ValidationError, model_validator
from pydantic_settings import BaseSettings
from ruamel.yaml import YAML
from ruamel.yaml.error import YAMLError

PATTERNS = "resources/knowledge/patterns"
SUPERSEDED = "-superseded"
ID = re.compile(r"(?<![#\w])\^([a-z])(\d+)\b")
TARGET = re.compile(r"→\s*\^([a-z]\d+)\b")
LETTER = re.compile(r"`([a-z])` [\w-]+")
FENCE = re.compile(r"^\s*(```|~~~)")
H2 = re.compile(r"^## (.*?)\s*$")
SUPERSEDED_BULLET = re.compile(r"^- ~~(.*)~~ → \^([a-z]\d+) \((\d{4}-\d{2}-\d{2}), (.*)\) \^([a-z]\d+)\s*$")
IGNORED_DIRS = {".git", ".venv", "node_modules"}
AST_GREP = "ast-grep"  # never `sg`: /usr/bin/sg is shadow-utils


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
    sections = {"Rules", "Superseded"} if superseded else {"Rules"}
    fence_line = 0
    for number, line in enumerate(note.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            fence_line = 0 if fence_line else number
            continue
        if fence_line:
            continue
        heading = H2.match(line)
        if heading:
            in_rules = heading.group(1) in sections
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
        fails.append(f"FAIL {note.name}: no {'## Superseded' if superseded else '## Rules'}")
    return rules, fails


class TomlCond(BaseModel):
    key: str
    equals: str | None = None
    absent: bool = False


class Detect(BaseModel):
    lang: Literal["python", "toml"]
    files: list[str]
    rule: str | None = None
    absent_in_repo: str | None = None
    all: list[TomlCond] | None = None

    @model_validator(mode="after")
    def _toml_needs_conditions(self) -> "Detect":
        if self.lang == "toml" and not self.all:
            raise ValueError("a toml detect needs at least one condition in `all`")
        return self


@dataclass
class Superseded:
    id: str
    by: str
    date: str
    reason: str
    detect: Detect | None
    note: Path
    detect_error: str | None = None  # set when a detect block exists but is invalid (detect is then None)


@dataclass
class Outcome:
    state: Literal["match", "absent", "incomplete"]
    files: list[str]
    reason: str = ""


def _load_detect(block: list[str]) -> Detect:
    """The YAML of a `detect:` block (lines indented under the bullet)."""
    indent = min(len(line) - len(line.lstrip()) for line in block if line.strip())
    text = "\n".join(line[indent:] for line in block)
    data = YAML(typ="safe").load(StringIO(text))
    if not isinstance(data, dict) or "detect" not in data:
        raise ValueError("expected a `detect:` mapping")
    return Detect.model_validate(data["detect"])


def parse_superseded(note: Path) -> tuple[list[Superseded], list[str]]:
    """The superseded rules of a `-superseded` note (bullets under `## Superseded`), and FAIL lines."""
    found: list[Superseded] = []
    fails: list[str] = []
    current: tuple[int, re.Match[str]] | None = None
    block: list[str] = []
    in_section = False
    fence = False

    def flush() -> None:
        if current is None:
            return
        number, m = current
        detect = error = None
        if block:
            try:
                detect = _load_detect(block)
            except (YAMLError, ValidationError, ValueError) as exc:
                error = " ".join(str(exc).split()) or type(exc).__name__
                fails.append(f"FAIL {note.name}: invalid detect for ^{m.group(5)} at line {number}: {error}")
        found.append(Superseded(m.group(5), m.group(2), m.group(3), m.group(4), detect, note, error))

    for number, line in enumerate(note.read_text(encoding="utf-8").splitlines(), 1):
        if FENCE.match(line):
            fence = not fence
            continue
        if fence:
            continue
        heading = H2.match(line)
        if heading:
            flush()
            current, block = None, []
            in_section = heading.group(1) == "Superseded"
            continue
        if not in_section:
            continue
        if line.startswith("- "):
            flush()
            current, block = None, []
            m = SUPERSEDED_BULLET.match(line)
            if m:
                current = (number, m)
            elif ID.search(TARGET.sub("", line)):
                fails.append(f"FAIL {note.name}: malformed superseded bullet at line {number}")
        elif current and (line.startswith(" ") or not line.strip()):
            block.append(line)
    flush()
    return found, fails


def _glob_regex(pattern: str) -> re.Pattern[str]:
    out, i = "", 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        elif pattern[i] == "?":
            out, i = out + "[^/]", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(out + r"\Z")


def _deleted(path: Path) -> bool:
    """A tracked file removed from the work tree. An unreadable parent is not a deletion."""
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    except OSError:
        return False
    return False


def _candidates(repo: Path) -> tuple[list[str], str]:
    """Repo-relative files git knows (tracked, or untracked and not ignored), minus `.git`, `.venv`, `node_modules`.

    Ignored directories (a root-owned Docker data dir, say) are never visited. Second item: error, or "".
    """
    try:
        done = subprocess.run(["git", "-C", str(repo), "ls-files", "-z", "-co", "--exclude-standard"],
                              capture_output=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as exc:
        return [], f"git ls-files failed: {exc}"
    if done.returncode != 0 or done.stderr.strip():  # git only warns (exit 0) on a directory it cannot open
        return [], f"git ls-files failed: {done.stderr.decode(errors='replace').strip()}"
    names = [n for n in done.stdout.decode("utf-8", errors="surrogateescape").split("\0") if n]
    return sorted(n for n in names if not IGNORED_DIRS.intersection(n.split("/")) and not _deleted(repo / n)), ""


def _expand(candidates: list[str], patterns: list[str]) -> list[str]:
    """The candidates matching one of the globs."""
    regexes = [_glob_regex(p) for p in patterns]
    return [c for c in candidates if any(r.match(c) for r in regexes)]


def _unreadable(repo: Path, files: list[str]) -> str:
    """First file that cannot be read, as `file: reason`, or ""."""
    for rel in files:
        try:
            with open(repo / rel, "rb") as handle:
                handle.read(1)
        except OSError as exc:
            return f"{rel}: {exc.strerror}"
    return ""


def _ast_grep(repo: Path, args: list[str]) -> list[dict] | None:
    """Parsed JSON hits of an ast-grep call, or None when it fails."""
    try:
        done = subprocess.run([AST_GREP, *args], cwd=repo, capture_output=True, text=True, timeout=300)
        # `run` exits 1 when nothing matches, with `[]` on stdout: only a code above 1 or no JSON is a failure
        if done.returncode > 1 or (done.returncode == 1 and not done.stdout.strip()):
            return None
        data = json.loads(done.stdout or "[]")
    except (OSError, subprocess.SubprocessError, json.JSONDecodeError):
        return None
    return data if isinstance(data, list) else None


def _toml_value(doc: dict, key: str) -> tuple[bool, object]:
    node: object = doc
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return False, None
        node = node[part]
    return True, node


def _evaluate_toml(repo: Path, detect: Detect, files: list[str]) -> Outcome:
    conds = detect.all or []
    hits: list[str] = []
    for rel in files:
        try:
            doc = tomllib.loads((repo / rel).read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError) as exc:
            return Outcome("incomplete", [], f"{rel}: {exc}")
        ok = True
        for cond in conds:
            present, value = _toml_value(doc, cond.key)
            if cond.absent:
                ok = ok and not present
            else:
                ok = ok and present and (cond.equals is None or value == cond.equals)
        if ok:
            hits.append(rel)
    return Outcome("match" if hits else "absent", hits)


def evaluate(repo: Path, detect: Detect) -> Outcome:
    """Does the old form still exist in the repo? match / absent (verified) / incomplete (could not tell)."""
    candidates, error = _candidates(repo)
    if error:
        return Outcome("incomplete", [], error)
    files = _expand(candidates, detect.files)
    if not files:
        return Outcome("absent", [])
    bad = _unreadable(repo, files)  # ast-grep exits 0 on an unreadable explicit file
    if bad:
        return Outcome("incomplete", [], f"unreadable: {bad}")
    if detect.lang == "toml":
        if not detect.all:
            return Outcome("incomplete", [], "toml detect without conditions")
        return _evaluate_toml(repo, detect, files)
    if not detect.rule:
        return Outcome("incomplete", [], "python detect without rule")
    if not shutil.which(AST_GREP):
        return Outcome("incomplete", [], f"{AST_GREP} not found in PATH")
    hits = _ast_grep(repo, ["scan", "--inline-rules", detect.rule, "--json=compact", *files])
    if hits is None:
        return Outcome("incomplete", [], f"{AST_GREP} scan failed")
    try:
        matched = sorted({h["file"] for h in hits})
    except (KeyError, TypeError):
        return Outcome("incomplete", [], f"{AST_GREP} scan gave unexpected JSON")
    if not matched:
        return Outcome("absent", [])
    if detect.absent_in_repo:
        sources = [c for c in candidates if c.endswith(".py")]
        bad = _unreadable(repo, sources)
        if bad:
            return Outcome("incomplete", [], f"unreadable: {bad}")
        for start in range(0, len(sources), 200):
            found = _ast_grep(repo, ["run", "-p", detect.absent_in_repo, "-l", "python", "--json=compact",
                                     *sources[start:start + 200]])
            if found is None:
                return Outcome("incomplete", [], f"{AST_GREP} run failed")
            if found:
                return Outcome("absent", [], "replacement pattern present in repo")
    return Outcome("match", matched)


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
        if note.stem.endswith(SUPERSEDED):
            fails += parse_superseded(note)[1]
    stems = [n.stem for n in (vault / PATTERNS).glob("*.md") if not n.stem.endswith(SUPERSEDED)]
    owners = {letter: next((s for s in stems if s == name or s.startswith(name + "-")), None)
              for letter, name in letters.items()}  # no owner: a `pitfalls.md` letter, kept when a rule moves out
    seen: dict[str, Rule] = {}
    for rule in rules:
        if rule.id[0] not in letters:
            fails.append(f"FAIL {rule.note.name}: letter {rule.id[0]} not in {rules_file.name}")
        owner, base = owners.get(rule.id[0]), rule.note.stem.removesuffix(SUPERSEDED)
        if owner and owner != base:
            fails.append(f"FAIL {rule.note.name}: ^{rule.id} uses letter {rule.id[0]} of {owner}")
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


@dataclass
class Repo:
    slug: str
    path: Path


FRONT = re.compile(r"^(status|path|repo):\s*(.*?)\s*$")
REMOTE = re.compile(r"^(?:[a-z+]+://)?(?:[^@/]+@)?([^/:]+)[:/](.+?)(?:\.git)?/*$")
LOG_DATE = re.compile(r"^(\d{4}-\d{2}-\d{2})-")


def _front(note: Path) -> dict[str, str]:
    """`status:`, `path:` and `repo:` of the frontmatter of a project note."""
    out: dict[str, str] = {}
    lines = note.read_text(encoding="utf-8").splitlines()
    if lines and lines[0].strip() == "---":
        for line in lines[1:]:
            if line.strip() == "---":
                break
            m = FRONT.match(line)
            if m:
                out[m.group(1)] = m.group(2).strip("\"'")
    return out


def _same_remote(path: Path, url: str) -> bool:
    """True when the `origin` remote of `path` names the same host/owner/repo as `url` (scheme, `.git`, case ignored)."""
    try:
        done = subprocess.run(["git", "remote", "get-url", "origin"], cwd=path, capture_output=True, text=True,
                              timeout=60)
    except (OSError, subprocess.SubprocessError):
        return False
    a, b = REMOTE.match(done.stdout.strip().lower()), REMOTE.match(url.strip().lower())
    return done.returncode == 0 and bool(a and b) and a.groups() == b.groups()


def _recent_log(vault: Path, slug: str, days: int) -> bool:
    limit = date.today() - timedelta(days=days)
    for log in (vault / "inbox/daily/implementation" / slug).glob("*.md"):
        m = LOG_DATE.match(log.name)
        if m:
            try:
                if date.fromisoformat(m.group(1)) >= limit:
                    return True
            except ValueError:
                continue
    return False


def active_repos(vault: Path, lab_root: Path, days: int, dormant: list[Repo] | None = None,
                 warns: list[str] | None = None) -> tuple[list[Repo], Counter[str]]:
    """Repos of the `status: active` project notes that pass the activity rule, and the skipped ones by reason."""
    repos: list[Repo] = []
    skipped: Counter[str] = Counter()
    seen: set[Path] = set()
    for note in sorted((vault / "projects").glob("*.md")):
        slug = note.stem
        try:
            front = _front(note)
        except (OSError, UnicodeDecodeError):
            skipped["unreadable"] += 1
            if warns is not None:
                warns.append(f"WARN unreadable {slug}")
            continue
        if front.get("status") != "active":
            continue
        if front.get("path"):
            path = Path(front["path"]).expanduser()
            if not path.is_dir():  # the note may name a clone path of another machine
                found = next((c for c in (lab_root / path.name, lab_root / slug) if c.is_dir()), None)
                # a folder with the same name may be another repo: when the note has `repo:`, `origin` must match it
                if found and (not front.get("repo") or _same_remote(found, front["repo"])):
                    path = found
            missing = f"not-cloned {slug} {front['path']}"
        else:
            path = lab_root / slug
            missing = f"no-path {slug}"
        if not path.is_dir():
            skipped[missing.split()[0]] += 1
            if warns is not None:
                warns.append(f"WARN {missing}")
            continue
        if not (path / ".git").exists():
            skipped["not-cloned"] += 1
            continue
        key = path.resolve()
        if key in seen:
            continue
        seen.add(key)
        try:
            done = subprocess.run(["git", "log", "-1", "--all", "--format=%H", f"--since={days}.days"], cwd=path,
                                  capture_output=True, text=True, timeout=60)
        except (OSError, subprocess.SubprocessError):
            skipped["git-error"] += 1
            continue
        if done.returncode != 0:
            skipped["git-error"] += 1
        elif done.stdout.strip() or _recent_log(vault, slug, days):
            repos.append(Repo(slug, path))
        else:
            skipped["dormant"] += 1
            if dormant is not None:
                dormant.append(Repo(slug, path))
    return repos, skipped


MARKER = "<!-- pattern-drift:^{} -->"


def _section(lines: list[bytes]) -> list[str]:
    """The `## ` heading each line sits under ('' before the first)."""
    heading, out = "", []
    for raw in lines:
        m = H2.match(raw.decode("utf-8", "replace").rstrip("\r\n"))
        if m:
            heading = m.group(1)
        out.append(heading)
    return out


def _open_markers(roadmap: Path) -> list[str]:
    """Ids of the `pattern-drift` markers under a `## Next` heading of `roadmap` (empty if unreadable)."""
    try:
        lines = roadmap.read_bytes().splitlines(keepends=True)
    except OSError:
        return []
    found = []
    for raw, heading in zip(lines, _section(lines)):
        m = re.search(rb"<!-- pattern-drift:\^(\w+) -->", raw)
        if m and heading == "Next":
            found.append(m.group(1).decode())
    return found


def apply_task(roadmap: Path, sup: Superseded, outcome: Outcome) -> Literal["opened", "closed", "kept", "none"]:
    """Open (match) or close (verified absent) the migration line of `sup` in `roadmap`; never rewrites another line."""
    data = roadmap.read_bytes()
    lines = data.splitlines(keepends=True)
    marker = MARKER.format(sup.id).encode()
    marked = [i for i, raw in enumerate(lines) if marker in raw]
    sections = _section(lines)
    if outcome.state == "incomplete":
        return "kept" if marked else "none"
    if outcome.state == "absent":
        under_next = [i for i in marked if sections[i] == "Next"]
        if not under_next:
            return "kept" if marked else "none"
        for i in reversed(under_next):
            del lines[i]
        roadmap.write_bytes(b"".join(lines))
        return "closed"
    if marked:
        return "kept"
    eol = b"\r\n" if b"\r\n" in data else b"\n"
    reason = sup.reason if len(sup.reason) <= 80 else sup.reason[:79].rstrip() + "…"
    files = ", ".join(f"`{f}`" for f in outcome.files)
    task = f"- Migrate: ^{sup.id} → ^{sup.by} ({reason}) in {files} {MARKER.format(sup.id)}".encode() + eol
    start = next((i for i, raw in enumerate(lines) if H2.match(raw.decode("utf-8", "replace").rstrip("\r\n"))
                  and sections[i] == "Next"), None)
    if start is None:
        if lines and not lines[-1].endswith((b"\n", b"\r")):
            lines[-1] += eol
        lines += [eol, b"## Next" + eol, task] if lines else [b"## Next" + eol, task]
    else:
        end = start + 1
        while end < len(lines) and sections[end] == "Next":
            end += 1
        while end - 1 > start and not lines[end - 1].strip():
            end -= 1
        if not lines[end - 1].endswith((b"\n", b"\r")):
            lines[end - 1] += eol
        lines.insert(end, task)
    roadmap.write_bytes(b"".join(lines))
    return "opened"


def scan(vault: Path, lab_root: Path, days: int) -> str:
    """Open or close the migration tasks of every active repo; print one line per action, return the summary."""
    dormant: list[Repo] = []
    warns: list[str] = []
    repos, skipped = active_repos(vault, lab_root, days, dormant, warns)
    for warn in warns:
        print(warn)
    sups: list[Superseded] = []
    for note in sorted((vault / PATTERNS).glob(f"*{SUPERSEDED}.md")):
        try:
            sups += parse_superseded(note)[0]
        except (OSError, UnicodeDecodeError):
            print(f"WARN unreadable {note.name}")
    matches = opened = closed = incomplete = 0
    modified: list[str] = []
    for repo in repos:
        roadmap = repo.path / ".claude/memory/ROADMAP.md"
        for sup in sups:
            if sup.detect_error:
                outcome = Outcome("incomplete", [], f"invalid detect: {sup.detect_error}")
            elif sup.detect is None:
                continue
            else:
                outcome = evaluate(repo.path, sup.detect)
            if outcome.state == "incomplete":
                incomplete += 1
                print(f"incomplete {repo.slug} ^{sup.id} {outcome.reason}")
                continue
            matches += outcome.state == "match"
            if not roadmap.is_file():
                if outcome.state == "match":
                    print(f"WARN no ROADMAP {repo.slug} ^{sup.id}")
                continue
            try:
                action = apply_task(roadmap, sup, outcome)
            except OSError as exc:
                print(f"WARN unwritable {repo.slug} ROADMAP.md: {exc.strerror}")
                skipped["unwritable"] += 1
                break
            if action in ("opened", "closed"):
                opened += action == "opened"
                closed += action == "closed"
                print(f"{action} {repo.slug} ^{sup.id}")
                if repo.slug not in modified:
                    modified.append(repo.slug)
    for repo in dormant:  # read-only: open tasks of dormant repos are listed for the digest, never closed
        for line in _open_markers(repo.path / ".claude/memory/ROADMAP.md"):
            print(f"dormant {repo.slug} ^{line}")
    for slug in modified:
        print(f"modified {slug} (ROADMAP.md, not committed)")
    reasons = ", ".join(f"{k}: {v}" for k, v in sorted(skipped.items()))
    skip = f"skipped {sum(skipped.values())}" + (f" ({reasons})" if reasons else "")
    return (f"scanned {len(repos)} repos · {skip} · matches {matches} · opened {opened} · closed {closed}"
            f" · incomplete {incomplete}")


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if not args or args[0] not in ("check", "scan"):
        print(__doc__, file=sys.stderr)
        return 2
    settings = Settings()
    vault, rules_file, lab_root = settings.brain_path, settings.rules_file, settings.lab_root
    flags = ("--vault", "--rules") if args[0] == "check" else ("--vault", "--lab-root")
    rest = args[1:]
    while rest:
        if rest[0] in flags and len(rest) >= 2:
            if rest[0] == "--vault":
                vault = Path(rest[1])
            elif rest[0] == "--lab-root":
                lab_root = Path(rest[1])
            else:
                rules_file = Path(rest[1])
            rest = rest[2:]
        else:
            print(__doc__, file=sys.stderr)
            return 2
    if vault is None or not (vault / PATTERNS).is_dir():
        logger.error("no vault with {} (give --vault or set BRAIN_PATH)", PATTERNS)
        return 2
    if args[0] == "scan":
        print(scan(vault, lab_root, settings.active_days))
        return 0
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
