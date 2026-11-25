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


def test_brief_missing_or_unknown_anchor_is_unknown():
    t = text()
    assert "cat-file -e" in t and "ancre absente ou inconnue" in t


def test_brief_redacts_secrets_from_allowed_commands():
    t = text()
    assert "--format" in t and ".Config.Env" in t and "masque" in t


def test_brief_allowlist_forbids_chaining():
    t = text()
    for token in ["`;`", "`&&`", "`||`", "`$(`", "`--data`", "`--request`", "`-o`"]:
        assert token in t, token


def test_brief_remote_calls_never_prompt():
    t = text()
    assert "BatchMode=yes" in t and "sudo -n" in t and "refus d'authentification" in t


def test_brief_null_remote_gives_no_clone_command():
    t = text()
    assert "pas de remote" in t and 'LAB_ROOT:=$HOME/lab_perso' in t
