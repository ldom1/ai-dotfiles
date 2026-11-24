"""load.sh prints one `[domain]` pointer line when the project note has `domain:`."""
import subprocess
from pathlib import Path

LOAD = Path(__file__).resolve().parents[1] / "load.sh"
POINTER = "[domain] homelab: /domain-brief <sujet>"


def run_load(tmp_path: Path, frontmatter: str, *args: str, extra: str = "") -> str:
    vault = tmp_path / "vault"
    (vault / "projects").mkdir(parents=True)
    body = "\n".join(f"line {i} of the project note" for i in range(40))
    (vault / "projects/homelab.md").write_text(f"---\ntitle: homelab\n{frontmatter}---\n\n# homelab\n{extra}{body}\n")
    env_file = tmp_path / "brain.env"
    env_file.write_text(f"BRAIN_PATH={vault}\nexport BRAIN_PATH\n")
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    (repo / ".brain-project").write_text("homelab\n")
    out = subprocess.run(
        ["bash", str(LOAD), *args],
        cwd=repo,
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "BRAIN_ENV_FILE": str(env_file), "BRAIN_LOAD_SKIP_MEMORY": "1"},
        capture_output=True,
        text=True,
        check=True,
    )
    return out.stdout


def test_pointer_printed(tmp_path):
    assert POINTER in run_load(tmp_path, "domain: homelab\n").splitlines()


def test_no_pointer_without_domain(tmp_path):
    assert "[domain]" not in run_load(tmp_path, "")


def test_pointer_with_max_bytes(tmp_path):
    out = run_load(tmp_path, "domain: homelab\n", "--max-bytes", "200")
    assert "note truncated" in out
    assert POINTER in out.splitlines()


def test_domain_in_body_is_ignored(tmp_path):
    assert "[domain]" not in run_load(tmp_path, "", extra="domain: homelab\n")


def test_pointer_with_crlf_note(tmp_path):
    run_load(tmp_path, "domain: homelab\n")
    vault_note = tmp_path / "vault/projects/homelab.md"
    vault_note.write_bytes(vault_note.read_bytes().replace(b"\r\n", b"\n").replace(b"\n", b"\r\n"))
    out = subprocess.run(
        ["bash", str(LOAD)], cwd=tmp_path / "repo",
        env={"PATH": "/usr/bin:/bin", "HOME": str(tmp_path), "BRAIN_ENV_FILE": str(tmp_path / "brain.env"), "BRAIN_LOAD_SKIP_MEMORY": "1"},
        capture_output=True, text=True, check=True,
    ).stdout
    assert POINTER in out.splitlines()


def test_pointer_with_quoted_domain(tmp_path):
    assert POINTER in run_load(tmp_path, 'domain: "homelab"  \n').splitlines()
