"""link-pattern-rules.sh: link vault pattern notes with `paths:` into a Claude Code rules dir."""
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "link-pattern-rules.sh"
WITH_PATHS = "---\ntitle: Docker\ntags: [knowledge]\npaths:\n  - \"**/Dockerfile*\"\n---\n\n# Docker\n"
NO_PATHS = "---\ntitle: Python\ntags: [knowledge]\n---\n\n# Python\npaths: in the body does not count\n"


def vault(tmp_path: Path) -> Path:
    patterns = tmp_path / "vault" / "resources" / "knowledge" / "patterns"
    patterns.mkdir(parents=True)
    (patterns / "docker-patterns.md").write_text(WITH_PATHS)
    (patterns / "python-patterns.md").write_text(NO_PATHS)
    (patterns / "poc-deployment-pattern.md").write_text(WITH_PATHS)  # not a *-patterns.md note
    return tmp_path / "vault"


def run(brain: Path, rules: Path) -> subprocess.CompletedProcess:
    r = subprocess.run(["bash", str(SCRIPT), str(brain), str(rules)], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    return r


def links(rules: Path) -> dict:
    return {p.name: p.resolve() for p in rules.iterdir() if p.is_symlink()}


def test_links_only_notes_with_paths(tmp_path):
    brain, rules = vault(tmp_path), tmp_path / "rules"
    run(brain, rules)
    note = brain / "resources/knowledge/patterns/docker-patterns.md"
    assert links(rules) == {"docker-patterns.md": note.resolve()}


def test_rerun_is_idempotent(tmp_path):
    brain, rules = vault(tmp_path), tmp_path / "rules"
    run(brain, rules)
    first = links(rules)
    run(brain, rules)
    assert links(rules) == first
    assert sorted(p.name for p in rules.iterdir()) == ["docker-patterns.md"]


def test_crlf_frontmatter_counts(tmp_path):
    brain, rules = vault(tmp_path), tmp_path / "rules"
    note = brain / "resources/knowledge/patterns/infisical-patterns.md"
    note.write_bytes(WITH_PATHS.replace("\n", "\r\n").encode())
    run(brain, rules)
    assert "infisical-patterns.md" in links(rules)


def test_stale_links_removed_other_rules_kept(tmp_path):
    brain, rules = vault(tmp_path), tmp_path / "rules"
    run(brain, rules)
    (rules / "my-rule.md").write_text("---\npaths: [\"**/x\"]\n---\nmine\n")
    gone = rules / "old-patterns.md"
    gone.symlink_to(tmp_path / "deleted-patterns.md")
    (brain / "resources/knowledge/patterns/docker-patterns.md").write_text(NO_PATHS)
    r = run(brain, rules)
    assert sorted(p.name for p in rules.iterdir()) == ["my-rule.md"]
    assert "removed docker-patterns.md" in r.stdout
