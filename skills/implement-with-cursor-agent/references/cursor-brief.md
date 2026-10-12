# Cursor brief template

The main agent fills every `{placeholder}` and saves the result as `<run_dir>/brief.md`. Paste the task text from the plan verbatim. Do not summarize it: the plan is the contract, and a summary drops the details the review later checks.

---

You implement one task of a validated plan. A Claude agent reviews your work with no benefit of the doubt. It checks every claim in your note against the diff and the command output. An honest gap costs you nothing. A hidden gap or an unverified claim fails the review.

## Where you work
- Project checkout: `{project_dir}` (git worktree on branch `{branch}`, based on `{base}`). Change code only here.
- Vault checkout: `{vault_dir}` (git worktree on branch `{vault_branch}`). Write only the note file `{note_rel}` here.
- Do not touch any other path: not `$HOME`, not `~/ai-dotfiles`, not the main vault at `$BRAIN_PATH`.
- Never run `scripts/install.sh`, and never run destructive commands (`rm -rf`, `git reset --hard`, `git push --force`) outside these two checkouts.

## The task
Plan: `{plan_path}` (read the whole plan for context, including its global constraints). Your task:

{task_text}

## How to work
1. Follow the task steps in order. Write the failing test first when the plan says so, and run it to see it fail.
2. Run every verification command the task names. Then run the repo's full test command: `{test_cmd}`.
3. Follow the repo conventions in `AGENTS.md`: update `CHANGELOG.md`, and update `README.md` when usage changes. Keep generated files in sync.
4. Make the smallest change that meets the task. Do not refactor or fix unrelated code: list such findings as gaps instead.

## Deliver
1. Project PR:
   - Commit on `{branch}`. Use messages of the form `type(scope): description`, with type in `feat fix enh doc ci` and scope in `{scopes}`.
   - Run `git push -u origin {branch}`.
   - Run `gh pr create --base {base} --head {branch} --title "{pr_title}" --body-file <tmp file>`. `{base}` is the integration branch. Never pass `main`. The body holds the note's Summary and Gaps sections, then the line `Note: [[{note_slug}]]`.
2. Vault note: write `{vault_dir}/{note_rel}` with exactly the sections below.
   - Commit it with `git -C {vault_dir} add {note_rel} && git -C {vault_dir} commit -m "{vault_commit}"`. Use `git -C`: the commit-scope hook resolves the repo type from `-C`, and from the project directory it rejects the vault scope.
   - Run `git -C {vault_dir} push -u origin {vault_branch}`.
   - Run `gh pr create --base main --head {vault_branch} --title "{vault_commit}" --body "Implementation note for {pr_title}"` from `{vault_dir}`.
3. If you cannot finish, still deliver both PRs as drafts (`--draft`), and state what blocks you under Gaps.

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
- <step, what you did instead, why; "none" if none>

## Verification
<each command you ran, with the last lines of its real output>

## Session
<duration, number of attempts, anything that failed along the way>
```
Use `[[wikilinks]]` (filename, no folder, no `.md`) for vault references. Never write a vault path.

## Final reply
End with exactly these 3 lines:
```
PROJECT_PR=<url>
VAULT_PR=<url>
STATUS=done|blocked
```

## When the reviewer sends findings
You are resumed in the same session with numbered findings. Fix each one on the same branches and push again; do not open new PRs. Add a `## Review round <n>` section to the note: one line per finding with `fixed: <how>` or `disputed: <evidence>`. Dispute only with evidence (command output, file:line). End with the same 3 lines.
