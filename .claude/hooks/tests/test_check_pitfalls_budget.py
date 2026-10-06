"""check-pitfalls-budget.sh: write-time size cap and stable rule ids for pitfalls.md."""
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "check-pitfalls-budget.sh"
FRONT = "---\ntitle: t\ntags:\n- not-a-rule\n---\n\nIntro line.\n\n"  # rules start at line 9


def write(tmp_path: Path, body: str, crlf: bool = False) -> Path:
    f = tmp_path / "pitfalls.md"
    text = FRONT + body
    f.write_bytes(text.replace("\n", "\r\n").encode() if crlf else text.encode())
    return f


def run(f: Path, cap: int) -> subprocess.CompletedProcess:
    return subprocess.run(["bash", str(SCRIPT), str(f), str(cap)], capture_output=True, text=True)


def test_at_cap_passes_and_one_byte_over_fails(tmp_path):
    f = write(tmp_path, "## Verification\n- Check live state. ^v1\n")
    size = f.stat().st_size
    ok = run(f, size)
    assert ok.returncode == 0, ok.stdout
    assert "— ok (1 rules)" in ok.stdout
    over = run(f, size - 1)
    assert over.returncode == 1
    assert "OVER by 1 B" in over.stdout


def test_over_budget_lists_sections_largest_first(tmp_path):
    f = write(tmp_path, "## Small\n- a ^s1\n## Big\n- " + "x" * 200 + " ^b1\n")
    rows = [line.split(None, 1)[1] for line in run(f, 10).stdout.splitlines() if line.startswith("  ")]
    assert rows[0] == "Big"
    assert rows.index("Big") < rows.index("Small")


def test_rule_without_id_fails(tmp_path):
    r = run(write(tmp_path, "## V\n- no id here\n"), 10_000)
    assert r.returncode == 1
    assert "rule without id (line 10): - no id here" in r.stdout


def test_id_like_text_mid_line_is_not_an_id(tmp_path):
    r = run(write(tmp_path, "## V\n- see `^v1` in the docs\n"), 10_000)
    assert r.returncode == 1
    assert "rule without id (line 10)" in r.stdout


def test_duplicate_id_fails(tmp_path):
    r = run(write(tmp_path, "## V\n- one ^v1\n- two ^v1\n"), 10_000)
    assert r.returncode == 1
    assert "duplicate id ^v1 (lines 10, 11)" in r.stdout


def test_retired_id_reused_fails(tmp_path):
    r = run(write(tmp_path, "## V\n- one ^v2\n\n## Retired ids\n^v2→^v1\n"), 10_000)
    assert r.returncode == 1
    assert "retired id reused ^v2 (line 10)" in r.stdout


def test_retired_section_and_frontmatter_lines_need_no_id(tmp_path):
    r = run(write(tmp_path, "## V\n- one ^v1 \n\n## Retired ids\n^v2→^v1\n"), 10_000)
    assert r.returncode == 0, r.stdout


def test_crlf_file_is_checked_like_lf(tmp_path):
    r = run(write(tmp_path, "## V\n- no id here\n", crlf=True), 10_000)
    assert r.returncode == 1
    assert "rule without id (line 10)" in r.stdout


def test_missing_file_exits_2(tmp_path):
    assert run(tmp_path / "nope.md", 10).returncode == 2
