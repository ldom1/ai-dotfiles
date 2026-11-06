import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]


def skill_text() -> str:
    return (REPO / "skills/capture/SKILL.md").read_text(encoding="utf-8")


def template_headers(name: str) -> list[str]:
    text = (REPO / "config/memory-templates" / name).read_text(encoding="utf-8")
    return re.findall(r"^## (.+)$", text, re.M)


def test_roadmap_template_and_capture_agree():
    assert template_headers("ROADMAP.md") == [
        "Now", "Next", "Later", "Open debt", "Gates", "Rejected",
    ]
    skill = skill_text()
    for name in ("Gates", "Rejected"):
        assert f"`{name}`" in skill
