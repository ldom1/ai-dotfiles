"""The veille skill quotes non-GitHub pages with a local tool, not a cloud scraper."""
from pathlib import Path

SKILL = (
    Path(__file__).resolve().parents[3]
    / "skills/veille-technique/skills/veille/SKILL.md"
)


def test_veille_uses_defuddle():
    text = SKILL.read_text()
    assert "npx -y defuddle@0.19.6 parse" in text
    assert "--md" in text
    assert "firecrawl" not in text.lower()
    assert "WebFetch" in text
    assert "paraphrase" in text
    assert "If defuddle fails or prints nothing" in text
