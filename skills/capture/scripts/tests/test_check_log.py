import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from check_log import check, main

GOOD = """## Fix the merge guard

**Goal:** stop false positives.
**Changes:**
- `.claude/hooks/merge-guard.sh`: pass data-only commands (#50). See [[git-patterns#^g7]].
**Commands/tests:** `pytest .claude/hooks/tests`
**Follow-ups:** none
**Pitfall hit:** [[pitfalls#^v5]]
"""


def write(tmp_path: Path, text: str, name: str = "2026-10-15-merge-guard.md") -> Path:
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def make_vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "resources/knowledge/patterns").mkdir(parents=True)
    (vault / "resources/knowledge/patterns/git-patterns.md").write_text("x")
    (vault / "pitfalls.md").write_text("x")
    (vault / ".obsidian").mkdir()
    (vault / ".obsidian/hidden-note.md").write_text("x")
    return vault


def test_good_log_passes(tmp_path):
    assert check(write(tmp_path, GOOD), make_vault(tmp_path)) == []


def test_lookup_only_passes(tmp_path):
    assert check(write(tmp_path, "Lookup/Q&A only. No files modified.\n")) == []


def test_bad_filename(tmp_path):
    fails = check(write(tmp_path, GOOD, name="notes.md"))
    assert any(f.startswith("filename:") for f in fails)


def test_no_topic_block(tmp_path):
    fails = check(write(tmp_path, "**Goal:** x\n"))
    assert any(f.startswith("structure:") for f in fails)


def test_missing_section(tmp_path):
    fails = check(write(tmp_path, GOOD.replace("**Follow-ups:** none\n", "")))
    assert "section: 'Follow-ups' appears 0 times in 'Fix the merge guard'" in fails


def test_extra_section(tmp_path):
    fails = check(write(tmp_path, GOOD + "**Decisions:** keep it\n"))
    assert "extra section: 'Decisions' in 'Fix the merge guard'" in fails


def test_wrong_order(tmp_path):
    text = GOOD.replace("**Goal:** stop false positives.\n", "") + "**Goal:** late\n"
    fails = check(write(tmp_path, text))
    assert any(f.startswith("order:") for f in fails)


def test_second_block_is_checked(tmp_path):
    text = GOOD + "\n## Second topic\n\n**Goal:** x\n**Follow-ups:** none\n"
    fails = check(write(tmp_path, text))
    assert "section: 'Changes' appears 0 times in 'Second topic'" in fails


def test_real_variants_pass(tmp_path):
    text = GOOD + (
        "\n## Same thread, later\n\n**Changes (notion-pilot `develop`):** x\n"
        "**Follow-ups:** none\n**Pitfall hit:** [[pitfalls#^s1]]\n"
    )
    assert check(write(tmp_path, text, name="2026-10-14-guide-v1.4.0.md")) == []


def test_duplicate_section(tmp_path):
    fails = check(write(tmp_path, GOOD + "**Follow-ups:** more\n"))
    assert "section: 'Follow-ups' appears 2 times in 'Fix the merge guard'" in fails


def test_folder_link(tmp_path):
    fails = check(write(tmp_path, GOOD + "See [[notion-pilot/CONTEXT]] and [[pitfalls.md]].\n"))
    assert any("folder link: [[notion-pilot/CONTEXT]]" in f for f in fails)
    assert any("folder link: [[pitfalls.md]]" in f for f in fails)


def test_broken_link_only_with_vault(tmp_path):
    path = write(tmp_path, GOOD + "See [[no-such-note|alias]] and [[hidden-note]].\n")
    assert check(path) == []
    fails = check(path, make_vault(tmp_path))
    assert any("broken link: [[no-such-note]]" in f for f in fails)
    assert any("broken link: [[hidden-note]]" in f for f in fails)


def test_code_is_ignored(tmp_path):
    text = GOOD + "Run `[[a/b]]` and `**Fake:**`.\n\n```\n**Decisions:** x\n[[c/d]]\n```\n"
    assert check(write(tmp_path, text)) == []


def test_main_exit_codes(tmp_path, capsys):
    assert main([str(write(tmp_path, GOOD))]) == 0
    assert capsys.readouterr().out.strip() == "OK"
    bad = write(tmp_path, GOOD + "**Decisions:** x\n", name="2026-10-15-bad.md")
    assert main([str(bad)]) == 1
    assert capsys.readouterr().out.startswith("FAIL extra section:")
    assert main([str(tmp_path / "missing.md")]) == 2


HARNESS = """## Add a merge guard

**Goal:** stop bad merges.
**Changes:** hook added.
**Follow-ups:** none
**Harness changes:**
- `.claude/hooks/merge-guard.sh` · block data-only merges · expected: fewer refusals · check: merge-guard refusals
- `skills/capture/SKILL.md` · add metrics label · expected: Metrics line in logs · check: grep '**Metrics:**' inbox/daily
**Metrics:** 1a2b3c4d · 42 min · 12 tool calls
"""


def test_harness_changes_and_metrics_labels_ok(tmp_path):
    assert check(write(tmp_path, HARNESS)) == []


def test_labels_order(tmp_path):
    text = "## t\n\n**Goal:** g\n**Metrics:** 1a2b3c4d\n**Changes:** c\n**Follow-ups:** none\n"
    fails = check(write(tmp_path, text))
    assert any(f.startswith("order:") for f in fails)


def test_lookup_only_still_ok(tmp_path):
    assert check(write(tmp_path, "Lookup/Q&A only. No files modified.\n")) == []


def test_bad_harness_row_fails(tmp_path):
    text = HARNESS.replace("\n**Metrics:** 1a", "\n- component · change · check: c\n**Metrics:** 1a")
    fails = check(write(tmp_path, text))
    assert fails == ["harness row: Add a merge guard: line 9"]


def test_harness_row_with_dot_and_verdict_ok(tmp_path):
    text = HARNESS.replace("\n**Metrics:** 1a", "\n- a · b · c · expected: e · f · check: c · verdict: helped (1 vs 2, 2026-01-01)\n**Metrics:** 1a")
    assert check(write(tmp_path, text)) == []
