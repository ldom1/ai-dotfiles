"""pattern-drift.py check: rule ids of the vault pattern notes."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "pattern-drift.py"
spec = importlib.util.spec_from_file_location("pattern_drift", SCRIPT)
pd = importlib.util.module_from_spec(spec)
spec.loader.exec_module(pd)

RULES_DOC = "Letters in pattern notes: `p` python-patterns, `m` storage-patterns, `g` git-patterns.\n"


def setup(tmp_path: Path, notes: dict[str, str]) -> tuple[Path, Path]:
    tmp_path.mkdir(parents=True, exist_ok=True)
    vault = tmp_path / "vault"
    folder = vault / "resources/knowledge/patterns"
    folder.mkdir(parents=True)
    for name, text in notes.items():
        (folder / name).write_text(text, encoding="utf-8")
    rules = tmp_path / "pitfall-rules.md"
    rules.write_text(RULES_DOC, encoding="utf-8")
    return vault, rules


def note(body: str) -> str:
    return f"---\ntitle: T\n---\n\n# T\n\n## Rules\n{body}\n## Related\n- [[x]]\n"


def run(tmp_path: Path, notes: dict[str, str]) -> list[str]:
    vault, rules = setup(tmp_path, notes)
    return pd.check(vault, rules)


def test_rule_ids_counted(tmp_path):
    vault, rules = setup(tmp_path, {"python-patterns.md": note("- a ^p1\n- b ^p2\n")})
    assert pd.check(vault, rules) == []
    assert pd.main(["check", "--vault", str(vault), "--rules", str(rules)]) == 0


def test_cli_prints_ok(tmp_path, capsys):
    vault, rules = setup(tmp_path, {"python-patterns.md": note("- a ^p1\n- b ^p2\n")})
    assert pd.main(["check", "--vault", str(vault), "--rules", str(rules)]) == 0
    assert capsys.readouterr().out.strip() == "OK 2 rules"


def test_missing_id_fails(tmp_path):
    fails = run(tmp_path, {"python-patterns.md": note("- a ^p1\n- no id\n")})
    assert fails == ["FAIL python-patterns.md: rule without id at line 9"]


def test_fenced_bullets_ignored(tmp_path):
    body = "- a ^p1\n```\n- foo\n```\n"
    assert run(tmp_path, {"python-patterns.md": note(body)}) == []


def test_sub_bullets_belong_to_parent(tmp_path):
    assert run(tmp_path, {"python-patterns.md": note("- a ^p1\n  - detail\n")}) == []


def test_subsection_rules_counted(tmp_path):
    fails = run(tmp_path, {"python-patterns.md": note("### Sub\n- a ^p1\n- b\n")})
    assert len(fails) == 1 and "rule without id" in fails[0]


def test_link_is_not_an_id(tmp_path):
    rules, fails = pd.parse_rules(setup(tmp_path, {"storage-patterns.md": note("- see [[pitfalls#^v5]] ^m1\n")})[0]
                                  / "resources/knowledge/patterns/storage-patterns.md")
    assert fails == [] and [r.id for r in rules] == ["m1"]


def test_link_alone_is_not_an_id(tmp_path):
    fails = run(tmp_path, {"storage-patterns.md": note("- see [[pitfalls#^m1]]\n")})
    assert any("rule without id" in f for f in fails)


def test_duplicate_id_across_vault_fails(tmp_path):
    fails = run(tmp_path, {"python-patterns.md": note("- a ^p1\n"), "python-patterns-superseded.md": note("- a ^p1\n")})
    assert any(f.startswith("FAIL") and "duplicate id p1" in f for f in fails)


def test_undeclared_letter_fails(tmp_path):
    fails = run(tmp_path, {"zed-patterns.md": note("- a ^z1\n")})
    assert fails == ["FAIL zed-patterns.md: letter z not in pitfall-rules.md"]


def test_supersede_target_must_be_active(tmp_path):
    ok = run(tmp_path / "a", {"python-patterns.md": note("- b ^p2\n"),
                        "python-patterns-superseded.md": note("- a ^p1 → ^p2\n")})
    assert ok == []
    absent = run(tmp_path / "b", {"python-patterns.md": note("- b ^p2\n"),
                            "python-patterns-superseded.md": note("- a ^p1 → ^p9\n")})
    assert any("^p9" in f for f in absent)
    replaced = run(tmp_path / "c", {"python-patterns.md": note("- b ^p2\n"),
                              "python-patterns-superseded.md": note("- a ^p1 → ^p2\n- b ^p2 → ^p3\n")})
    assert any("duplicate id p2" in f or "^p3" in f for f in replaced)


def test_note_without_rules_section_fails(tmp_path):
    fails = run(tmp_path, {"python-patterns.md": "# T\n\nnothing\n"})
    assert fails == ["FAIL python-patterns.md: no ## Rules"]


def test_unclosed_fence_is_reported(tmp_path):
    fails = run(tmp_path, {"python-patterns.md": note("- a ^p1\n```\n- foo\n")})
    assert any("unclosed code fence at line 9" in f for f in fails)
    assert not any("rule without id" in f for f in fails)
