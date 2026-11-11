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


def test_capture_reads_ticked_arbitrages():
    skill = skill_text()
    assert "the recommended one first" in skill  # a ticked arbitrage with no answer accepts the first option
    assert "`done: true`" in skill  # read-back covers the checkbox, not only `répondu`
    assert "never ticks `done`" in skill  # the checkbox is the human's


def test_pitfall_rules_have_one_home():
    rules = REPO / "skills/brain-audit/reference/pitfall-rules.md"
    assert rules.is_file()
    assert "Letters in `pitfalls.md`" in rules.read_text(encoding="utf-8")
    compile_text = (REPO / "skills/brain-audit/skills/compile/SKILL.md").read_text(encoding="utf-8")
    for text in (skill_text(), compile_text):
        assert "reference/pitfall-rules.md" in text
        assert "Letters in `pitfalls.md`" not in text  # the id-letter sentence lives only in the reference
        assert "check-pitfalls-budget.sh" not in text


def test_capture_does_not_read_brain_env():
    assert "brain.env" not in skill_text()  # SessionStart exports BRAIN_PATH


def test_connect_has_no_commit_step():
    connect = (REPO / "skills/brain-audit/skills/connect/SKILL.md").read_text(encoding="utf-8")
    assert "git commit" not in connect
    assert "-patterns.md" not in connect
    assert "resources/knowledge/*-patterns" not in connect


def test_compile_writes_patterns_in_one_format():
    compile_text = (REPO / "skills/brain-audit/skills/compile/SKILL.md").read_text(encoding="utf-8")
    assert "## Rules" in compile_text
    assert "Observed in" in compile_text
    assert "never paths" in compile_text
