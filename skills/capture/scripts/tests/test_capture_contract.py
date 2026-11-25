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


def test_compile_keeps_paths_and_never_reformats():
    compile_text = (REPO / "skills/brain-audit/skills/compile/SKILL.md").read_text(encoding="utf-8")
    assert "paths:" in compile_text
    assert "Never reformat" in compile_text


def test_capture_and_localbrain_share_destination_rule():
    root = Path(__file__).parents[4]
    capture = (root / "skills/capture/SKILL.md").read_text(encoding="utf-8")
    localbrain = (root / "LocalBrain.md").read_text(encoding="utf-8")
    for text in (capture, localbrain):
        assert "resources/knowledge/<domain>/" in text
        for dest in ("pitfalls.md", "<repo>/.claude/memory/", "Live now"):
            assert dest in text, dest


def test_domain_project_keeps_only_state_in_repo():
    capture = (REPO / "skills/capture/SKILL.md").read_text(encoding="utf-8")
    localbrain = (REPO / "LocalBrain.md").read_text(encoding="utf-8")
    for text in (capture, localbrain):
        assert "one note per app" in text
        assert "only state and decisions" in text


def test_capture_has_supersede_verdict():
    skill = skill_text()
    for needle in ("**Supersede", "-superseded.md", "detect:", "pattern-drift.py scan"):
        assert needle in skill


def test_capture_keeps_drift_markers():
    step3 = skill_text().split("## 3.")[1].split("## 4.")[0]
    assert "<!-- pattern-drift:" in step3
    assert "never remove" in step3


def test_brain_audit_runs_drift():
    text = (REPO / "skills/brain-audit/SKILL.md").read_text(encoding="utf-8")
    assert "`compile` → `drift`" in text
    assert "pattern-drift.py check" in text
    assert "remplace ^" in text


def test_digest_lists_migrations():
    text = (REPO / "skills/brain-audit/skills/digest/SKILL.md").read_text(encoding="utf-8")
    for needle in ("opened", "closed", "incomplete", "à vérifier"):
        assert needle in text


def _vault() -> Path:
    import os

    import pytest

    brain = os.environ.get("BRAIN_PATH")
    if not brain:
        env = REPO / "config/brain.env"
        if env.is_file():
            m = re.search(r"^(?:export\s+)?BRAIN_PATH=[\"']?([^\"'\n]+)", env.read_text(), re.M)
            brain = m.group(1).replace("$HOME", str(Path.home())) if m else None
    if not brain or not (Path(brain) / "resources/knowledge/patterns").is_dir():
        pytest.skip("no vault: BRAIN_PATH unset or without patterns")
    return Path(brain)


def _parse_rules():
    import importlib.util

    spec = importlib.util.spec_from_file_location("pattern_drift", REPO / "scripts/pattern-drift.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.parse_rules


def test_agents_python_ids_are_active():
    patterns = _vault() / "resources/knowledge/patterns"
    parse_rules = _parse_rules()
    active = {r.id for r in parse_rules(patterns / "python-patterns.md")[0]}
    sup = patterns / "python-patterns-superseded.md"
    superseded = {r.id for r in parse_rules(sup)[0]} if sup.exists() else set()
    text = (REPO / "AGENTS.md").read_text(encoding="utf-8")
    section = re.search(r"^## Python\n(.*?)(?=^## )", text, re.M | re.S).group(1)
    bullets = [b for b in section.splitlines() if b.startswith("- ")]
    assert bullets
    for bullet in bullets:
        ids = re.findall(r"\(\^(p\d+)\)\s*$", bullet)
        assert ids, f"no (^pN) at end of: {bullet[:60]}"
        assert ids[0] in active, f"{ids[0]} not in python-patterns.md"
        assert ids[0] not in superseded, f"{ids[0]} is superseded"
