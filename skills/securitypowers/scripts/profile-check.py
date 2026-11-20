#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = ["pyyaml==6.0.2"]
# ///
"""Is the project's .agents/security-profile.md present and fresh?

Usage: uv run --script profile-check.py [--hash] <project_dir>
  prints `ok` | `missing` | `stale: <reason>`   (exit 0 | 1 | 2)
  --hash prints the sha256 of the files listed under `sources:` (write it into `sources_sha256`).
Env: PROFILE_MAX_AGE_DAYS (default 90), TODAY (YYYY-MM-DD, default today in UTC).
"""
import hashlib
import os
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

import yaml

FRONT_MATTER = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n", re.S)


class Stale(Exception):
    pass


def _front_matter(profile: Path) -> dict:
    m = FRONT_MATTER.match(profile.read_text(encoding="utf-8"))
    if not m:
        raise Stale("no front matter")
    try:
        data = yaml.safe_load(m.group(1))
    except yaml.YAMLError:
        raise Stale("front matter is not valid YAML") from None
    if not isinstance(data, dict):
        raise Stale("no front matter")
    return data


def _digest(project: Path, sources: object) -> str:
    if not isinstance(sources, list) or not sources:
        raise Stale("no sources")
    h = hashlib.sha256()
    for src in sources:
        path = project / str(src).strip()
        if not path.is_file():
            raise Stale(f"source missing {src}")
        try:
            h.update(path.read_bytes())
        except OSError:
            raise Stale(f"cannot read {src}") from None
    return h.hexdigest()


def _reviewed(value: object) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if value is None:
        raise Stale("no reviewed date")
    try:
        return date.fromisoformat(str(value).strip())
    except ValueError:
        raise Stale(f"bad reviewed date '{value}'") from None


def check(project: Path, today: date, max_age: int) -> str:
    profile = project / ".agents/security-profile.md"
    if not profile.is_file():
        return "missing"
    front = _front_matter(profile)
    reviewed = _reviewed(front.get("reviewed"))
    age = (today - reviewed).days
    if age < 0:
        raise Stale("reviewed date in the future")
    if age > max_age:
        raise Stale(f"reviewed {age} days ago")
    if _digest(project, front.get("sources")) != str(front.get("sources_sha256", "")).strip():
        raise Stale("sources changed")
    return "ok"


def main(argv: list[str]) -> int:
    args = argv[1:]
    hash_only = bool(args) and args[0] == "--hash"
    if hash_only:
        args = args[1:]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 64
    project = Path(args[0])
    try:
        if hash_only:
            profile = project / ".agents/security-profile.md"
            if not profile.is_file():
                print("missing")
                return 1
            print(_digest(project, _front_matter(profile).get("sources")))
            return 0
        today = date.fromisoformat(os.environ.get("TODAY") or datetime.now(timezone.utc).date().isoformat())
        result = check(project, today, int(os.environ.get("PROFILE_MAX_AGE_DAYS", "90")))
    except Stale as e:
        print(f"stale: {e}")
        return 2
    print(result)
    return 0 if result == "ok" else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
