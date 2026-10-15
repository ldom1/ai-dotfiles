import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

import mutate
from mutate import generate_mutants

MUTATE = Path(__file__).parent.parent / "mutate.py"

CALC = '''import re


def is_adult(age):
    return age >= 18


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def add(a, b):
    return a + b
'''

TESTS = '''from calc import add, is_adult, slug


def test_boundary():
    assert is_adult(18) and not is_adult(17)


def test_vacuous():
    assert is_adult(30) or True


def test_slug():
    assert slug("Acme  Corp") == "acme-corp"


def test_add():
    assert add(2, 3) == 5
'''


def project(tmp_path: Path) -> Path:
    (tmp_path / "calc.py").write_text(CALC)
    (tmp_path / "test_calc.py").write_text(TESTS)
    return tmp_path


def run(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, str(MUTATE), "--source", "calc.py", *args],
        cwd=cwd, capture_output=True, text=True, timeout=300,
    )


def test_generate_mutants_operators():
    descs = [m.desc for m in generate_mutants('def f(a):\n    """Doc."""\n    return a < 1\n')]
    assert "Lt -> GtE" in descs
    assert "1 -> 2" in descs
    assert "return None" in descs
    assert not any("Doc." in d for d in descs)


def test_regex_quantifier_escape_rules():
    source = (
        "import re\n\n"
        "def f():\n"
        '    return re.compile(r"\\\\+\\+(?:x\\(?y")\n'
    )
    descs = [m.desc for m in generate_mutants(source)]
    assert "regex '\\\\\\\\+\\\\+(?:x\\\\(?y': drop '+' at 2" in descs
    assert "regex '\\\\\\\\+\\\\+(?:x\\\\(?y': drop '?' at 11" in descs
    assert "regex '\\\\\\\\+\\\\+(?:x\\\\(?y': drop '+' at 4" not in descs
    assert "regex '\\\\\\\\+\\\\+(?:x\\\\(?y': drop '?' at 6" not in descs


def test_lines_filter():
    mutants = generate_mutants(CALC, {5})
    assert mutants and all(m.lineno == 5 for m in mutants)


def test_vacuous_test_fails(tmp_path):
    proc = run(project(tmp_path), "--test", "test_calc.py::test_boundary", "--test", "test_calc.py::test_vacuous")
    assert proc.returncode == 1, proc.stdout + proc.stderr
    assert "FAIL test_calc.py::test_vacuous: killed no mutant" in proc.stdout
    assert "FAIL test_calc.py::test_boundary" not in proc.stdout


def test_strong_test_passes(tmp_path):
    proc = run(project(tmp_path), "--test", "test_calc.py::test_boundary", "--lines", "4")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert "test_calc.py::test_boundary\tkilled" in proc.stdout


def test_regex_quantifier_mutant(tmp_path):
    proc = run(project(tmp_path), "--test", "test_calc.py::test_slug", "--lines", "7")
    assert proc.returncode == 0, proc.stdout + proc.stderr
    assert any(line.startswith("killed") and "regex" in line for line in proc.stdout.splitlines())


def test_same_size_mutant_is_not_masked_by_pyc(tmp_path):
    # "a - 0" survives, then "a + 1" (same size, same second) must not reuse its .pyc
    (tmp_path / "calc.py").write_text("def add_zero(a):\n    return a + 0\n")
    (tmp_path / "test_calc.py").write_text(
        "from calc import add_zero\n\n\ndef test_add_zero():\n    assert add_zero(2) == 2\n"
    )
    lines = run(tmp_path, "--test", "test_calc.py::test_add_zero").stdout.splitlines()
    assert any(line.startswith("survived") and "Add -> Sub" in line for line in lines), lines
    assert any(line.startswith("killed") and "0 -> 1" in line for line in lines), lines


def test_baseline_failure_exits_2(tmp_path):
    root = project(tmp_path)
    (root / "test_calc.py").write_text(TESTS + "\n\ndef test_broken():\n    assert False\n")
    proc = run(root, "--test", "test_calc.py::test_broken")
    assert proc.returncode == 2
    assert "baseline" in proc.stderr


def test_source_restored(tmp_path):
    root = project(tmp_path)
    run(root, "--test", "test_calc.py::test_boundary")
    assert (root / "calc.py").read_text() == CALC
    assert not (root / "calc.py.mutate-orig").exists()


def test_leftover_backup_blocks_run(tmp_path):
    root = project(tmp_path)
    (root / "calc.py.mutate-orig").write_text("old")
    proc = run(root, "--test", "test_calc.py::test_boundary")
    assert proc.returncode == 2
    assert (root / "calc.py").read_text() == CALC


def test_import_breaking_mutant_is_invalid(tmp_path):
    (tmp_path / "calc.py").write_text('LIMIT = int("18")\n\n\ndef is_adult(age):\n    return age >= LIMIT\n')
    (tmp_path / "test_calc.py").write_text(
        "from calc import is_adult\n\n\ndef test_vacuous():\n    assert is_adult(30) or True\n"
    )
    proc = run(tmp_path, "--test", "test_calc.py::test_vacuous", "--lines", "1")
    assert any(line.startswith("invalid") for line in proc.stdout.splitlines()), proc.stdout
    assert proc.returncode == 1


def test_keyboard_interrupt_restores_source(tmp_path, monkeypatch):
    root = project(tmp_path)
    original = (root / "calc.py").read_bytes()
    calls = {"count": 0}

    def fake_outcomes(_cmd, _tests, _timeout):
        calls["count"] += 1
        if calls["count"] == 1:
            return {"test_calc.py::test_boundary": True}
        raise KeyboardInterrupt

    monkeypatch.setattr(mutate, "_outcomes", fake_outcomes)
    with pytest.raises(KeyboardInterrupt):
        mutate.main(
            [
                "--source",
                str(root / "calc.py"),
                "--test",
                "test_calc.py::test_boundary",
            ]
        )
    assert (root / "calc.py").read_bytes() == original
    assert not (root / "calc.py.mutate-orig").exists()


def test_bad_lines_exits_2(tmp_path):
    proc = run(project(tmp_path), "--test", "test_calc.py::test_boundary", "--lines", "x")
    assert proc.returncode == 2
    assert proc.stderr.startswith("error:")
