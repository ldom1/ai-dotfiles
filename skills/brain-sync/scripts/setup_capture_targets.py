#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.12"
# dependencies = ["httpx==0.28.1"]
# ///
"""setup_capture_targets.py: create the Notion schema for capture targets (one-off, idempotent).

  --parent-page ID --captures-db ID --lab-db ID --projects-db ID [--apply]

Without --apply it prints the missing pieces only (dry run). With --apply it creates them in
order and re-reads the databases after each step, so a rerun is a no-op.
Pieces: the targets database "Projets dev" (Nom, Slug, Résumé, Actif), DomTelegramBot.Cible
(two-way, reverse renamed "Captures"), DomTelegramBot."Veille cible faite", Laboratoire.Projet
(two-way to Projects, reverse renamed "Idée d'origine") and two rollups on Projects.
Env: NOTION_TOKEN. Prints NOTION_TARGETS_DATABASE_ID=<id> at the end. Never prints the token.
"""
import argparse
import os
import sys
from typing import Any

import httpx

NOTION = "https://api.notion.com/v1"
VERSION = "2022-06-28"
TARGETS_TITLE = "Projets dev"
ALL_STEPS = [
    "create targets db",
    "add Cible",
    "rename Cible reverse",
    "add Veille cible faite",
    "add Projet",
    "rename Projet reverse",
    "add rollup Sources d'origine",
    "add rollup Outils d'origine",
]
ROLLUPS = {"Sources d'origine": "Sources", "Outils d'origine": "Outils"}

Props = dict[str, Any]


def plan_schema(captures: Props, lab: Props, projects: Props, targets: Props | None) -> list[str]:
    """Missing pieces, in apply order. Inputs are `properties` objects of GET /databases/{id};
    `targets` is None when the targets database does not exist yet."""
    steps = []
    if targets is None:
        steps.append("create targets db")
    if "Cible" not in captures:
        steps.append("add Cible")
    if targets is None or "Captures" not in targets:
        steps.append("rename Cible reverse")
    if "Veille cible faite" not in captures:
        steps.append("add Veille cible faite")
    if "Projet" not in lab:
        steps.append("add Projet")
    if "Idée d'origine" not in projects:
        steps.append("rename Projet reverse")
    steps += [f"add rollup {name}" for name in ROLLUPS if name not in projects]
    return steps


def _norm(db_id: str) -> str:
    return db_id.replace("-", "")


def reverse_name(props: Props, target_db: str) -> str | None:
    """Name of the relation property in `props` that points at `target_db`, if any."""
    for name, prop in props.items():
        if prop.get("type") == "relation" and _norm(prop["relation"].get("database_id", "")) == _norm(target_db):
            return name
    return None


class Notion:
    def __init__(self, token: str) -> None:
        self.http = httpx.Client(
            base_url=NOTION,
            headers={"Authorization": f"Bearer {token}", "Notion-Version": VERSION},
            timeout=30.0,
        )

    def props(self, db_id: str) -> Props:
        resp = self.http.get(f"/databases/{db_id}")
        resp.raise_for_status()
        return resp.json()["properties"]

    def patch(self, db_id: str, properties: Props) -> None:
        self.http.patch(f"/databases/{db_id}", json={"properties": properties}).raise_for_status()

    def create_targets(self, parent_page: str) -> str:
        body = {
            "parent": {"type": "page_id", "page_id": parent_page},
            "title": [{"type": "text", "text": {"content": TARGETS_TITLE}}],
            "properties": {
                "Nom": {"title": {}},
                "Slug": {"rich_text": {}},
                "Résumé": {"rich_text": {}},
                "Actif": {"checkbox": {}},
            },
        }
        resp = self.http.post("/databases", json=body)
        resp.raise_for_status()
        return str(resp.json()["id"])


def apply_step(n: Notion, step: str, a: argparse.Namespace, targets_id: str | None) -> str | None:
    """Run one step; return the targets database id (new or unchanged)."""
    if step == "create targets db":
        return n.create_targets(a.parent_page)
    assert targets_id, "targets database id unknown"
    if step == "add Cible":
        n.patch(a.captures_db, {"Cible": {"relation": {"database_id": targets_id, "dual_property": {}}}})
    elif step == "rename Cible reverse":
        old = reverse_name(n.props(targets_id), a.captures_db)
        if old is None:
            raise RuntimeError("Cible has no reverse property on the targets database")
        n.patch(targets_id, {old: {"name": "Captures"}})
    elif step == "add Veille cible faite":
        n.patch(a.captures_db, {"Veille cible faite": {"checkbox": {}}})
    elif step == "add Projet":
        n.patch(a.lab_db, {"Projet": {"relation": {"database_id": a.projects_db, "dual_property": {}}}})
    elif step == "rename Projet reverse":
        old = reverse_name(n.props(a.projects_db), a.lab_db)
        if old is None:
            raise RuntimeError("Projet has no reverse property on Projects")
        n.patch(a.projects_db, {old: {"name": "Idée d'origine"}})
    else:
        name = step.removeprefix("add rollup ")
        rollup = {
            "relation_property_name": "Idée d'origine",
            "rollup_property_name": ROLLUPS[name],
            "function": "show_original",
        }
        n.patch(a.projects_db, {name: {"rollup": rollup}})
    return targets_id


def current(n: Notion, a: argparse.Namespace) -> tuple[list[str], str | None]:
    captures = n.props(a.captures_db)
    cible = captures.get("Cible", {})
    targets_id = cible.get("relation", {}).get("database_id") or a.targets_db
    targets = n.props(targets_id) if targets_id else None
    return plan_schema(captures, n.props(a.lab_db), n.props(a.projects_db), targets), targets_id


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for flag in ("--parent-page", "--captures-db", "--lab-db", "--projects-db"):
        p.add_argument(flag, required=True)
    p.add_argument("--targets-db", help="targets database id, when it exists but Cible does not yet")
    p.add_argument("--apply", action="store_true")
    a = p.parse_args(argv)
    token = os.environ.get("NOTION_TOKEN")
    if not token:
        print("NOTION_TOKEN is not set", file=sys.stderr)
        return 2
    n = Notion(token)
    steps, targets_id = current(n, a)
    for step in steps:
        print(f"{'apply' if a.apply else 'plan'}: {step}")
    if not a.apply:
        return 0
    done: set[str] = set()
    while steps:
        step = steps[0]
        if step in done:
            raise RuntimeError(f"step did not take effect: {step}")
        targets_id = apply_step(n, step, a, targets_id)
        a.targets_db = targets_id
        done.add(step)
        steps, targets_id = current(n, a)
    print("reminder: set 'Sources d'origine' and 'Outils d'origine' to 'hide if empty' on Projects (UI only)")
    print(f"NOTION_TARGETS_DATABASE_ID={targets_id}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
