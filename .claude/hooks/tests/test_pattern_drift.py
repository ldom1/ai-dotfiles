"""pattern-drift.py check: rule ids of the vault pattern notes."""
import importlib.util
import shutil
from pathlib import Path

import pytest

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
    # ^p3 exists only in a -superseded note: it is not an active target
    replaced = run(tmp_path / "c", {"python-patterns.md": note("- b ^p2\n"),
                              "python-patterns-superseded.md": note("- a ^p1 → ^p3\n- c ^p3 → ^p2\n")})
    assert replaced == ["FAIL python-patterns-superseded.md: ^p1 supersede target ^p3 is not an active rule at line 8"]


def test_note_without_rules_section_fails(tmp_path):
    fails = run(tmp_path, {"python-patterns.md": "# T\n\nnothing\n"})
    assert fails == ["FAIL python-patterns.md: no ## Rules"]


def test_unclosed_fence_is_reported(tmp_path):
    fails = run(tmp_path, {"python-patterns.md": note("- a ^p1\n```\n- foo\n")})
    assert any("unclosed code fence at line 9" in f for f in fails)
    assert not any("rule without id" in f for f in fails)


def test_superseded_note_needs_no_rules_section(tmp_path):
    body = "# T\n\n## Superseded\n- ~~a~~ → ^p2 (2026-11-25, why) ^p1\n"
    fails = run(tmp_path, {"python-patterns.md": note("- b ^p2\n"), "python-patterns-superseded.md": body})
    assert fails == []
    assert run(tmp_path / "n", {"python-patterns.md": "# T\n\n## Superseded\n- a ^p1\n"}) == [
        "FAIL python-patterns.md: no ## Rules"]


# ---- detect evaluation ----

FIXTURES = Path(__file__).parent / "fixtures" / "pattern_drift"
OLD = (FIXTURES / "real/old_ad_generator_config.py").read_text()
OLD_API = (FIXTURES / "real/old_api_server_config.py").read_text()
NEW = (FIXTURES / "real/basesettings_prosper_config.py").read_text()
NEW_DASH = (FIXTURES / "real/basesettings_dashboard_config.py").read_text()
needs_ast_grep = pytest.mark.skipif(shutil.which("ast-grep") is None, reason="ast-grep not installed")


def repo_of(tmp_path: Path, files: dict[str, str]) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir(parents=True, exist_ok=True)
    for name, text in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_text(text, encoding="utf-8")
    return repo


def fixture_detect() -> "pd.Detect":
    found, fails = pd.parse_superseded(FIXTURES / "python-patterns-superseded.md")
    assert fails == [] and len(found) == 1
    return found[0].detect


def toml_detect(*conds) -> "pd.Detect":
    return pd.Detect(lang="toml", files=["pyproject.toml"], all=[pd.TomlCond(**c) for c in conds])


UV_BUILD = {"key": "build-system.build-backend", "equals": "uv_build"}


def test_parse_superseded(tmp_path):
    found, fails = pd.parse_superseded(FIXTURES / "python-patterns-superseded.md")
    assert fails == []
    item = found[0]
    assert (item.id, item.by, item.date) == ("p4", "p31", "2026-11-25")
    assert item.reason.startswith("pydantic-settings: typed")
    assert item.detect.lang == "python" and item.detect.files == ["**/config.py"]
    assert item.detect.absent_in_repo == "class $C(BaseSettings): $$$B"


@needs_ast_grep
def test_old_config_matches(tmp_path):
    for name, text in (("ad", OLD), ("api", OLD_API)):
        out = pd.evaluate(repo_of(tmp_path / name, {"pkg/config.py": text}), fixture_detect())
        assert out.state == "match" and out.files == ["pkg/config.py"]


@needs_ast_grep
def test_basesettings_config_absent(tmp_path):
    for name, text in (("prosper", NEW), ("dash", NEW_DASH)):
        out = pd.evaluate(repo_of(tmp_path / name, {"app/config.py": text}), fixture_detect())
        assert out.state == "absent"


@needs_ast_grep
def test_migrated_config_with_logger_absent(tmp_path):
    config = 'import logging\nfrom typing import TypeVar\n\nLOGGER = logging.getLogger(__name__)\nT = TypeVar("T")\n'
    settings = "from pydantic_settings import BaseSettings\n\n\nclass Settings(BaseSettings):\n    x: int = 1\n"
    detect = fixture_detect()
    assert pd.evaluate(repo_of(tmp_path, {"pkg/config.py": config, "pkg/settings.py": settings}), detect).state == "absent"
    # the guard is what makes it absent when the old form is still there
    mixed = config + 'LIMIT = 3\n'
    assert pd.evaluate(repo_of(tmp_path / "m", {"pkg/config.py": mixed}), detect).state == "match"
    assert pd.evaluate(repo_of(tmp_path / "g", {"pkg/config.py": mixed, "pkg/settings.py": settings}), detect).state == "absent"


@needs_ast_grep
def test_constant_in_class_absent(tmp_path):
    text = "class A:\n    LIMIT = 3\n\n\ndef f():\n    OTHER = 4\n"
    assert pd.evaluate(repo_of(tmp_path, {"config.py": text}), fixture_detect()).state == "absent"


@needs_ast_grep
def test_constant_in_comment_absent(tmp_path):
    text = '# LIMIT = 3\n"""\nLIMIT = 3\n"""\n'
    assert pd.evaluate(repo_of(tmp_path, {"config.py": text}), fixture_detect()).state == "absent"


def test_uv_build_matches(tmp_path):
    repo = repo_of(tmp_path, {"pyproject.toml": '[build-system]\nbuild-backend = "uv_build"\n'})
    out = pd.evaluate(repo, toml_detect(UV_BUILD))
    assert out.state == "match" and out.files == ["pyproject.toml"]


def test_hatchling_absent(tmp_path):
    repo = repo_of(tmp_path, {"pyproject.toml": '[build-system]\nbuild-backend = "hatchling.build"\n'})
    assert pd.evaluate(repo, toml_detect(UV_BUILD)).state == "absent"


def test_toml_absent_key(tmp_path):
    repo = repo_of(tmp_path, {"pyproject.toml": '[project]\nname = "x"\n'})
    assert pd.evaluate(repo, toml_detect({"key": "tool.uv.build-backend.module-root", "absent": True})).state == "match"


def test_bad_toml_incomplete(tmp_path):
    out = pd.evaluate(repo_of(tmp_path, {"pyproject.toml": "[build-system\n"}), toml_detect(UV_BUILD))
    assert out.state == "incomplete" and "pyproject.toml" in out.reason


def test_same_key_other_table_absent(tmp_path):
    repo = repo_of(tmp_path, {"pyproject.toml": '[tool.foo]\nbuild-backend = "uv_build"\n'})
    assert pd.evaluate(repo, toml_detect(UV_BUILD)).state == "absent"


def test_glob_without_file_is_absent(tmp_path):
    assert pd.evaluate(repo_of(tmp_path, {"README.md": "x"}), fixture_detect()).state == "absent"
    assert pd.evaluate(repo_of(tmp_path / "t", {"README.md": "x"}), toml_detect(UV_BUILD)).state == "absent"


@needs_ast_grep
def test_ast_grep_missing_is_incomplete(tmp_path, monkeypatch):
    repo = repo_of(tmp_path, {"config.py": OLD})
    empty = tmp_path / "empty"
    empty.mkdir()
    monkeypatch.setenv("PATH", str(empty))
    out = pd.evaluate(repo, fixture_detect())
    assert out.state == "incomplete" and "ast-grep" in out.reason


def test_invalid_detect_is_incomplete(tmp_path):
    bad = ("# T\n\n## Superseded\n- ~~a~~ → ^p2 (2026-11-25, why) ^p1\n  detect:\n    lang: ruby\n    files: [x]\n"
           "- ~~b~~ → ^p2 (2026-11-25, why) ^p3\n  detect:\n    lang: [unclosed\n")
    vault, rules = setup(tmp_path, {"python-patterns.md": note("- b ^p2\n"), "python-patterns-superseded.md": bad})
    found, fails = pd.parse_superseded(vault / "resources/knowledge/patterns/python-patterns-superseded.md")
    assert len(fails) == 2 and all(f.startswith("FAIL") and "invalid detect" in f for f in fails)
    assert [(s.id, s.detect) for s in found] == [("p1", None), ("p3", None)]
    assert pd.check(vault, rules) == fails
    # a scan treats a rule with a broken detect as incomplete (never a crash): detect is None
    assert all(s.detect is None for s in found)


@needs_ast_grep
def test_venv_ignored(tmp_path):
    repo = repo_of(tmp_path, {".venv/lib/config.py": OLD, "node_modules/x/config.py": OLD, ".git/config.py": OLD,
                              "app/config.py": NEW})
    assert pd.evaluate(repo, fixture_detect()).state == "absent"
    repo = repo_of(tmp_path / "b", {".venv/lib/config.py": OLD, "app/config.py": OLD})
    assert pd.evaluate(repo, fixture_detect()).files == ["app/config.py"]
