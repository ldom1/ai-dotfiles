"""ontologie.py: project activity of each element and consistency of the links (spec 2026-11-20-ontologie-design)."""
import importlib.util
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "ontologie.py"
spec = importlib.util.spec_from_file_location("ontologie", SCRIPT)
onto = importlib.util.module_from_spec(spec)
spec.loader.exec_module(onto)

SLURM = """---
title: "Slurm"
aliases:
  - "SLURM"
created: 2026-11-20
tags: [ontologie, technologie]
status: active
concepts:
  - "[[orchestration]]"
level: maîtrise
---

# Slurm

> Ordonnanceur.
"""


def write(vault: Path, rel: str, text: str) -> Path:
    path = vault / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def element(level: str, title: str, extra: str = "") -> str:
    return f'---\ntitle: "{title}"\ncreated: 2026-11-20\ntags: [ontologie, {level}]\nstatus: active\n{extra}---\n\n# {title}\n'


def project(vault: Path, slug: str, links: str, logs: tuple[str, ...] = ()) -> Path:
    for name in logs:
        write(vault, f"inbox/daily/implementation/{slug}/{name}", "## log\n")
    return write(vault, f"projects/{slug}.md", f'---\ntitle: {slug}\ncaps: "[[Artelys]]"\n---\n\n# {slug}\n\n## Links\n- none\n\n## Ontologie\n{links}\n')


def vault_ok(tmp_path: Path) -> Path:
    """A small valid vault: one concept, one sujet, two technologies, one project with two logs."""
    write(tmp_path, "ontologie/concepts/orchestration.md", element("concept", "Orchestration", "level:\n"))
    write(tmp_path, "ontologie/sujets/monte-carlo.md",
          element("sujet", "Monte-Carlo ?", 'asked_by:\n  - clients\nconcepts:\n  - "[[orchestration]]"\n'))
    write(tmp_path, "ontologie/technologies/slurm.md", SLURM)
    write(tmp_path, "ontologie/technologies/python.md", element("technologie", "Python", "concepts: []\nlevel:\n"))
    project(tmp_path, "hpc", "[[slurm]] [[python]] [[monte-carlo]]", ("2026-05-03-a.md", "2026-11-18-b.md"))
    return tmp_path


def run(capsys, *argv: str) -> tuple[int, str]:
    code = onto.main(list(argv))
    return code, capsys.readouterr().out


def prop(path: Path, key: str) -> str | None:
    for line in path.read_text(encoding="utf-8").split("\n---\n", 1)[0].splitlines():
        if line.startswith(f"{key}:"):
            return line.split(":", 1)[1].strip()
    return None


def test_activity_writes_the_month_of_the_latest_project_log(tmp_path, capsys):
    v = vault_ok(tmp_path)
    code, out = run(capsys, "activity", str(v))
    assert code == 0 and out.strip() == "OK 3 notes, 3 changed"
    assert prop(v / "ontologie/technologies/slurm.md", "project_activity") == "2026-11"
    assert prop(v / "ontologie/sujets/monte-carlo.md", "project_activity") == "2026-11"
    assert prop(v / "ontologie/concepts/orchestration.md", "project_activity") is None  # concepts get none


def test_activity_takes_the_latest_month_over_several_projects(tmp_path, capsys):
    v = vault_ok(tmp_path)
    project(v, "old", "[[slurm]]", ("2025-12-30-x.md",))
    project(v, "new", "[[python]]", ("2027-01-02-y.md", "notes.md"))
    run(capsys, "activity", str(v))
    assert prop(v / "ontologie/technologies/slurm.md", "project_activity") == "2026-11"
    assert prop(v / "ontologie/technologies/python.md", "project_activity") == "2027-01"


def test_activity_project_with_no_log_gives_no_date(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/technologies/dagster.md", element("technologie", "Dagster", "concepts: []\nlevel:\n"))
    project(v, "nolog", "[[dagster]]")
    code, _ = run(capsys, "activity", str(v))
    assert code == 0
    assert prop(v / "ontologie/technologies/dagster.md", "project_activity") is None


def test_activity_second_run_changes_nothing(tmp_path, capsys):
    v = vault_ok(tmp_path)
    run(capsys, "activity", str(v))
    before = (v / "ontologie/technologies/slurm.md").read_bytes()
    _, out = run(capsys, "activity", str(v))
    assert out.strip() == "OK 3 notes, 0 changed"
    assert (v / "ontologie/technologies/slurm.md").read_bytes() == before


def test_activity_keeps_the_rest_of_the_note_byte_for_byte(tmp_path, capsys):
    v = vault_ok(tmp_path)
    run(capsys, "activity", str(v))
    after = (v / "ontologie/technologies/slurm.md").read_text(encoding="utf-8")
    assert after == SLURM.replace("level: maîtrise\n", "level: maîtrise\nproject_activity: 2026-11\n")


def test_activity_reads_the_logs_of_the_renamed_project_only(tmp_path, capsys):
    v = vault_ok(tmp_path)
    (v / "projects/hpc.md").rename(v / "projects/crystal.md")  # the logs of `hpc` stay under the old name
    write(v, "inbox/daily/implementation/crystal/2026-07-01-z.md", "## log\n")
    run(capsys, "activity", str(v))
    assert prop(v / "ontologie/technologies/slurm.md", "project_activity") == "2026-07"


def test_activity_removes_the_date_when_no_project_links_the_element(tmp_path, capsys):
    v = vault_ok(tmp_path)
    run(capsys, "activity", str(v))
    project(v, "hpc", "[[python]]", ())  # slurm and the sujet are no longer linked
    _, out = run(capsys, "activity", str(v))
    assert prop(v / "ontologie/technologies/slurm.md", "project_activity") is None
    assert prop(v / "ontologie/technologies/python.md", "project_activity") == "2026-11"
    assert out.strip() == "OK 3 notes, 2 changed"


def test_activity_counts_only_the_ontologie_section_of_project_notes(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/technologies/dagster.md", element("technologie", "Dagster", "concepts: []\nlevel:\n"))
    write(v, "inbox/daily/specs/hpc/2026-11-01-design.md", "Uses [[dagster]].\n")
    write(v, "projects/other.md", "---\ntitle: other\n---\n\n## Links\n- [[dagster]]\n")  # a link outside the section
    write(v, "inbox/daily/implementation/other/2026-10-10-a.md", "## log\n")
    run(capsys, "activity", str(v))
    assert prop(v / "ontologie/technologies/dagster.md", "project_activity") is None


def test_check_clean_vault_is_ok(tmp_path, capsys):
    code, out = run(capsys, "check", str(vault_ok(tmp_path)))
    assert (code, out.strip()) == (0, "OK 4 elements")


def test_check_dangling_link_in_a_project_section(tmp_path, capsys):
    v = vault_ok(tmp_path)
    project(v, "hpc", "[[slurm]] [[python]] [[monte-carlo]] [[slrum]]")
    code, out = run(capsys, "check", str(v))
    assert code == 1
    assert "FAIL projects/hpc.md: link [[slrum]] in ## Ontologie has no note in ontologie/" in out


def test_check_project_section_link_to_a_note_outside_ontologie(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "resources/docker-patterns.md", "# rules\n")
    project(v, "hpc", "[[slurm]] [[python]] [[monte-carlo]] [[docker-patterns]]")
    code, out = run(capsys, "check", str(v))
    assert code == 1 and "FAIL projects/hpc.md: link [[docker-patterns]] in ## Ontologie has no note in ontologie/" in out


def test_check_property_link_to_the_wrong_level(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/technologies/dagster.md",
          element("technologie", "Dagster", 'concepts:\n  - "[[monte-carlo]]"\n  - "[[nowhere]]"\nlevel:\n'))
    project(v, "p2", "[[dagster]]")
    code, out = run(capsys, "check", str(v))
    assert code == 1
    assert "FAIL ontologie/technologies/dagster.md: concepts link [[monte-carlo]] is not a note in ontologie/concepts/" in out
    assert "FAIL ontologie/technologies/dagster.md: concepts link [[nowhere]] is not a note in ontologie/concepts/" in out


def test_check_duplicate_file_name_in_the_vault(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "projects/slurm.md", "---\ntitle: slurm\n---\n")
    code, out = run(capsys, "check", str(v))
    assert code == 1
    assert "FAIL ontologie/technologies/slurm.md: file name also exists at projects/slurm.md" in out


def test_check_archive_copies_are_not_duplicates(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "archive/slurm.md", "# old\n")
    code, _ = run(capsys, "check", str(v))
    assert code == 0


def test_check_sujet_without_concept(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/sujets/cout.md", element("sujet", "Coût ?", "asked_by:\n  - moi\nconcepts: []\n"))
    project(v, "p2", "[[cout]]")
    code, out = run(capsys, "check", str(v))
    assert code == 1 and "FAIL ontologie/sujets/cout.md: a sujet needs at least one concept" in out


def test_check_values_outside_the_allowed_lists(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/sujets/monte-carlo.md",
          element("sujet", "Monte-Carlo ?", 'asked_by:\n  - client\nconcepts:\n  - "[[orchestration]]"\n'))
    write(v, "ontologie/technologies/python.md", element("technologie", "Python", "concepts: []\nlevel: expert\n"))
    code, out = run(capsys, "check", str(v))
    assert code == 1
    assert "FAIL ontologie/sujets/monte-carlo.md: asked_by value 'client' is not one of moi, clients, prospects" in out
    assert "FAIL ontologie/technologies/python.md: level value 'expert' is not one of maîtrise, pratique, notion" in out


def test_check_sujet_without_asked_by(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/sujets/monte-carlo.md", element("sujet", "Monte-Carlo ?", 'concepts:\n  - "[[orchestration]]"\n'))
    code, out = run(capsys, "check", str(v))
    assert code == 1 and "FAIL ontologie/sujets/monte-carlo.md: asked_by is empty" in out


def test_check_unlinked_element_is_a_warning(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/technologies/rust.md", element("technologie", "Rust", "concepts: []\nlevel:\n"))
    code, out = run(capsys, "check", str(v))
    assert code == 0
    assert "WARN ontologie/technologies/rust.md: no project and no ontologie note links it" in out
    assert out.strip().endswith("OK 5 elements")


def test_check_note_without_frontmatter(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "ontologie/concepts/vide.md", "# vide\n")
    code, out = run(capsys, "check", str(v))
    assert code == 1 and "FAIL ontologie/concepts/vide.md: no frontmatter block" in out


def test_no_vault_is_an_error(tmp_path, capsys, monkeypatch):
    monkeypatch.delenv("BRAIN_PATH", raising=False)
    assert onto.main(["check"]) == 2
    assert onto.main(["check", str(tmp_path / "missing")]) == 2


def test_check_project_or_rules_link_to_a_missing_note(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "resources/python-patterns.md", "# rules\n")
    write(v, "ontologie/technologies/python.md",
          element("technologie", "Python", 'concepts: []\nlevel:\nrules: "[[python-patterns]]"\nproject: "[[gone]]"\n'))
    code, out = run(capsys, "check", str(v))
    assert code == 1
    assert out.count("FAIL") == 1
    assert "FAIL ontologie/technologies/python.md: project link [[gone]] has no note in the vault" in out


def test_vault_without_an_ontologie_folder_is_an_error_not_ok(tmp_path, capsys):
    (tmp_path / "projects").mkdir()
    for command in ("check", "activity"):
        code, out = run(capsys, command, str(tmp_path))
        assert code == 2 and "OK" not in out


def test_check_ignores_the_obsidian_trash(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, ".trash/slurm.md", "# deleted\n")
    code, out = run(capsys, "check", str(v))
    assert (code, out.strip()) == (0, "OK 4 elements")


def test_links_with_alias_or_heading_and_a_section_that_is_not_last(tmp_path, capsys):
    v = vault_ok(tmp_path)
    write(v, "projects/hpc.md", "---\ntitle: hpc\n---\n\n## Ontologie\n[[slurm|Slurm 25]] [[python#usage]] [[monte-carlo]]\n\n## Links\n- [[gone]]\n")
    code, out = run(capsys, "check", str(v))
    assert (code, out.strip()) == (0, "OK 4 elements")  # [[gone]] is outside the section
    run(capsys, "activity", str(v))
    assert prop(v / "ontologie/technologies/slurm.md", "project_activity") == "2026-11"
    assert prop(v / "ontologie/technologies/python.md", "project_activity") == "2026-11"


def test_check_reports_a_repeated_dangling_link_once(tmp_path, capsys):
    v = vault_ok(tmp_path)
    project(v, "hpc", "[[slurm]] [[python]] [[monte-carlo]] [[slrum]] [[slrum]]")
    _, out = run(capsys, "check", str(v))
    assert out.count("[[slrum]]") == 1


REPO = Path(__file__).resolve().parents[3]


def test_capture_skill_names_the_commands_and_the_two_bans():
    text = (REPO / "skills/capture/SKILL.md").read_text(encoding="utf-8")
    section = text.split("### Ontologie", 1)[1].split("\n## ", 1)[0]
    assert "uv run --script ~/ai-dotfiles/scripts/ontologie.py activity" in section
    assert "uv run --script ~/ai-dotfiles/scripts/ontologie.py check" in section
    assert "Never create a note in `ontologie/`" in section and "Never write `level`" in section
    assert "`type: arbitrage`" in section and "## Ontologie" in section
    assert "that the owner did not accept" in section  # an accepted proposal is created by the agent
    assert "Never fix a `FAIL` by creating a note" in section


def test_brain_audit_connect_runs_the_check_and_never_merges_alone():
    text = (REPO / "skills/brain-audit/skills/connect/SKILL.md").read_text(encoding="utf-8")
    section = text.split("## Ontologie", 1)[1]
    assert "ontologie.py check" in section and "ontologie.py activity" in section
    assert "Do not merge them yourself" in section and "`archive/`" in section
    assert "never write `level`" in section
    assert "that the owner did not accept" in section and "Never fix a `FAIL` by creating a note" in section
