"""spec-tldr-check.py denies a Write of a vault spec without a `## TL;DR` before `## Context`."""
import json
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / "spec-tldr-check.py"
SPEC = "/vault/inbox/daily/specs/proj/2026-11-25-x-design.md"


def decision(file_path: str, content: str) -> str:
    payload = {"tool_name": "Write", "tool_input": {"file_path": file_path, "content": content}}
    out = subprocess.run([sys.executable, str(HOOK)], input=json.dumps(payload),
                         capture_output=True, text=True, check=True).stdout
    return json.loads(out)["hookSpecificOutput"]["permissionDecision"] if out.strip() else "allow"


def test_spec_without_tldr_is_denied():
    assert decision(SPEC, "---\ntitle: x\n---\n# X\n\n## Context\nwhy\n") == "deny"


def test_spec_with_tldr_first_is_allowed():
    assert decision(SPEC, "---\ntitle: x\n---\n# X\n\n## TL;DR\n- a\n\n## Context\nwhy\n") == "allow"


def test_tldr_after_context_is_denied():
    assert decision(SPEC, "# X\n\n## Context\nwhy\n\n## TL;DR\n- a\n") == "deny"


def test_tldr_inside_code_fence_does_not_count():
    assert decision(SPEC, "# X\n\n```\n## TL;DR\n```\n\n## Context\n") == "deny"


def test_other_files_are_ignored():
    assert decision("/vault/inbox/daily/plans/proj/2026-11-25-x-plan.md", "# X\n## Context\n") == "allow"
    assert decision("/repo/README.md", "# X\n## Context\n") == "allow"


def test_bad_input_fails_open():
    out = subprocess.run([sys.executable, str(HOOK)], input="not json", capture_output=True, text=True)
    assert out.returncode == 0 and out.stdout.strip() == ""
