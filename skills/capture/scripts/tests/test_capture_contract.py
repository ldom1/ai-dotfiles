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


def test_capture_routes_human_items_to_review():
    skill = skill_text()
    assert "inbox/review/" in skill
    assert "why_not_agent" in skill
    assert "_templates/review-item.md" in skill
    assert (
        'uv run --script ~/ai-dotfiles/scripts/tasks-review.py check "${BRAIN_PATH:?}/inbox/review"'
        in skill
    )


def test_capture_review_agent_side_rules():
    skill = skill_text()
    assert '"${BRAIN_PATH:?}/inbox/review"' in skill  # unset BRAIN_PATH fails loudly, not `OK 0 items`
    assert "`status: fait`" in skill and "`écarté`" in skill
    assert "status: répondu" not in skill  # only the human sets répondu
    assert "only the human sets `répondu`" in skill
    assert "[review] … répondu" in skill  # read-back of the human's answers
    assert "`session:` with `$CLAUDE_SESSION_ID`" in skill
