import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sync_dev_projects import Row, Scan, VaultProject, plan_sync, scan_vault

# Front matter copied from the real $BRAIN_PATH/projects/ai-dotfiles.md (2026-11-22).
AI_DOTFILES = """---
title: ai-dotfiles
created: 2026-04-02
updated: 2026-11-10
tags: [project, claude-code, cursor, vibe, harness, config, skills, marketplace, local-ci]
caps: "[[developer]]"
status: active
path: "~/ai-dotfiles"
repo: https://github.com/ldom1/ai-dotfiles
---

# ai-dotfiles

> Outer harness for AI coding agents: one repo holds the rules, hooks, skills and vault-backed memory of Claude Code, Cursor and Vibe.

## Idea
Text.
"""
SUMMARY = (
    "Outer harness for AI coding agents: one repo holds the rules, hooks, skills and "
    "vault-backed memory of Claude Code, Cursor and Vibe."
)


def note(dir_: Path, slug: str, text: str) -> None:
    (dir_ / f"{slug}.md").write_text(text, encoding="utf-8")


def fm(title: str, status: str = "active", body: str = "") -> str:
    return f"---\ntitle: {title}\nstatus: {status}\n---\n\n# {title}\n\n{body}"


def test_scan_reads_slug_title_status_and_summary(tmp_path: Path) -> None:
    note(tmp_path, "ai-dotfiles", AI_DOTFILES)
    note(tmp_path, "politics", fm("Politics", status="paused"))
    scan = scan_vault(tmp_path)
    assert scan.projects["ai-dotfiles"] == VaultProject("ai-dotfiles", "ai-dotfiles", SUMMARY, True)
    assert scan.projects["politics"].active is False
    assert scan.complete and scan.malformed == []


def test_summary_falls_back_to_first_paragraph_then_empty(tmp_path: Path) -> None:
    note(tmp_path, "a", fm("A", body="First paragraph " + "x" * 300 + "\n\nSecond.\n"))
    note(tmp_path, "b", fm("B"))
    scan = scan_vault(tmp_path)
    assert scan.projects["a"].summary.startswith("First paragraph ")
    assert len(scan.projects["a"].summary) == 200
    assert scan.projects["b"].summary == ""


def test_multiline_quote_is_joined(tmp_path: Path) -> None:
    note(tmp_path, "q", fm("Q", body="> line one\n> line two\n\nRest.\n"))
    assert scan_vault(tmp_path).projects["q"].summary == "line one line two"


def test_malformed_note_is_listed_and_skipped(tmp_path: Path) -> None:
    note(tmp_path, "nofm", "# No front matter\n")
    note(tmp_path, "datetitle", "---\ntitle: 2026-01-01\nstatus: active\n---\n")
    note(tmp_path, "badyaml", "---\ntitle: [unclosed\n---\n")
    note(tmp_path, "ok", fm("Ok"))
    scan = scan_vault(tmp_path)
    assert sorted(scan.malformed) == ["badyaml", "datetitle", "nofm"]
    assert list(scan.projects) == ["ok"]
    assert scan.complete


def test_non_md_and_template_files_are_ignored(tmp_path: Path) -> None:
    note(tmp_path, "ok", fm("Ok"))
    (tmp_path / "_template.html").write_text("x")
    (tmp_path / "ok.html").write_text("x")
    (tmp_path / "sub").mkdir()
    note(tmp_path / "sub", "inner", fm("Inner"))
    assert list(scan_vault(tmp_path).projects) == ["ok"]


def test_unreadable_file_makes_the_scan_incomplete(tmp_path: Path) -> None:
    note(tmp_path, "ok", fm("Ok"))
    (tmp_path / "broken.md").symlink_to(tmp_path / "missing.md")
    assert scan_vault(tmp_path).complete is False


P_A = VaultProject("a", "A", "sa", True)
P_B = VaultProject("b", "B", "sb", True)


def scan(*projects: VaultProject, malformed: list[str] | None = None, complete: bool = True) -> Scan:
    return Scan({p.slug: p for p in projects}, malformed or [], complete)


def row(p: VaultProject, page_id: str, **change: object) -> Row:
    data = {"page_id": page_id, "slug": p.slug, "name": p.name, "summary": p.summary, "active": p.active}
    return Row(**(data | change))


def test_plan_creates_updates_and_deactivates() -> None:
    rows = {"a": row(P_A, "pa", summary="old"), "gone": Row("pg", "gone", "Gone", "", True)}
    assert plan_sync(rows, scan(P_A, P_B)) == [
        ("update", "pa", P_A),
        ("create", P_B),
        ("deactivate", "pg"),
    ]


def test_plan_never_deactivates_after_an_incomplete_scan() -> None:
    rows = {"gone": Row("pg", "gone", "Gone", "", True)}
    assert plan_sync(rows, scan(complete=False)) == []


def test_malformed_note_keeps_its_row_untouched() -> None:
    rows = {"a": row(P_A, "pa")}
    assert plan_sync(rows, scan(malformed=["a"])) == []


def test_already_inactive_absent_row_is_left_alone() -> None:
    rows = {"gone": Row("pg", "gone", "Gone", "", False)}
    assert plan_sync(rows, scan()) == []


def test_renamed_note_creates_new_and_deactivates_old() -> None:
    renamed = VaultProject("a-new", "A", "sa", True)
    assert plan_sync({"a": row(P_A, "pa")}, scan(renamed)) == [("create", renamed), ("deactivate", "pa")]


def test_plan_is_idempotent() -> None:
    rows = {"a": row(P_A, "pa"), "b": row(P_B, "pb")}
    assert plan_sync(rows, scan(P_A, P_B)) == []
