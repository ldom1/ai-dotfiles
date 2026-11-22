#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1", "pyyaml==6.0.2", "loguru==0.7.3", "pydantic-settings==2.7.1"]
# ///
"""sync_dev_projects.py: copy the vault's dev projects to the Notion targets database.

  [--vault PATH] [--dry-run]

Reads $BRAIN_PATH/projects/*.md front matter (title, status) and the first "> " summary line.
Upserts one Notion row per note, keyed by Slug (the filename without .md). Never deletes or
archives a row: an absent project only unchecks Actif, and only after a scan that read every file.
A malformed note is logged and skipped; its row keeps its values.
Env: BRAIN_PATH, NOTION_TOKEN, NOTION_TARGETS_DATABASE_ID. Logs counts, never the token.
"""
import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx
import yaml
from loguru import logger
from pydantic import SecretStr
from pydantic_settings import BaseSettings

NOTION = "https://api.notion.com/v1"
VERSION = "2022-06-28"
SUMMARY_CHARS = 200


class Settings(BaseSettings):
    brain_path: Path | None = None
    notion_token: SecretStr | None = None
    notion_targets_database_id: str | None = None


@dataclass(frozen=True)
class VaultProject:
    slug: str
    name: str
    summary: str
    active: bool


@dataclass(frozen=True)
class Row:
    page_id: str
    slug: str
    name: str
    summary: str
    active: bool


@dataclass(frozen=True)
class Scan:
    projects: dict[str, VaultProject]
    malformed: list[str]
    complete: bool


Op = tuple[Any, ...]


def _summary(body: str) -> str:
    lines = body.splitlines()
    after_h1 = next((i + 1 for i, line in enumerate(lines) if line.startswith("# ")), 0)
    rest = lines[after_h1:]
    quote: list[str] = []
    for line in rest:
        if line.startswith(">"):
            quote.append(line.lstrip("> ").strip())
        elif quote:
            break
    if quote:
        return " ".join(quote)[:SUMMARY_CHARS]
    para: list[str] = []
    for line in rest:
        if line.strip() and not line.startswith("#"):
            para.append(line.strip())
        elif para:
            break
    return " ".join(para)[:SUMMARY_CHARS]


def _parse(text: str) -> tuple[dict[str, Any], str] | None:
    """Front matter and body, or None when the note has no valid front matter."""
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---", 4)
    if end < 0:
        return None
    try:
        meta = yaml.safe_load(text[4:end])
    except yaml.YAMLError:
        return None
    if not isinstance(meta, dict) or not isinstance(meta.get("title"), str):
        return None
    return meta, text[end + 4 :]


def scan_vault(projects_dir: Path) -> Scan:
    projects: dict[str, VaultProject] = {}
    malformed: list[str] = []
    complete = True
    for path in sorted(projects_dir.glob("*.md")):
        slug = path.stem
        try:
            text = path.read_text(encoding="utf-8")
        except OSError as exc:
            logger.warning("unreadable note {}: {}", slug, exc)
            complete = False
            continue
        parsed = _parse(text)
        if parsed is None:
            malformed.append(slug)
            continue
        meta, body = parsed
        projects[slug] = VaultProject(slug, meta["title"], _summary(body), meta.get("status") == "active")
    return Scan(projects, malformed, complete)


def plan_sync(rows: dict[str, Row], scan: Scan) -> list[Op]:
    ops: list[Op] = []
    for slug, project in scan.projects.items():
        current = rows.get(slug)
        if current is None:
            ops.append(("create", project))
        elif (current.name, current.summary, current.active) != (project.name, project.summary, project.active):
            ops.append(("update", current.page_id, project))
    if scan.complete:
        known = set(scan.projects) | set(scan.malformed)
        ops += [("deactivate", r.page_id) for slug, r in rows.items() if slug not in known and r.active]
    return ops


def _text(value: str) -> list[dict[str, Any]]:
    return [{"type": "text", "text": {"content": value}}] if value else []


def _plain(prop: dict[str, Any]) -> str:
    return "".join(p.get("plain_text", "") for p in prop.get("title") or prop.get("rich_text") or [])


def _props(p: VaultProject) -> dict[str, Any]:
    return {
        "Nom": {"title": _text(p.name)},
        "Slug": {"rich_text": _text(p.slug)},
        "Résumé": {"rich_text": _text(p.summary)},
        "Actif": {"checkbox": p.active},
    }


def fetch_rows(http: httpx.Client, db_id: str) -> dict[str, Row]:
    rows: dict[str, Row] = {}
    body: dict[str, Any] = {"page_size": 100}
    while True:
        resp = http.post(f"/databases/{db_id}/query", json=body)
        resp.raise_for_status()
        data = resp.json()
        for page in data["results"]:
            props = page["properties"]
            slug = _plain(props["Slug"])
            if slug:
                rows[slug] = Row(page["id"], slug, _plain(props["Nom"]), _plain(props["Résumé"]), props["Actif"]["checkbox"])
        if not data.get("has_more"):
            return rows
        body["start_cursor"] = data["next_cursor"]


def apply(http: httpx.Client, db_id: str, ops: list[Op]) -> None:
    for op in ops:
        if op[0] == "create":
            body = {"parent": {"database_id": db_id}, "properties": _props(op[1])}
            http.post("/pages", json=body).raise_for_status()
        elif op[0] == "update":
            http.patch(f"/pages/{op[1]}", json={"properties": _props(op[2])}).raise_for_status()
        else:
            http.patch(f"/pages/{op[1]}", json={"properties": {"Actif": {"checkbox": False}}}).raise_for_status()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--vault", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    settings = Settings()
    vault = args.vault or settings.brain_path
    if vault is None or settings.notion_token is None or not settings.notion_targets_database_id:
        logger.error("need --vault or BRAIN_PATH, NOTION_TOKEN and NOTION_TARGETS_DATABASE_ID")
        return 2
    scan = scan_vault(vault / "projects")
    for slug in scan.malformed:
        logger.warning("malformed note skipped: {}", slug)
    http = httpx.Client(
        base_url=NOTION,
        headers={"Authorization": f"Bearer {settings.notion_token.get_secret_value()}", "Notion-Version": VERSION},
        timeout=30.0,
    )
    ops = plan_sync(fetch_rows(http, settings.notion_targets_database_id), scan)
    counts = {kind: sum(op[0] == kind for op in ops) for kind in ("create", "update", "deactivate")}
    logger.info(
        "{}created={} updated={} deactivated={} malformed={} complete={}",
        "dry-run " if args.dry_run else "",
        counts["create"], counts["update"], counts["deactivate"], len(scan.malformed), scan.complete,
    )
    if not args.dry_run:
        apply(http, settings.notion_targets_database_id, ops)
    return 0


if __name__ == "__main__":
    sys.exit(main())
