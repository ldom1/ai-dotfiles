"""fit-sections.py: print a Markdown file within N bytes, whole '## ' sections only, and name what was dropped."""
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[3] / "scripts" / "fit-sections.py"
PRE = "---\ntitle: t\n---\n\nIntro.\n\n"
A = "## A\n- a1 ^a1\n"
B = "## B\n" + "".join(f"- {'b' * 300} ^b{i}\n" for i in range(3))
C = "## C\n- c1 ^c1\n"


def run(tmp_path: Path, text: str, cap: int, crlf: bool = False) -> str:
    f = tmp_path / "pitfalls.md"
    f.write_bytes(text.replace("\n", "\r\n").encode() if crlf else text.encode())
    return subprocess.run(["python3", str(SCRIPT), str(f), str(cap)], capture_output=True, text=True, check=True).stdout


def test_file_that_fits_is_printed_unchanged(tmp_path):
    text = PRE + A + B + C
    assert run(tmp_path, text, 10_000) == text


def test_cut_keeps_whole_sections_in_order_and_names_the_rest(tmp_path):
    text = PRE + A + B + C
    cap = len((PRE + A).encode()) + 400 + 50  # A fits, B does not; C would fit but comes after B
    out = run(tmp_path, text, cap)
    assert out.startswith(PRE + A)
    assert "## B" not in out and "## C" not in out
    last = out.splitlines()[-1]
    assert last.startswith(f"[truncated: {len((B + C).encode()):,} B omitted, sections dropped: B, C")
    assert len(out.encode()) <= cap


def test_room_smaller_than_preamble_prints_only_the_note(tmp_path):
    out = run(tmp_path, PRE + A + B + C, 400)  # room = 0: not even the 26 B preamble fits
    assert out.splitlines() == [out.strip()]
    assert "sections dropped: (preamble), A, B, C" in out


def test_crlf_file_is_cut_like_lf(tmp_path):
    out = run(tmp_path, PRE + A + B + C, len((PRE + A).encode()) + 450, crlf=True)
    assert "sections dropped: B, C" in out
    assert "\r" not in out
