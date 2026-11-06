"""tasks-review.py: check review items at write time, print the one-line summary."""
import importlib.util
import os
from datetime import date, timedelta
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "tasks-review.py"
TODAY = date(2026, 11, 6)

spec = importlib.util.spec_from_file_location("tasks_review", SCRIPT)
tr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tr)


@pytest.fixture
def vault(tmp_path):
    (tmp_path / "projects").mkdir()
    (tmp_path / "projects" / "dombot.md").write_text("# dombot\n")
    (tmp_path / "inbox" / "review").mkdir(parents=True)
    return tmp_path


def item(vault, name, **props):
    base = {"type": "geste", "project": '"[[dombot]]"', "tool": "claude", "session": "s1",
            "status": "ouvert", "created": "2026-11-05", "why_not_agent": "needs the UI"}
    base.update(props)
    lines = [f"{k}: {v}" for k, v in base.items() if v is not None]
    path = vault / "inbox" / "review" / f"{name}.md"
    path.write_text("---\n" + "\n".join(lines) + "\n---\nbody\n")
    return path


def age(path, days):
    """Set the file mtime (the script reads the answer date from it) to `days` before TODAY."""
    ts = (TODAY - timedelta(days=days) - date(1970, 1, 1)).days * 86400 + 12 * 3600
    os.utime(path, (ts, ts))


def rdir(vault):
    return str(vault / "inbox" / "review")


def fails(vault):
    return [p for i in tr.load_items(vault / "inbox" / "review") for p in tr.problems(i, vault)]


def test_valid_geste_and_arbitrage_ok(vault, capsys):
    item(vault, "a")
    item(vault, "b", type="arbitrage", why_not_agent=None, options="[A, B]")
    assert tr.main(["check", rdir(vault)]) == 0
    assert capsys.readouterr().out.strip() == "OK 2 items"


def test_geste_without_reason_fails(vault, capsys):
    item(vault, "a", why_not_agent=None)
    assert tr.main(["check", rdir(vault)]) == 1
    assert "FAIL a.md: geste needs why_not_agent" in capsys.readouterr().out


def test_obsidian_list_and_empty_property(vault, capsys):
    item(vault, "a", type="arbitrage", why_not_agent=None, options="\n  - A\n  - B")
    assert fails(vault) == []
    item(vault, "b", why_not_agent="")
    item(vault, "c", why_not_agent=None)
    item(vault, "d", why_not_agent='"  "')
    assert tr.main(["check", rdir(vault)]) == 1
    out = capsys.readouterr().out
    assert "FAIL b.md: geste needs why_not_agent" in out
    assert "FAIL c.md: geste needs why_not_agent" in out
    assert "FAIL d.md: geste needs why_not_agent" in out
    assert "a.md" not in out


def test_arbitrage_needs_two_options(vault):
    item(vault, "a", type="arbitrage", why_not_agent=None, options="\n  - A")
    assert any("arbitrage needs 2 options" in p for p in fails(vault))


def test_answered_needs_answer(vault, capsys):
    item(vault, "a", status="répondu")
    assert tr.main(["check", rdir(vault)]) == 1
    assert "FAIL a.md: répondu needs answer" in capsys.readouterr().out
    (vault / "inbox" / "review" / "a.md").unlink()
    item(vault, "b", status="répondu", answer="go")
    assert fails(vault) == []


def test_bad_enum_and_path_link(vault):
    item(vault, "a", status="done")
    msg = " ".join(fails(vault))
    for allowed in ("ouvert", "répondu", "fait", "écarté"):
        assert allowed in msg
    (vault / "inbox" / "review" / "a.md").unlink()
    item(vault, "b", project='"[[projects/dombot]]"')
    assert any("[[slug]]" in p for p in fails(vault))


def test_unknown_project_fails(vault, capsys):
    item(vault, "a", project='"[[dombt]]"')
    assert tr.main(["check", rdir(vault)]) == 1
    assert "FAIL a.md: no projects/dombt.md" in capsys.readouterr().out


def test_missing_dir_ok_zero(tmp_path, capsys):
    assert tr.main(["check", str(tmp_path / "nope")]) == 0
    assert capsys.readouterr().out.strip() == "OK 0 items"


def test_created_accepts_date_and_iso_string_rejects_other(vault):
    item(vault, "a", created="2026-11-05")
    item(vault, "b", created='"2026-11-05"')
    assert fails(vault) == []
    item(vault, "c", created="yesterday")
    assert any("created" in p for p in fails(vault))


def test_no_frontmatter_fails(vault, capsys):
    (vault / "inbox" / "review" / "x.md").write_text("no frontmatter\n")
    assert tr.main(["check", rdir(vault)]) == 1
    assert "FAIL x.md" in capsys.readouterr().out


def test_summary_line(vault):
    item(vault, "g1")
    item(vault, "g2")
    item(vault, "a1", type="arbitrage", why_not_agent=None, options="[A, B]")
    age(item(vault, "a2", type="arbitrage", why_not_agent=None, options="[A, B]", status="répondu",
             answer="A"), 2)
    line = tr.summary_line(tr.load_items(vault / "inbox" / "review"), "dombot", TODAY)
    assert line == "[review] dombot: 3 ouverts (2 gestes, 1 arbitrage), 1 répondu < 7 j → TASKS_REVIEW"
    assert len(line.encode()) <= 300


def test_summary_empty_for_unknown_project(vault):
    item(vault, "g1")
    assert tr.summary_line(tr.load_items(vault / "inbox" / "review"), "other", TODAY) == ""


def test_summary_cli_prints_nothing_for_missing_dir(tmp_path, capsys):
    assert tr.main(["summary", "--project", "dombot", str(tmp_path / "nope")]) == 0
    assert capsys.readouterr().out == ""


def test_answer_older_than_7_days_not_counted(vault):
    age(item(vault, "a", status="répondu", answer="x"), 9)
    assert tr.summary_line(tr.load_items(vault / "inbox" / "review"), "dombot", TODAY) == ""


def test_impossible_date_fails_that_file_only(vault, capsys):
    item(vault, "a", created="2026-13-45")
    item(vault, "b", why_not_agent=None)
    assert tr.main(["check", rdir(vault)]) == 1
    out = capsys.readouterr().out
    assert len([ln for ln in out.splitlines() if ln.startswith("FAIL a.md")]) == 1
    assert "FAIL b.md: geste needs why_not_agent" in out


def test_unquoted_link_says_quote_it(vault):
    item(vault, "a", project="[[dombot]]")
    msgs = fails(vault)
    assert msgs == ['project must be a quoted link: "[[slug]]"']


def test_non_utf8_file_fails_that_file_only(vault, capsys):
    (vault / "inbox" / "review" / "bad.md").write_bytes(b"---\ntype: geste\n---\n\xff\xfe\n")
    item(vault, "b", why_not_agent=None)
    assert tr.main(["check", rdir(vault)]) == 1
    out = capsys.readouterr().out
    assert "FAIL bad.md: not UTF-8" in out
    assert "FAIL b.md: geste needs why_not_agent" in out


@pytest.mark.parametrize("argv", [["check"], ["summary", "--project", "dombot"]])
def test_no_dir_and_no_brain_path_exits_2(monkeypatch, capsys, argv):
    monkeypatch.delenv("BRAIN_PATH", raising=False)
    assert tr.main(argv) == 2
    cap = capsys.readouterr()
    assert cap.out == ""
    assert "BRAIN_PATH is not set and no DIR given" in cap.err
