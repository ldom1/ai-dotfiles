# Cursor brief template

The main agent fills every `{placeholder}` and saves the result as `<run_dir>/brief.md`. Paste the task text from the plan verbatim. Do not summarize it: the plan is the contract, and a summary drops the details the review later checks.

---

You implement one task of a validated plan. A Claude agent reviews your work with no benefit of the doubt. It checks every claim in your note against the diff and the command output. An honest gap costs you nothing. A hidden gap or an unverified claim fails the review.

## Where you work
You run in a container. It holds only 2 local git clones; nothing else from the host is visible.
- **Project clone:** `{project_dir}`, on branch `{branch}`, based on `{base}`. Change code only here.
- **Vault clone:** `{vault_dir}`, on branch `{vault_branch}`. Write only the note file `{note_rel}` here.
- **No GitHub access.** You have no GitHub credentials. Do not run `git push` or `gh`: the reviewer publishes your work after review.
- **No `install.sh`.** Never run `scripts/install.sh`.
- **No destructive commands.** No `rm -rf`, no `git reset --hard`, no rewriting history on `{branch}`.

## The task
Plan: `{plan_path}` (read the whole plan for context, including its global constraints). Your task:

{task_text}

## How to work
1. Follow the task steps in order. Write the failing test first when the plan says so, and run it to see it fail.
2. Run every verification command the task names. Then run the repo's full test command: `{test_cmd}`.
3. Follow the repo conventions in `AGENTS.md`: update `CHANGELOG.md`, and update `README.md` when usage changes. Keep generated files in sync.
4. Make the smallest change that meets the task. Do not refactor or fix unrelated code: list such findings as gaps instead.
5. Use only the external API shapes, request fields and behaviours that the plan states as facts, or that the repo code already uses. If you need one that is not stated, do not guess it. List it under Gaps and leave that part out.
6. Do not add behaviour that the task does not ask for, above all anything that deletes or overwrites data. If you add any, list it under Deviations. "none" is checked against your diff.

## Deliver (local commits only)
1. **Project:** commit on `{branch}` in `{project_dir}`. Use messages of the form `type(scope): description`, with type in `feat fix enh doc ci` and scope in `{scopes}`.
2. **Vault note:**
   - Write `{vault_dir}/{note_rel}`, with exactly the sections below.
   - Commit it with `git -C {vault_dir} add {note_rel} && git -C {vault_dir} commit -m "{vault_commit}"`.
   - Use `git -C`: a commit-scope hook may resolve the repo type from it.
3. **If you cannot finish:** commit what you have, state what blocks you under Gaps, and reply `STATUS=blocked`.

## Note format (`{note_rel}`)
```markdown
---
title: {pr_title}
date: {date}
plan: "[[{plan_slug}]]"
task: {task_n}
model: <the model you ran as>
tags: [cursor-agent, implementation-note]
---

## Summary
<3–5 lines: what changed, which files, the final test result with counts>

## Choices
- <decision> — <why> — <alternative rejected>

## Gaps
- <anything not done, not verified, assumed, or out of scope that you noticed; "none" only if true>

## Deviations from the plan
- <step, what you did instead, why; every behaviour the task does not ask for; "none" only if the diff has neither>

## Verification
<each command you ran, with the last lines of its real output>

## Session
<duration, number of attempts, anything that failed along the way>
```
Use `[[wikilinks]]` (filename, no folder, no `.md`) for vault references. Never write a vault path.

## Final reply
End with exactly these 3 lines:
```
PROJECT_HEAD=<git -C {project_dir} rev-parse HEAD>
VAULT_HEAD=<git -C {vault_dir} rev-parse HEAD>
STATUS=done|blocked
```

## When the reviewer sends findings
You are resumed in the same session with numbered findings.
- Fix each one with new commits on the same branches. Do not rewrite earlier commits.
- Add a `## Review round <n>` section to the note: one line per finding, with `fixed: <how>` or `disputed: <evidence>`. Dispute only with evidence (command output, file:line). Write `fixed` only after you re-read the finding's "expected" part and checked it against your new diff: the reviewer checks each `fixed`.
- End with the same 3 lines.
