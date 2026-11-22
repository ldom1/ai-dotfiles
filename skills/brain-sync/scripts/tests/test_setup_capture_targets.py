import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from setup_capture_targets import ALL_STEPS, plan_schema


def rel(db: str) -> dict:
    return {"type": "relation", "relation": {"database_id": db}}


CHECK = {"type": "checkbox", "checkbox": {}}

# Shapes copied from the live workspace on 2026-11-22 (names and types only).
CAPTURES_NOW = {
    "Name": {"type": "title", "title": {}},
    "Laboratoire": rel("lab"),
    "Tools": rel("tools"),
    "Notions": rel("notions"),
    "Data & Tech": rel("dt"),
    "Veille faite": CHECK,
    "Triée": CHECK,
}
LAB_NOW = {
    "Nom": {"type": "title", "title": {}},
    "Sources": rel("captures"),
    "Outils": rel("tools"),
}
PROJECTS_NOW = {
    "Nom du projet": {"type": "title", "title": {}},
    "Related to Data & technology (Artelys projects)": rel("dt"),
}
CAPTURES_DONE = CAPTURES_NOW | {"Cible": rel("targets"), "Veille cible faite": CHECK}
LAB_DONE = LAB_NOW | {"Projet": rel("projects")}
PROJECTS_DONE = PROJECTS_NOW | {
    "Idée d'origine": rel("lab"),
    "Sources d'origine": {"type": "rollup", "rollup": {}},
    "Outils d'origine": {"type": "rollup", "rollup": {}},
}
TARGETS_DONE = {
    "Nom": {"type": "title", "title": {}},
    "Slug": {"type": "rich_text", "rich_text": {}},
    "Résumé": {"type": "rich_text", "rich_text": {}},
    "Actif": CHECK,
    "Captures": rel("captures"),
}


def test_plan_on_the_live_shape_lists_everything() -> None:
    assert plan_schema(CAPTURES_NOW, LAB_NOW, PROJECTS_NOW, None) == [
        "create targets db",
        "add Cible",
        "rename Cible reverse",
        "add Veille cible faite",
        "add Projet",
        "rename Projet reverse",
        "add rollup Sources d'origine",
        "add rollup Outils d'origine",
    ]
    assert plan_schema(CAPTURES_NOW, LAB_NOW, PROJECTS_NOW, None) == ALL_STEPS


def test_plan_is_empty_when_everything_exists() -> None:
    assert plan_schema(CAPTURES_DONE, LAB_DONE, PROJECTS_DONE, TARGETS_DONE) == []


def test_reverse_not_renamed_yet_is_the_only_step_left() -> None:
    targets = {k: v for k, v in TARGETS_DONE.items() if k != "Captures"}
    targets["Related to DomTelegramBot (Cible)"] = rel("captures")
    assert plan_schema(CAPTURES_DONE, LAB_DONE, PROJECTS_DONE, targets) == ["rename Cible reverse"]


def test_existing_veille_faite_is_never_planned() -> None:
    steps = plan_schema(CAPTURES_NOW, LAB_NOW, PROJECTS_NOW, None)
    assert not any("Veille faite" in s and "cible" not in s for s in steps)
