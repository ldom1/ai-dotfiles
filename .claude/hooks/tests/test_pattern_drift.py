"""pattern-drift.py check: rule ids of the vault pattern notes."""
import importlib.util
import os
import shutil
import subprocess
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
    if not (repo / ".git").exists():
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
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
    (empty / "git").symlink_to(shutil.which("git"))  # git stays, ast-grep goes
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
    assert all(s.detect_error for s in found)
    ok, _ = pd.parse_superseded(FIXTURES / "python-patterns-superseded.md")
    assert ok[0].detect_error is None


@needs_ast_grep
def test_venv_ignored(tmp_path):
    repo = repo_of(tmp_path, {".venv/lib/config.py": OLD, "node_modules/x/config.py": OLD,
                              "app/config.py": NEW})
    assert pd.evaluate(repo, fixture_detect()).state == "absent"
    repo = repo_of(tmp_path / "b", {".venv/lib/config.py": OLD, "app/config.py": OLD})
    assert pd.evaluate(repo, fixture_detect()).files == ["app/config.py"]


def test_toml_detect_without_conditions_rejected(tmp_path):
    body = ("# T\n\n## Superseded\n- ~~a~~ → ^p2 (2026-11-25, why) ^p1\n  detect:\n    lang: toml\n"
            "    files: [pyproject.toml]\n")
    vault, _ = setup(tmp_path, {"python-patterns-superseded.md": body})
    found, fails = pd.parse_superseded(vault / "resources/knowledge/patterns/python-patterns-superseded.md")
    assert len(fails) == 1 and "at least one condition" in fails[0]
    assert found[0].detect is None and found[0].detect_error


def test_toml_without_conditions_is_incomplete(tmp_path):
    repo = repo_of(tmp_path, {"pyproject.toml": "[project]\n"})
    bare = pd.Detect.model_construct(lang="toml", files=["pyproject.toml"], all=None)
    assert pd.evaluate(repo, bare).state == "incomplete"
    assert pd.evaluate(repo, pd.Detect.model_construct(lang="toml", files=["pyproject.toml"], all=[])).state == "incomplete"


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads anything")
def test_unreadable_directory_is_incomplete(tmp_path):
    # tracked file in a directory that becomes unreadable: a candidate that matches the glob cannot be read
    repo = repo_of(tmp_path, {"locked/config.py": OLD})
    subprocess.run(["git", "add", "locked/config.py"], cwd=repo, check=True)
    (repo / "locked").chmod(0)
    try:
        assert pd.evaluate(repo, fixture_detect()).state == "incomplete"
    finally:
        (repo / "locked").chmod(0o755)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads anything")
def test_untracked_unreadable_directory_is_incomplete(tmp_path):
    # untracked, not ignored: git cannot list it, so detection cannot be trusted
    repo = repo_of(tmp_path, {"locked/config.py": OLD, "pyproject.toml": '[tool.foo]\nx = 1\n'})
    (repo / "locked").chmod(0)
    try:
        assert pd.evaluate(repo, toml_detect(UV_BUILD)).state == "incomplete"
    finally:
        (repo / "locked").chmod(0o755)


@pytest.mark.skipif(os.geteuid() == 0, reason="root reads anything")
def test_ignored_unreadable_dir_is_skipped(tmp_path):
    repo = repo_of(tmp_path, {"data/postgres/x": "1", ".gitignore": "data/\n",
                              "pyproject.toml": '[build-system]\nbuild-backend = "uv_build"\n'})
    (repo / "data/postgres").chmod(0)
    (repo / "data").chmod(0)
    try:
        assert pd.evaluate(repo, toml_detect(UV_BUILD)).state == "match"
        assert pd.evaluate(repo, fixture_detect()).state == "absent"
    finally:
        (repo / "data").chmod(0o755)
        (repo / "data/postgres").chmod(0o755)


def test_not_a_git_repo_is_incomplete(tmp_path):
    plain = tmp_path / "plain"
    plain.mkdir()
    (plain / "pyproject.toml").write_text('[build-system]\nbuild-backend = "uv_build"\n')
    assert pd.evaluate(plain, toml_detect(UV_BUILD)).state == "incomplete"


@needs_ast_grep
@pytest.mark.skipif(os.geteuid() == 0, reason="root reads anything")
def test_unreadable_python_file_is_incomplete(tmp_path):
    repo = repo_of(tmp_path, {"config.py": OLD})
    (repo / "config.py").chmod(0)
    try:
        out = pd.evaluate(repo, fixture_detect())
    finally:
        (repo / "config.py").chmod(0o644)
    assert out.state == "incomplete" and "config.py" in out.reason


@needs_ast_grep
def test_unexpected_json_is_incomplete(tmp_path, monkeypatch):
    repo = repo_of(tmp_path, {"config.py": OLD})
    monkeypatch.setattr(pd, "_ast_grep", lambda *_: [{"nofile": 1}])
    assert pd.evaluate(repo, fixture_detect()).state == "incomplete"


# ---- scan ----

import re
import subprocess
from datetime import date, timedelta

SUMMARY = re.compile(r"^scanned \d+ repos · skipped \d+( \((dormant|no-path|not-cloned|git-error|unreadable|unwritable): \d+"
                     r"(, (dormant|no-path|not-cloned|git-error|unreadable|unwritable): \d+)*\))? · matches \d+ · opened \d+"
                     r" · closed \d+ · incomplete \d+$")
SUP = ("# T\n\n## Superseded\n- ~~old~~ → ^p31 (2026-11-25, uv_build replaces hatchling) ^p9\n"
       "  detect:\n    lang: toml\n    files: [pyproject.toml]\n    all:\n"
       "      - {key: build-system.build-backend, equals: hatchling}\n")
OLD_TOML = '[build-system]\nbuild-backend = "hatchling"\n'
NEW_TOML = '[build-system]\nbuild-backend = "uv_build"\n'
MARK = "<!-- pattern-drift:^p9 -->"


def git(repo: Path, *args: str, when: str = "") -> None:
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}
    if when:
        env["GIT_COMMITTER_DATE"] = env["GIT_AUTHOR_DATE"] = when
    subprocess.run(["git", *args], cwd=repo, env=env, check=True, capture_output=True)


def world(tmp_path: Path, status: str = "active", age: int = 1, toml: str = OLD_TOML,
          roadmap: str | bytes | None = "# R\n\n## Next\n- a\n\n## Later\n- b\n", path: bool = True):
    """Vault with one project `proj` (repo under lab/proj) and the toml superseded note."""
    vault, _ = setup(tmp_path, {"python-patterns.md": note("- n ^p31\n"), "python-patterns-superseded.md": SUP})
    lab = tmp_path / "lab"
    repo = lab / "proj"
    repo.mkdir(parents=True)
    (repo / "pyproject.toml").write_text(toml)
    git(repo, "init", "-q")
    git(repo, "add", ".")
    when = (date.today() - timedelta(days=age)).isoformat() + "T12:00:00"
    git(repo, "commit", "-qm", "c", when=when)
    if roadmap is not None:
        (repo / ".claude/memory").mkdir(parents=True)
        data = roadmap if isinstance(roadmap, bytes) else roadmap.encode()
        (repo / ".claude/memory/ROADMAP.md").write_bytes(data)
    (vault / "projects").mkdir()
    front = f"---\nstatus: {status}\n" + (f"path: {repo}\n" if path else "") + "---\n"
    (vault / "projects/proj.md").write_text(front)
    return vault, lab, repo


def road(repo: Path) -> bytes:
    return (repo / ".claude/memory/ROADMAP.md").read_bytes()


def run_scan(vault, lab, capsys=None):
    return pd.scan(vault, lab, 60)


def test_active_by_commit(tmp_path):
    vault, lab, repo = world(tmp_path)
    repos, skipped = pd.active_repos(vault, lab, 60)
    assert [r.slug for r in repos] == ["proj"] and not skipped


def test_active_by_session_log(tmp_path):
    vault, lab, repo = world(tmp_path, age=200)
    assert pd.active_repos(vault, lab, 60)[0] == []
    logs = vault / "inbox/daily/implementation/proj"
    logs.mkdir(parents=True)
    (logs / f"{date.today() - timedelta(days=3)}-x.md").write_text("x")
    assert [r.slug for r in pd.active_repos(vault, lab, 60)[0]] == ["proj"]


def test_dormant_skipped(tmp_path):
    vault, lab, repo = world(tmp_path, age=200)
    repos, skipped = pd.active_repos(vault, lab, 60)
    assert repos == [] and skipped == {"dormant": 1}


def test_not_cloned_skipped(tmp_path):
    vault, lab, repo = world(tmp_path)
    shutil.rmtree(repo)
    assert pd.active_repos(vault, lab, 60)[1] == {"not-cloned": 1}


def test_no_path_skipped(tmp_path):
    vault, lab, repo = world(tmp_path, path=False)
    shutil.rmtree(repo)
    assert pd.active_repos(vault, lab, 60)[1] == {"no-path": 1}


def point_note_at(vault, text):
    (vault / "projects/proj.md").write_text(f"---\nstatus: active\npath: {text}\n---\n")


def test_fallback_by_basename(tmp_path):
    vault, lab, repo = world(tmp_path)
    repo.rename(lab / "other")
    point_note_at(vault, "/gone/lab/other")
    repos, skipped = pd.active_repos(vault, lab, 60)
    assert [r.path for r in repos] == [lab / "other"] and not skipped


def test_fallback_by_slug(tmp_path):
    vault, lab, repo = world(tmp_path)
    point_note_at(vault, "/gone/lab/Proj-Other")
    repos, skipped = pd.active_repos(vault, lab, 60)
    assert [r.path for r in repos] == [repo] and not skipped


def test_warn_lines_printed(tmp_path, capsys):
    vault, lab, repo = world(tmp_path)
    shutil.rmtree(repo)
    point_note_at(vault, "/gone/lab/proj")
    (vault / "projects/bare.md").write_text("---\nstatus: active\n---\n")
    pd.scan(vault, lab, 60)
    out = capsys.readouterr().out
    assert "WARN not-cloned proj /gone/lab/proj" in out
    assert "WARN no-path bare" in out


def test_fallback_path_under_lab_root(tmp_path):
    vault, lab, repo = world(tmp_path, path=False)
    assert [r.slug for r in pd.active_repos(vault, lab, 60)[0]] == ["proj"]


def test_inactive_note_not_counted(tmp_path):
    vault, lab, repo = world(tmp_path, status="archived", age=200)
    assert pd.active_repos(vault, lab, 60) == ([], {})


def test_open_then_no_duplicate(tmp_path):
    vault, lab, repo = world(tmp_path)
    assert "opened 1" in pd.scan(vault, lab, 60)
    assert "opened 0" in pd.scan(vault, lab, 60)
    text = road(repo).decode()
    assert text.count(MARK) == 1
    assert text.index("- Migrate: ^p9 → ^p31 (uv_build replaces hatchling) in `pyproject.toml` " + MARK) \
        < text.index("## Later")
    assert text.index("- a\n") < text.index("- Migrate")


def test_closed_on_verified_absent(tmp_path):
    vault, lab, repo = world(tmp_path)
    pd.scan(vault, lab, 60)
    (repo / "pyproject.toml").write_text(NEW_TOML)
    summary = pd.scan(vault, lab, 60)
    assert "closed 1" in summary and MARK not in road(repo).decode()
    assert road(repo).decode() == "# R\n\n## Next\n- a\n\n## Later\n- b\n"


def test_kept_when_incomplete(tmp_path, capsys):
    vault, lab, repo = world(tmp_path)
    pd.scan(vault, lab, 60)
    (repo / "pyproject.toml").write_text("not = [toml")
    before = road(repo)
    summary = pd.scan(vault, lab, 60)
    assert "incomplete 1" in summary and road(repo) == before
    assert "incomplete proj ^p9 pyproject.toml" in capsys.readouterr().out


def test_invalid_detect_counted_incomplete(tmp_path):
    vault, lab, repo = world(tmp_path)
    note_ = vault / "resources/knowledge/patterns/python-patterns-superseded.md"
    note_.write_text(note_.read_text().replace("lang: toml", "lang: cobol"))
    assert "incomplete 1" in pd.scan(vault, lab, 60) and MARK not in road(repo).decode()


def test_rejected_never_touched(tmp_path):
    text = f"# R\n\n## Next\n- a\n\n## Rejected\n- Migrate: ^p9 → ^p31 (x) in `p` {MARK}\n"
    vault, lab, repo = world(tmp_path, roadmap=text)
    assert "opened 0" in pd.scan(vault, lab, 60) and road(repo).decode() == text
    (repo / "pyproject.toml").write_text(NEW_TOML)
    assert "closed 0" in pd.scan(vault, lab, 60) and road(repo).decode() == text


def test_marker_elsewhere_never_touched(tmp_path):
    text = f"# R\n\n## Next\n- a\n\n## Later\n- Migrate: ^p9 {MARK}\n"
    vault, lab, repo = world(tmp_path, roadmap=text)
    assert "opened 0" in pd.scan(vault, lab, 60) and road(repo).decode() == text
    (repo / "pyproject.toml").write_text(NEW_TOML)
    assert "closed 0" in pd.scan(vault, lab, 60) and road(repo).decode() == text


def test_matched_files_change_line_unchanged(tmp_path):
    vault, lab, repo = world(tmp_path)
    pd.scan(vault, lab, 60)
    before = road(repo)
    (repo / "sub").mkdir()
    (repo / "sub/pyproject.toml").write_text(OLD_TOML)
    sup = pd.parse_superseded(vault / "resources/knowledge/patterns/python-patterns-superseded.md")[0][0]
    sup.detect.files = ["**/pyproject.toml"]
    out = pd.evaluate(repo, sup.detect)
    assert len(out.files) == 2 and pd.apply_task(repo / ".claude/memory/ROADMAP.md", sup, out) == "kept"
    assert road(repo) == before


def test_no_roadmap_warns(tmp_path, capsys):
    vault, lab, repo = world(tmp_path, roadmap=None)
    summary = pd.scan(vault, lab, 60)
    assert "WARN no ROADMAP proj ^p9" in capsys.readouterr().out
    assert "opened 0" in summary and not (repo / ".claude").exists()


def test_next_section_added_when_missing(tmp_path):
    vault, lab, repo = world(tmp_path, roadmap="# R\n\n## Later\n- b")
    pd.scan(vault, lab, 60)
    text = road(repo).decode()
    assert text.startswith("# R\n\n## Later\n- b\n") and "\n## Next\n- Migrate: ^p9" in text


def test_dormant_open_task_kept(tmp_path):
    line = f"- Migrate: ^p9 → ^p31 (x) in `pyproject.toml` {MARK}\n"
    text = f"# R\n\n## Next\n{line}"
    vault, lab, repo = world(tmp_path, age=200, roadmap=text, toml=NEW_TOML)
    summary = pd.scan(vault, lab, 60)
    assert "scanned 0" in summary and "dormant: 1" in summary and road(repo).decode() == text


def test_crlf_roadmap_kept(tmp_path):
    vault, lab, repo = world(tmp_path, roadmap=b"# R\r\n\r\n## Next\r\n- a\r\n\r\n## Later\r\n- b\r\n")
    pd.scan(vault, lab, 60)
    data = road(repo)
    assert data.count(b"\n") == data.count(b"\r\n") and MARK.encode() in data
    (repo / "pyproject.toml").write_text(NEW_TOML)
    pd.scan(vault, lab, 60)
    assert road(repo) == b"# R\r\n\r\n## Next\r\n- a\r\n\r\n## Later\r\n- b\r\n"


def test_same_path_scanned_once(tmp_path):
    vault, lab, repo = world(tmp_path)
    (vault / "projects/twin.md").write_text(f"---\nstatus: active\npath: {repo}\n---\n")
    summary = pd.scan(vault, lab, 60)
    assert "scanned 1 repos" in summary and "opened 1" in summary and road(repo).decode().count(MARK) == 1


def test_summary_format(tmp_path, capsys):
    vault, lab, repo = world(tmp_path)
    assert SUMMARY.match(pd.scan(vault, lab, 60))
    (repo / "pyproject.toml").write_text("not = [toml")
    assert SUMMARY.match(pd.scan(vault, lab, 60))
    shutil.rmtree(repo)
    assert SUMMARY.match(pd.scan(vault, lab, 60))
    assert pd.main(["scan", "--vault", str(vault), "--lab-root", str(lab)]) == 0
    assert SUMMARY.match(capsys.readouterr().out.strip().splitlines()[-1])


def test_dormant_open_task_listed(tmp_path, capsys):
    text = f"# R\n\n## Next\n- Migrate: ^p9 → ^p31 (x) in `p` {MARK}\n"
    vault, lab, repo = world(tmp_path, age=200, roadmap=text)
    before = road(repo)
    summary = run_scan(vault, lab)
    assert "dormant proj ^p9\n" in capsys.readouterr().out
    assert road(repo) == before
    assert "skipped 1 (dormant: 1)" in summary


def test_dormant_rejected_marker_not_listed(tmp_path, capsys):
    text = f"# R\n\n## Next\n- a\n\n## Rejected\n- Migrate: ^p9 → ^p31 (x) in `p` {MARK}\n"
    vault, lab, repo = world(tmp_path, age=200, roadmap=text)
    run_scan(vault, lab)
    assert "dormant proj" not in capsys.readouterr().out


# ---- follow-up: letter owner, fallback remote, unreadable inputs ----

def test_rule_with_another_notes_letter_fails(tmp_path):
    fails = run(tmp_path, {"git-patterns.md": note("- a ^g1\n"), "storage-patterns.md": note("- b ^g2\n")})
    assert fails == ["FAIL storage-patterns.md: ^g2 uses letter g of git-patterns"]


def test_pitfalls_letter_allowed_in_pattern_note(tmp_path):
    vault, rules = setup(tmp_path, {"git-patterns.md": note("- a ^g1\n- moved from pitfalls ^v12\n"),
                                    "python-patterns-superseded.md": "# T\n\n## Superseded\n- ~~a~~ → ^g1 (2026-11-25, w) ^p1\n"})
    rules.write_text("Letters in `pitfalls.md`: `v` Verification. " + RULES_DOC, encoding="utf-8")
    assert pd.check(vault, rules) == []


def note_with_repo(vault: Path, path: str, repo_url: str) -> None:
    (vault / "projects/proj.md").write_text(f"---\nstatus: active\npath: {path}\nrepo: {repo_url}\n---\n")


def test_fallback_rejects_other_remote(tmp_path, capsys):
    vault, lab, repo = world(tmp_path)
    git(repo, "remote", "add", "origin", "https://github.com/o/other.git")
    note_with_repo(vault, "/gone/lab/proj", "https://github.com/o/proj")
    repos, skipped = pd.active_repos(vault, lab, 60)
    assert repos == [] and skipped == {"not-cloned": 1}


def test_fallback_accepts_same_remote_other_form(tmp_path):
    vault, lab, repo = world(tmp_path)
    git(repo, "remote", "add", "origin", "git@github.com:O/Proj.git")
    note_with_repo(vault, "/gone/lab/proj", "https://github.com/o/proj")
    assert [r.path for r in pd.active_repos(vault, lab, 60)[0]] == [repo]


def test_non_utf8_project_note_skipped(tmp_path, capsys):
    vault, lab, repo = world(tmp_path)
    (vault / "projects/bad.md").write_bytes(b"---\nstatus: active\npath: \xff\xfe\n---\n")
    summary = pd.scan(vault, lab, 60)
    assert "WARN unreadable bad" in capsys.readouterr().out
    assert "scanned 1 repos" in summary and "unreadable: 1" in summary and "opened 1" in summary


def test_non_utf8_superseded_note_skipped(tmp_path, capsys):
    vault, lab, repo = world(tmp_path)
    (vault / "resources/knowledge/patterns/zed-patterns-superseded.md").write_bytes(b"# T\n\xff\n")
    summary = pd.scan(vault, lab, 60)
    assert "WARN unreadable zed-patterns-superseded.md" in capsys.readouterr().out
    assert "opened 1" in summary


def test_readonly_roadmap_skipped(tmp_path, capsys):
    vault, lab, repo = world(tmp_path)
    roadmap = repo / ".claude/memory/ROADMAP.md"
    roadmap.chmod(0o444)
    try:
        summary = pd.scan(vault, lab, 60)
    finally:
        roadmap.chmod(0o644)
    assert "WARN unwritable proj" in capsys.readouterr().out
    assert "unwritable: 1" in summary and "opened 0" in summary and MARK not in road(repo).decode()
