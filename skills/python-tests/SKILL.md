---
name: python-tests
description: Write or fix Python code test-first — red, green, full suite, lint, mutation check, CHANGELOG. Use when the user asks to fix a bug with a test, to add or write tests, or to do TDD, including "corrige … avec un test", "corrige-le avec un test", "écris un test", "ajoute des tests", "test qui échoue", "fix this with a test", "write a failing test". Not for JavaScript or shell tests.
---

# python-tests

Goal: each new test fails before the change, passes after it, and kills at least one mutant of the changed code.

## Steps

1. **Find the commands.** Read `pyproject.toml`, `Makefile` and `.github/workflows/`. Use the exact test and lint commands of CI. Without CI, use `.venv/bin/python -m pytest`, `.venv/bin/ruff check`, `.venv/bin/ruff format --check`, and `.venv/bin/mypy <package>` if mypy is configured.
2. **Red.** Write the test first. Name it after the bug or the spec line. Run only that test and read the failure. It must be an assertion failure or the exact error that the change removes. An import error is not red.
3. **Green.** Write the smallest change that makes the test pass. Run the test again.
4. **Full suite.** Run the full test command. Read the pass, fail and skip counts. A skip that CI does not have is a failure.
5. **Lint.** Run each lint command from step 1. Fix each error that your change caused.
6. **Mutation check.** Run this command. `--lines` covers the lines you changed:

   ```bash
   .venv/bin/python ~/ai-dotfiles/skills/python-tests/scripts/mutate.py \
     --source <changed file> --lines <first>-<last> \
     --test <new test node id>
   ```

   Repeat `--test` for each new test. Exit 0 means each new test killed a mutant. Exit 1 means a test killed none, so it does not check the change. Make that test assert the changed behaviour, then run step 6 again. Do not mutate files by hand.
7. **CHANGELOG.** If behaviour changed, add a line under `## [Unreleased]` in `CHANGELOG.md`.

## Rules

- Wrong behaviour outside the task: add a test with `@pytest.mark.xfail(strict=True, reason="<bug>")` and report it. Do not fix it.
- Database: use a real local database, not a mock.
- External API: use a fake built from a real recorded response. Never invent a field.
- Do not write a test that cannot fail (`assert x or True`), a test that repeats another test, or a test that locks in a bug.

## Definition of done

Deterministic (a command proves it):
1. Each new test was red before it was green.
2. The full suite is green, and its skips equal the skips of CI.
3. Lint is green.
4. `mutate.py` exits 0.
5. `CHANGELOG.md` changed if behaviour changed.

Judged (read the diff):
6. Each test name points to its bug or spec line.
7. No test locks in a wrong behaviour.
