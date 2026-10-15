#!/usr/bin/env python3
"""Check that each named test kills at least one mutant of a source file.

Usage:
  mutate.py --source pkg/mod.py --test tests/test_mod.py::test_a [--test ...]
            [--lines 10-25] [--pytest "python -m pytest"] [--timeout 60] [--max-mutants 200]

The source file is mutated in place, one mutant at a time, and restored at the end.
Exit 0: every test killed a mutant. 1: a test killed none.
2: usage error, failing baseline, or a leftover backup file.
"""
from __future__ import annotations

import argparse
import ast
import os
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterator, NamedTuple


class Mutant(NamedTuple):
    lineno: int
    desc: str
    source: str


SWAP_CMP = {
    ast.Eq: ast.NotEq,
    ast.NotEq: ast.Eq,
    ast.Lt: ast.GtE,
    ast.GtE: ast.Lt,
    ast.Gt: ast.LtE,
    ast.LtE: ast.Gt,
    ast.In: ast.NotIn,
    ast.NotIn: ast.In,
    ast.Is: ast.IsNot,
    ast.IsNot: ast.Is,
}
SWAP_BIN = {
    ast.Add: ast.Sub,
    ast.Sub: ast.Add,
    ast.Mult: ast.Div,
    ast.Div: ast.Mult,
    ast.FloorDiv: ast.Div,
    ast.Mod: ast.Mult,
}
STATUS = {"PASSED": True, "XFAIL": True, "FAILED": False, "ERROR": False, "XPASS": False}
TIMEOUT = "timeout"


def _set(obj: ast.AST, attr: str, value: object) -> Callable[[], None]:
    return lambda: setattr(obj, attr, value)


def _is_unescaped(value: str, index: int) -> bool:
    backslashes = 0
    j = index - 1
    while j >= 0 and value[j] == "\\":
        backslashes += 1
        j -= 1
    return backslashes % 2 == 0


def _node_sites(node: ast.AST, regex_args: set[int], docstrings: set[int]) -> Iterator[tuple[str, Callable[[], None]]]:
    if isinstance(node, ast.Compare):
        for i, op in enumerate(node.ops):
            new = SWAP_CMP.get(type(op))
            if new:
                ops = list(node.ops)
                ops[i] = new()
                yield f"{type(op).__name__} -> {new.__name__}", _set(node, "ops", ops)
    elif isinstance(node, ast.BinOp) and type(node.op) in SWAP_BIN:
        new = SWAP_BIN[type(node.op)]
        yield f"{type(node.op).__name__} -> {new.__name__}", _set(node, "op", new())
    elif isinstance(node, ast.BoolOp):
        new = ast.Or if isinstance(node.op, ast.And) else ast.And
        yield f"{type(node.op).__name__} -> {new.__name__}", _set(node, "op", new())
    elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
        yield "drop not", _set(node, "operand", ast.UnaryOp(ast.Not(), node.operand))
    elif isinstance(node, (ast.If, ast.While)):
        yield "negate condition", _set(node, "test", ast.UnaryOp(ast.Not(), node.test))
    elif isinstance(node, ast.Return) and node.value is not None and not (
        isinstance(node.value, ast.Constant) and node.value.value is None
    ):
        yield "return None", _set(node, "value", ast.Constant(None))
    elif isinstance(node, ast.Constant) and id(node) not in docstrings:
        value = node.value
        if isinstance(value, bool):
            yield f"{value} -> {not value}", _set(node, "value", not value)
        elif isinstance(value, (int, float)):
            yield f"{value} -> {value + 1}", _set(node, "value", value + 1)
        elif isinstance(value, str):
            new = "" if value else "mutant"
            yield f"{value!r} -> {new!r}", _set(node, "value", new)
            if id(node) in regex_args:
                for i, char in enumerate(value):
                    if char not in "+*?" or not _is_unescaped(value, i):
                        continue
                    if char == "?" and i > 0 and value[i - 1] == "(" and _is_unescaped(value, i - 1):
                        continue
                    yield f"regex {value!r}: drop {char!r} at {i}", _set(node, "value", value[:i] + value[i + 1 :])


def _collect(tree: ast.AST, lines: set[int] | None) -> list[tuple[int, str, Callable[[], None]]]:
    regex_args = {
        id(n.args[0])
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        and n.args
        and isinstance(n.func, ast.Attribute)
        and isinstance(n.func.value, ast.Name)
        and n.func.value.id == "re"
    }
    docstrings = {
        id(n.value)
        for n in ast.walk(tree)
        if isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant) and isinstance(n.value.value, str)
    }
    sites = []
    for node in ast.walk(tree):
        line = getattr(node, "lineno", None)
        if line is None or (lines and line not in lines):
            continue
        sites.extend((line, desc, apply) for desc, apply in _node_sites(node, regex_args, docstrings))
    return sites


def generate_mutants(source: str, lines: set[int] | None = None) -> list[Mutant]:
    mutants = []
    base_sites = _collect(ast.parse(source), lines)
    for k in range(len(base_sites)):
        tree = ast.parse(source)
        line, desc, apply = _collect(tree, lines)[k]
        apply()
        mutants.append(Mutant(line, desc, ast.unparse(tree) + "\n"))
    return mutants


def _outcomes(cmd: list[str], tests: list[str], timeout: int) -> dict[str, bool] | str | None:
    """Map node id -> passed. TIMEOUT on timeout. None when pytest did not run the tests."""
    env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    try:
        proc = subprocess.run(
            [*cmd, "-q", "-rA", "-p", "no:cacheprovider", *tests],
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except subprocess.TimeoutExpired:
        return TIMEOUT
    if proc.returncode not in (0, 1):
        return None
    outcomes = {}
    for line in proc.stdout.splitlines():
        word, _, rest = line.partition(" ")
        if word in STATUS and rest:
            outcomes[rest.split(" - ")[0].strip()] = STATUS[word]
    return outcomes


def _parse_lines(specs: list[str]) -> set[int] | None:
    lines: set[int] = set()
    for spec in specs:
        first, _, last = spec.partition("-")
        lines.update(range(int(first), int(last or first) + 1))
    return lines or None


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check that each test kills at least one mutant.")
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--test", action="append", required=True, help="pytest node id or test file")
    parser.add_argument("--lines", action="append", default=[], help="N or A-B; repeatable")
    parser.add_argument("--pytest", default=f"{shlex.quote(sys.executable)} -m pytest")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-mutants", type=int, default=200)
    args = parser.parse_args(argv)

    source: Path = args.source
    backup = source.with_name(source.name + ".mutate-orig")
    if not source.is_file():
        print(f"error: {source} is not a file", file=sys.stderr)
        return 2
    if backup.exists():
        print(f"error: {backup} exists: restore it to {source.name} or delete it", file=sys.stderr)
        return 2

    original = source.read_bytes()
    backup.write_bytes(original)
    try:
        cmd = shlex.split(args.pytest)
        try:
            normalized = ast.unparse(ast.parse(original.decode("utf-8"))) + "\n"
            selected_lines = _parse_lines(args.lines)
            all_mutants = generate_mutants(normalized, selected_lines)
        except (SyntaxError, UnicodeDecodeError, ValueError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2

        source.write_text(normalized, encoding="utf-8")
        base = _outcomes(cmd, args.test, args.timeout)
        if not isinstance(base, dict) or not base or not all(base.values()):
            print("error: baseline: the tests must all pass on the unmutated source", file=sys.stderr)
            return 2

        dropped = max(0, len(all_mutants) - args.max_mutants)
        if dropped:
            print(f"note: {dropped} mutants dropped by --max-mutants; narrow --lines", file=sys.stderr)
        mutants = all_mutants[: args.max_mutants]
        if not mutants:
            print("error: no mutation site in the selected lines", file=sys.stderr)
            return 2

        kills = {test: 0 for test in base}
        valid = invalid = 0
        for mutant in mutants:
            source.write_text(mutant.source, encoding="utf-8")
            result = _outcomes(cmd, args.test, args.timeout)
            if result is None:
                invalid += 1
                print(f"invalid  L{mutant.lineno} {mutant.desc}")
                continue
            valid += 1
            killed = [test for test in base if result == TIMEOUT or result.get(test) is False]
            for test in killed:
                kills[test] += 1
            if killed:
                print(f"killed   L{mutant.lineno} {mutant.desc} ({', '.join(killed)})")
            else:
                print(f"survived L{mutant.lineno} {mutant.desc}")
    finally:
        source.write_bytes(original)
        if backup.exists():
            backup.unlink()

    print(f"mutants: {valid} valid, {invalid} invalid")
    for test, count in kills.items():
        print(f"{test}\tkilled {count}/{valid}")
    weak = [test for test, count in kills.items() if count == 0]
    for test in weak:
        print(f"FAIL {test}: killed no mutant")
    return 1 if weak else 0


if __name__ == "__main__":
    sys.exit(main())
