from pathlib import Path
import subprocess


def _clean(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1].strip()
    return value


def _frontmatter(path: Path) -> dict[str, str] | None:
    lines = path.read_text().splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        end = next(i for i, line in enumerate(lines[1:], start=1) if line.strip() == "---")
    except StopIteration:
        return None
    meta: dict[str, str] = {}
    for line in lines[1:end]:
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = _clean(value)
    return meta


def _skill_files(root: Path) -> list[Path]:
    git = root / ".git"
    if git.exists():
        proc = subprocess.run(
            ["git", "-C", str(root), "ls-files", "skills/*/SKILL.md"],
            check=True,
            capture_output=True,
            text=True,
        )
        return [root / p for p in proc.stdout.splitlines() if p]
    return list((root / "skills").glob("*/SKILL.md"))


def bad_skills(root: Path) -> list[str]:
    bad = []
    for skill in _skill_files(root):
        name = skill.parent.name
        if name.startswith("coe-"):
            continue
        meta = _frontmatter(skill)
        if meta is None or meta.get("name") != name or not meta.get("description"):
            bad.append(name)
    return sorted(bad)


def test_repo_skills_have_matching_frontmatter():
    repo = Path(__file__).resolve().parents[3]
    assert bad_skills(repo) == []


def test_mismatch_is_reported(tmp_path: Path):
    skills = tmp_path / "skills"
    (skills / "good").mkdir(parents=True)
    (skills / "bad").mkdir(parents=True)
    (skills / "empty").mkdir(parents=True)
    (skills / "good" / "SKILL.md").write_text(
        "---\nname: good\ndescription: ok\n---\nbody\n"
    )
    (skills / "bad" / "SKILL.md").write_text(
        "---\nname: other\ndescription: ok\n---\nbody\n"
    )
    (skills / "empty" / "SKILL.md").write_text(
        "---\nname: empty\ndescription:\n---\nbody\n"
    )
    assert bad_skills(tmp_path) == ["bad", "empty"]
