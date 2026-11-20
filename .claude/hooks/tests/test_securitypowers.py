"""securitypowers plugin: profile freshness check, ASVS generator, router and sub-skill contracts."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
PLUGIN = REPO / "skills/securitypowers"
CHECK = PLUGIN / "scripts/profile-check.sh"
GEN_ASVS = PLUGIN / "scripts/gen-asvs.py"


def _check(project: Path, today: str = "2026-11-20", *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["bash", str(CHECK), *args, str(project)],
        capture_output=True, text=True, env={"PATH": "/usr/bin:/bin", "TODAY": today},
    )


def _profile(project: Path, reviewed: str | None, sources: list[str], digest: str | None = None) -> None:
    lines = ["---"]
    if reviewed:
        lines.append(f"reviewed: {reviewed}")
    lines.append("sources:")
    lines += [f"  - {s}" for s in sources]
    if digest is None:
        h = hashlib.sha256()
        for s in sources:
            h.update((project / s).read_bytes())
        digest = h.hexdigest()
    lines += [f"sources_sha256: {digest}", "---", "", "# Security profile", ""]
    (project / ".agents").mkdir(exist_ok=True)
    (project / ".agents/security-profile.md").write_text("\n".join(lines))


def _project(tmp_path: Path) -> Path:
    (tmp_path / "inventory.yml").write_text("all:\n  hosts: {node1: {}}\n")
    (tmp_path / "firewall.yml").write_text("ports: [22, 443]\n")
    return tmp_path


def test_profile_missing(tmp_path):
    r = _check(tmp_path)
    assert (r.returncode, r.stdout.strip()) == (1, "missing")


def test_profile_ok(tmp_path):
    p = _project(tmp_path)
    _profile(p, "2026-11-01", ["inventory.yml", "firewall.yml"])
    r = _check(p)
    assert (r.returncode, r.stdout.strip()) == (0, "ok")


def test_profile_stale_age(tmp_path):
    p = _project(tmp_path)
    _profile(p, "2026-01-01", ["inventory.yml"])
    r = _check(p)
    assert (r.returncode, r.stdout.strip()) == (2, "stale: reviewed 323 days ago")


def test_profile_stale_hash(tmp_path):
    p = _project(tmp_path)
    _profile(p, "2026-11-01", ["inventory.yml", "firewall.yml"])
    (p / "firewall.yml").write_text("ports: [22, 443, 3306]\n")
    r = _check(p)
    assert (r.returncode, r.stdout.strip()) == (2, "stale: sources changed")


def test_profile_source_missing(tmp_path):
    p = _project(tmp_path)
    _profile(p, "2026-11-01", ["inventory.yml"])
    (p / "inventory.yml").unlink()
    r = _check(p)
    assert (r.returncode, r.stdout.strip()) == (2, "stale: source missing inventory.yml")


def test_profile_no_reviewed(tmp_path):
    p = _project(tmp_path)
    _profile(p, None, ["inventory.yml"])
    r = _check(p)
    assert (r.returncode, r.stdout.strip()) == (2, "stale: no reviewed date")


def test_profile_hash_mode_matches(tmp_path):
    p = _project(tmp_path)
    _profile(p, "2026-11-01", ["inventory.yml", "firewall.yml"], digest="0" * 64)
    expected = hashlib.sha256(b"".join((p / s).read_bytes() for s in ["inventory.yml", "firewall.yml"])).hexdigest()
    r = _check(p, "2026-11-20", "--hash")
    assert (r.returncode, r.stdout.strip()) == (0, expected)


def test_profile_bad_reviewed_date(tmp_path):
    p = _project(tmp_path)
    _profile(p, "last week", ["inventory.yml"])
    r = _check(p)
    assert (r.returncode, r.stdout.strip()) == (2, "stale: bad reviewed date 'last week'")


ASVS_HEADER = "chapter_id,chapter_name,section_id,section_name,req_id,req_description,L\n"


def _gen(tmp_path: Path, rows: str) -> tuple[subprocess.CompletedProcess, str]:
    csv_path, out = tmp_path / "asvs.csv", tmp_path / "asvs.md"
    csv_path.write_text(ASVS_HEADER + rows, encoding="utf-8")
    r = subprocess.run(["python3", str(GEN_ASVS), str(csv_path), str(out)], capture_output=True, text=True)
    return r, out.read_text() if out.exists() else ""


def test_gen_asvs_keeps_unknown_level(tmp_path):
    rows = (
        'V1,Encoding,V1.2,Injection,V1.2.1,"Verify that output encoding, per context.",1\n'
        "V1,Encoding,V1.2,Injection,V1.2.9,Verify | pipes are escaped.,\n"
        "V6,Authentication,V6.2,Passwords,V6.2.1,Verify passwords are at least 8 characters.,1\n"
    )
    r, md = _gen(tmp_path, rows)
    assert r.returncode == 0, r.stderr
    assert "| V1.2.1 | 1 | Verify that output encoding, per context. |" in md
    assert "| V1.2.9 | ? | Verify \\| pipes are escaped. |" in md
    assert md.index("## V1 Encoding") < md.index("## V6 Authentication")
    assert "traceability" in md and "not a claim of coverage" in md
    assert "Requirements: 3 (L1: 2, L2: 0, L3: 0, unknown: 1)" in md


def test_gen_asvs_real_reference_is_complete():
    md = (PLUGIN / "references/asvs-5.0.md").read_text()
    rows = [line for line in md.splitlines() if re.match(r"^\| V\d+\.\d+\.\d+ \|", line)]
    assert len(rows) == 345
    assert "Requirements: 345 (L1: 70, L2: 183, L3: 92, unknown: 0)" in md


SUB = PLUGIN / "skills"
STRIX = {"find-security-vulnerabilities-in-code", "fix-security-vulnerabilities-with-strix"}
VENDORED = {"semgrep", "sarif-parsing", "differential-review", "sharp-edges", "supply-chain-risk-auditor", "owasp-security"}


def _routing_table_names() -> set[str]:
    text = (PLUGIN / "SKILL.md").read_text()
    section = text.split("## Routing Table", 1)[1].split("\n## ", 1)[0]
    return {m.group(1) for m in re.finditer(r"^\| `([a-z0-9-]+)` \|", section, re.M)}


def test_router_table_matches_dirs():
    dirs = {p.name for p in SUB.iterdir() if p.is_dir() and p.name != "securitypowers"}
    assert _routing_table_names() == dirs | STRIX


def test_router_symlink():
    link = SUB / "securitypowers/SKILL.md"
    assert link.is_symlink() and link.resolve() == (PLUGIN / "SKILL.md").resolve()


def test_vendored_have_license():
    for name in VENDORED:
        assert (SUB / name / "LICENSE").is_file(), name
    assert (PLUGIN / "references/insecure-defaults/LICENSE").is_file()


def test_pins_listed():
    cfg = json.loads((REPO / "config/vendored-skills.json").read_text())
    pins = {s["pin_file"] for s in cfg["skills"]}
    for pin in PLUGIN.glob(".*_version"):
        assert str(pin.relative_to(REPO)) in pins, pin.name
        assert re.fullmatch(r"[0-9a-f]{12}", pin.read_text().strip()), pin.name


def test_exposure_scan_refuses_unlisted_target():
    text = (SUB / "exposure-scan/SKILL.md").read_text()
    assert "authorized_targets" in text and "refuse" in text
    assert "ask the owner to confirm" in text and "pinned IP" in text


def test_host_hardening_contract():
    text = (SUB / "host-hardening/SKILL.md").read_text()
    assert "oscap info" in text and "not a certification" in text
    assert "Ask for confirmation before the first SSH command" in text


def test_audit_report_contract():
    text = (SUB / "audit-report/SKILL.md").read_text()
    assert "Comprendre l'audit" in text and ".gitignore" in text
    assert "resources/knowledge/security/" in text and "Generic only" in text


def test_every_sub_skill_reads_profile():
    for name in ("scan-fix-loop", "iac-scan", "host-hardening", "exposure-scan", "threat-model"):
        assert "profile-check.sh" in (SUB / name / "SKILL.md").read_text(), name
