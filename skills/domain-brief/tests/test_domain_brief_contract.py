"""Contract of the domain-brief skill: the rules of the spec that the text must carry."""
import re
from pathlib import Path

SKILL = Path(__file__).parents[1] / "SKILL.md"


def text() -> str:
    return SKILL.read_text(encoding="utf-8")


def test_brief_has_frontmatter_name():
    assert re.search(r"^name: domain-brief$", text(), re.M)


def test_brief_keeps_unknown_freshness():
    t = text()
    assert "inconnue" in t and "git fetch" in t and "origin/" in t


def test_brief_live_allowlist_is_exact():
    t = text()
    for cmd in ["docker inspect", "docker ps", "df", "findmnt", "systemctl status", "curl -sI", "sudo nginx -T"]:
        assert f"`{cmd}`" in t, cmd


def test_brief_never_reads_secret_values():
    t = text()
    assert "noms de clés" in t and "jamais une valeur" in t


def test_brief_separates_observed_and_expected():
    t = text()
    assert "état observé" in t and "état attendu" in t


def test_brief_checks_registry_against_dashboard():
    assert "app/config.py" in text()


def test_brief_is_read_only():
    assert "Ne modifie aucun fichier" in text()
