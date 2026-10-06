"""Agent files in .claude/agents/ carry valid frontmatter, and the template sets the default delegation model."""
import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
AGENTS = REPO / ".claude" / "agents"
TEMPLATE = REPO / ".claude" / "settings.json.tpl"
MODELS = {"haiku", "sonnet", "opus", "fable", "inherit"}


def frontmatter(path):
    _, head, _body = path.read_text().split("---", 2)
    return dict(line.split(":", 1) for line in head.strip().splitlines())


@pytest.mark.parametrize("name,model", [("lookup", "haiku"), ("reviewer", "sonnet")])
def test_agent_frontmatter(name, model):
    meta = frontmatter(AGENTS / f"{name}.md")
    assert {"name", "description", "model", "tools"} <= meta.keys()
    assert meta["name"].strip() == name
    assert meta["model"].strip() in MODELS
    assert meta["model"].strip() == model
    assert meta["description"].strip()
    tools = {t.strip() for t in meta["tools"].split(",")}
    assert tools == {"Read", "Grep", "Glob", "Bash"}


def test_template_sets_subagent_model():
    env = json.loads(TEMPLATE.read_text())["env"]
    assert env["CLAUDE_CODE_SUBAGENT_MODEL"] in MODELS
