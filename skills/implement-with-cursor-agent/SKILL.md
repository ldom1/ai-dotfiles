---
name: implement-with-cursor-agent
description: Experimental, smoke-tested only. Execute a validated implementation plan from the Local Brain vault with Cursor CLI agents as implementers and Claude as a hard, adversarial reviewer. One headless Cursor agent per plan task (gpt-5.3-codex) runs in a container with no GitHub credentials and commits locally: code in a project clone, an implementation note (choices, gaps, deviations, verification) in a vault clone. Claude gates, challenges, sends findings back, then publishes a project PR against the integration branch and a vault PR, and squash-merges that project PR into the integration branch only (develop, or the first stage in .git-promotion.json). It never merges, pushes, or promotes onto main. Use this whenever the user says "implement with cursor", "/implement-with-cursor-agent", "hand the plan to cursor agents", "let Cursor implement and you review", or wants a vault plan executed by Cursor with Claude reviewing, even if they do not name the skill. Not for writing a plan (superpowers:writing-plans), for Claude-only execution (superpowers:subagent-driven-development), or for a release (git-promotion).
---

# Implement with Cursor agents

You are the orchestrator and the reviewer. Cursor agents implement. You never write the implementation yourself: if you fix their code, the run no longer shows whether delegation works.

**Never land project code on `main`.** Do not `gh pr merge` a project PR whose base is `main`. Do not push or fast-forward the project `main`. Do not run `promote.py` toward `main` or any later stage. A release is a separate `/git-promotion` run, and only when the user asks for one. The vault note still fast-forwards the brain default branch. That is not a project release.

## Status and evidence

**Stage: smoke-tested, on an earlier flow.** On 2026-10-12, 2 trivial tasks merged after 1 review round each ([[2026-10-12-implement-with-cursor-agent-skill]]).
- That run predates the integration-branch rule: its project PRs landed on `main`, which this version refuses.
- The current flow, which merges into the integration branch, has not run yet.
- The run shows only that nothing failed on a trivial case. It does not evaluate the kill criterion.

| Stage | Entry condition |
|---|---|
| smoke-tested | One run merged end to end. The current stage, reached on the earlier flow only. |
| evaluated | The rules in "Evaluation protocol" are met. One plan with 3 or more tasks, and at least one non-trivial task: a logic change of ~100 lines or more, a dependency between tasks, or a shared file. |
| validated | 3 evaluated plans, and no escaped high-severity defect within 14 days of each merge. |

**Kill criterion** (applies from "evaluated" on). Stop the experiment if any of these holds:
- The mean review rounds per task is above 2.
- More than 1 task in 3 escalates.
- An escaped high-severity defect appears: a defect found after merge, in code this skill merged.

**Escalation** means any of these:
- (a) A high or medium finding is still open after round 2.
- (b) Cursor fails twice on one task: a non-zero rc, a hang (`124`) or a usage limit (`75`).
- (c) Claude or the user edits a task branch by hand.
- (d) A PR ends as a draft, or with `STATUS=blocked`.
- (e) A merge precondition fails and needs a human: red local-ci, or a failed vault precondition.

**Evaluation protocol.** Decide everything before the run, so the result cannot be rationalized afterwards.
- **Pre-register.** Write an evaluation plan in the vault before the run. It fixes the failure thresholds (rounds, escalations, escaped defects) and the overhead you accept against Claude alone. It also fixes how the reviewer's value is judged.
- **Baseline.** Measure the Claude-alone baseline on the same plan, never estimate it: estimating it means choosing the result.
- **Try to falsify the reviewer.** For each finding, log whether the gate or your own pass alone would have caught it. The evaluation must be able to conclude "the fresh reviewer adds nothing".
  - The trial leans that way. Both medium findings were also caught by the orchestrator. Reviewer-only findings were 6 low.
- **Brief conformance is a safety indicator,** not a format detail. In the trial, Cursor put its status lines last in only 1 of 4 replies.
  - If the agent ignores the output format, assume it can also ignore the brief's prohibitions: no `$HOME`, no `install.sh`.
  - Report the conformance rate next to the safety results.

**What the evidence covers:**
- `test_cursor_dispatch.py` tests the mechanism only: the model pin, the limit stop, the timeout, the resume and hooks off. It proves nothing about the code Cursor writes.
- Correctness of that code rests on 2 things: the gate (failing-first tests, the full suite, CI) and the review.
- "Review passed" does not mean "correct". Record every defect found after merge as **escaped**: that is the only measure of what the procedure misses.

## 0. Preflight

Stop and report on any failure.

1. **Plan.** Expect a path under `$BRAIN_PATH/inbox/daily/plans/<project>/`. Read the whole plan. If the user has not said it is validated, ask once.
2. **Project repo.** Work from the repo root: the merge guard reads the session directory. Run `git fetch origin`. Resolve the integration branch (`$base`). Stop if you cannot. Do not fall back to `main`.
   - `.git-promotion.json` with two or more `stages`: `$base` is `stages[0]` (usually `develop`). Feature PRs merge only there. `git-promotion` fast-forwards later stages. This skill does not.
   - No config, and `origin/develop` exists: `$base` is `develop`.
   - One stage, no `origin/develop`, `$base` equal to `main`, or `$base` equal to the last stage: stop. A single-stage repo releases with `promote.py --pr`, which squash-merges onto `main`. That path is out of scope.
   - `git rev-parse --verify origin/$base` must succeed.
3. **Tools.**
   - `agent --version`
   - `agent --list-models | grep -w "${CURSOR_MODEL:-gpt-5.3-codex}"`
   - `gh auth status`
   - `git -C "$BRAIN_PATH" remote get-url origin`
4. **Merge guard.** If `git config --get local-ci.guard` prints `true`, every merge needs a fresh `~/ai-dotfiles/bin/local-ci run --event pull_request --pr <N>` success.
5. **Model.** State the model you are on (FinOps rule). Cursor runs `CURSOR_MODEL`, default `gpt-5.3-codex`. A Claude-family Cursor model removes the second-model property: say so if the user picks one.
6. **Ledger** at `$R/ledger.md`, with `R=<scratchpad>/cursor-runs/<plan-slug>`. It is the trial report, so write it for a reader. Per task and per round, record:
   - status, commit SHAs, PR URLs, model, wall time, Cursor tokens (the `usage` block of the result JSON);
   - reviewer cost. Price its transcript `~/.claude/projects/<project>/<session>/subagents/agent-<id>.jsonl`: deduplicate by message id, and use output tokens = max(recorded, characters / 4), because the recorded value undercounts ([[claude-code-patterns#^c15]]);
   - every command you ran, with its result line;
   - brief conformance: status lines last (yes or no), note sections complete, commit scopes valid;
   - every finding as `source | severity | path:line | issue | outcome`. The source is one of `gate`, `reviewer`, `orchestrator`, `author`. List all sources when several found it;
   - rulings: `Ruling: <decision> — <why> — <cost if wrong>`;
   - escalation (yes or no, with its letter from the list above);
   - post-merge result.

   In an evaluation run, also measure the baseline. Run a native Sonnet subagent on the same task in a throwaway worktree, with no PR, and record its cost and its gate result.

## 1. Schedule

- Run one Cursor agent per plan task.
- Tasks that share **any** file run in sequence. That includes `CHANGELOG.md` and `README.md`. A clean textual merge does not prove a correct combined result. The later task starts from the updated integration branch after the earlier one merges.
- Tasks with disjoint files run in parallel, at most 3. This holds only if `test_cmd` has no shared mutable state: fixed ports, a database, fixed temp paths or a shared build directory. If it does, run them in sequence.
- If a task's plan section implies more than ~400 changed lines or 10 files, one review cannot cover it. Ask the plan author to split it.

## 2. Dispatch one task

Cursor works in **clones**, not worktrees:
- A worktree shares the main repo's `.git`, so commits made inside it write into `~/ai-dotfiles/.git`.
- `--no-hardlinks` keeps the clone's objects off the main repo's inodes.
- Each clone has no remote, so it holds no path back to the host repo.

```bash
T=<n>; slug=<plan-slug>; run="$R/task$T"; br="cursor/$slug-t$T"; repo=$(git rev-parse --show-toplevel); mkdir -p "$run"
git fetch origin && base_sha=$(git rev-parse "origin/$base")
git clone -q --no-hardlinks --no-checkout "$repo" "$run/project"
git -C "$run/project" fetch -q "$repo" "refs/remotes/origin/${base}:refs/heads/$br" && git -C "$run/project" checkout -q "$br" && git -C "$run/project" remote remove origin
git -C "$BRAIN_PATH" fetch origin
git clone -q --no-hardlinks --no-checkout "$BRAIN_PATH" "$run/vault"
git -C "$run/vault" fetch -q "$BRAIN_PATH" "refs/remotes/origin/main:refs/heads/$br" && git -C "$run/vault" checkout -q "$br" && git -C "$run/vault" remote remove origin
```

Fill `references/cursor-brief.md` into `$run/brief.md`. Use **container paths**:
- `project_dir`: `/work/project`
- `vault_dir`: `/work/vault`
- `plan_path`: `/work/vault/<plan path inside the vault>`

The other placeholders:
- `task_text`: paste the task section verbatim.
- `note_rel`: `inbox/daily/checkpoints/<project>/<date>-<slug>-task<T>.md`
- `note_slug`: the same filename without `.md`.
- `vault_commit`: `doc(inbox): add cursor note for <slug> task <T>`
- `scopes`: the locked list for this repo's type in `~/ai-dotfiles/skills/git-commit/scopes.json`.
- `base`: the integration branch from preflight. Never `main`.
- `test_cmd`: the plan's global test command, or the repo's CI test command.

Run Cursor in the background (Bash `run_in_background: true`), then wait for the notification:

```bash
bash ~/ai-dotfiles/skills/implement-with-cursor-agent/scripts/run-cursor.sh "$run" "$run/brief.md"
```

What the script does:
- **Container.** It runs Cursor in `local-ci-runner:24.04`. The container sees only `$run`, mounted at `/work`, plus the host's Cursor CLI and `uv`, both read-only.
- **Credentials.** The container gets no GitHub credentials. It gets the Cursor API key by variable name only.
  - The key comes from `CURSOR_API_KEY` or from `~/.config/cursor-agent/api-key` (mode 600).
  - Without a key, the script stops with `rc=4`.
- **Timeout.** It removes a container that hangs, after 30 minutes (`rc=124`).
- **Usage limit.** On a credit or usage-limit error, it stops with `rc=75` and does not switch models: `auto` can route to a Claude model. Ask the user before you rerun with another `CURSOR_MODEL`.
- **State.** Cursor's state lives in `$run/home`, so a resume works.

**Confinement.** The container replaces Cursor's own `--sandbox`, which enforced nothing in the canary test. Cursor still runs with `--force`, but only inside the container: it cannot see your home, `~/ai-dotfiles` or `/mnt/c`. What stays exposed:
- the 2 task clones;
- the Cursor API key;
- open network access. Cursor can send out what it sees. It cannot push, because it has no credentials.

## 3. Review

Assume the work is wrong until evidence shows otherwise. The note and the final reply are claims, not evidence.

### 3a. Gate: run commands before you read any prose

Everything in this section runs on the host, on Cursor's **local** commits. Nothing reaches GitHub before step 4.

1. `tail -1 $run/runs.log`:
   - `rc=124` is a hang. `rc=75` is a usage limit. `rc=4` is a missing API key.
   - Any non-zero rc means the attempt failed. Count it toward escalation (b).
2. Grep `PROJECT_HEAD=`, `VAULT_HEAD=` and `STATUS=` in the result JSON's `result` field.
   - If they are not the last 3 lines, record a brief non-conformance; do not hide it.
   - Each value must equal `git -C "$run/project" rev-parse HEAD` and `git -C "$run/vault" rev-parse HEAD`.
3. In `$run/project`:
   - Run `test_cmd` yourself, and read the pass and skip counts (^v3).
   - Run `git diff --stat "$base_sha...HEAD"`. A file outside the task's file list is a scope finding.
   - In the vault clone, `git -C "$run/vault" log --stat "$br" --not "$(git -C "$BRAIN_PATH" rev-parse origin/main)"` must show only the note file.
4. **Negative control** (^v5): the new tests must fail without the change, for the right reason.
   - Use a temporary worktree at `origin/$base`. Copy into it only the test files the branch adds or changes, plus any fixture files the branch adds next to them.
   - Run **only those test files**, not the global command.
   - **Pass:** the new tests fail with assertion failures, or with the exact error the feature removes.
   - **Inconclusive:** an import, collection or missing-file error. This is common when the test imports a module the branch creates. It is not a pass: record a Ruling and judge it by reading the test.
   - **Sensor task** (a check of state that is already correct): it passes on base by design. Seed one mutation that the sensor must catch, see it fail, then revert.
   - Remove the temporary worktree afterwards.
5. **CI.** Run the repo's CI steps by hand on `$run/project`. In a guarded repo, `local-ci` runs again on the published PR (step 5). The hook suite does not catch everything: a CI step once caught stale generated files that the tests missed.
6. **Note.**
   - All sections are present.
   - `[[wikilinks]]`, not paths.
   - Its Verification counts match what you just ran.

### 3b. Challenge

1. **Fresh reviewer first,** before your own pass, so it cannot align with your view.
   - Dispatch the `reviewer` agent with `model: opus`. Give it the plan task text, `git -C "$run/project" diff "$base_sha...HEAD"` and the note. Do not give it your findings or opinions.
   - Ask for `VERDICT: APPROVE|REJECT` and findings as `path:line severity issue — expected`.
   - Save its reply unedited to `$run/review-<round>.md`.
   - Run it again on every round that fixed a high or medium finding.
   - If it has not returned after ~15 minutes, treat it as failed and dispatch it once more.
2. **Your own pass,** step by step against the plan:
   - Is every step done, and does a test prove it?
   - Hidden requirements: `CHANGELOG.md`, `README.md`, generated files, CI checks.
   - The plan's edge cases, error paths, and fail-open or fail-closed behaviour.
   - Each **Choice**: would you have accepted it in a design review?
   - Each **Gap**: can it merge with that gap? A gap the note hides is a high finding.
   - **Deviations**: is each one justified, or is it a silent change of scope?
3. **Verify every finding yourself** at its `path:line` before you send it. Drop a finding you cannot reproduce, with the evidence, as a Ruling. Record the source of each finding. The reviewer's cost is justified only by findings the gate, you or the author did not already catch.

### 3c. Verdict

- **APPROVE** when no high or medium finding is left, and the gate is green.
- **CHANGES** otherwise. Write numbered findings to `$run/findings-<round>.md`, one per line: `<path:line> — <severity> — <issue> — <expected>`. Then resume the same Cursor session:
  ```bash
  bash ~/ai-dotfiles/skills/implement-with-cursor-agent/scripts/run-cursor.sh "$run" "$run/findings-<round>.md" resume
  ```
  Re-run the full gate on the new commits. Allow at most 2 rounds per task. If a task still fails after round 2, it escalates (a): stop it and report it with the ledger. Do not fix the code yourself.

## 4. Publish, after APPROVE only

Claude publishes from the host, with your `gh`. The pushed heads must be the heads you reviewed.

```bash
git fetch -q "$run/project" "$br:$br" && test "$(git rev-parse "$br")" = "<reviewed PROJECT_HEAD>" && git push -u origin "$br"
gh pr create --base "$base" --head "$br" --title "<subject>" --body-file "$run/pr-body.md"
git -C "$BRAIN_PATH" fetch -q "$run/vault" "$br:$br" && test "$(git -C "$BRAIN_PATH" rev-parse "$br")" = "<reviewed VAULT_HEAD>" && git -C "$BRAIN_PATH" push -u origin "$br"
gh pr create -R <vault owner/repo> --base main --head "$br" --title "<vault_commit>" --body "Implementation note for <subject>"
```

- `pr-body.md` holds the note's Summary and Gaps, then `Note: [[<note_slug>]]`.
- The PR base must be `$base`. If it is `main`, or the last stage in `.git-promotion.json`, stop and leave the PR open.

## 5. Land on the integration branch, in plan order

**Project PR.**

1. Check `gh pr view <N> --json mergeable,mergeStateStatus,baseRefName`. `UNKNOWN` means GitHub is still computing: wait a few seconds and ask again.
   - `CONFLICTING`:
     1. Bring the new base into the clone: `git -C "$run/project" fetch -q "$repo" "+refs/remotes/origin/${base}:refs/heads/new-base"`.
     2. Resume Cursor with "rebase `{branch}` onto `new-base`, resolve the conflicts, run the tests, commit".
     3. Re-run the gate, then `git fetch -q "$run/project" "+$br:$br" && git push --force-with-lease origin "$br"`.
   - Behind but clean: test the combined state. `local-ci` tests the PR merge ref. For tests CI does not run, merge the branch into a temporary worktree at `origin/$base`, run `test_cmd` there, and remove the worktree.
2. In a guarded repo, run `~/ai-dotfiles/bin/local-ci run --event pull_request --pr <N>` on the final head.
3. Run `/git-commit` to build the squash subject. Append ` (#<N>)`, as in the repo history.
4. From the repo root, run `gh pr merge <N> --squash --delete-branch --subject "<subject>"`. Do not use `-R`, `cd`, or `--admin`. This lands on `$base` only. The local branch `$br` is not checked out anywhere, so `--delete-branch` removes it locally and on the remote.
5. Update the local integration branch: `git fetch origin && git merge --ff-only "origin/$base"`. `git pull` fails when `pull.rebase` is set and other sessions have uncommitted work in the checkout. Do not check out or update `main`.
6. **Post-merge check:** run `test_cmd` on `$base` and record the result. Record any later defect in this code as escaped.
7. **Stop there.** Do not promote. Do not run `~/ai-dotfiles/skills/git-promotion/scripts/promote.py`. Tell the user `$base` moved. A later stage (`preprod`, `main`) is `/git-promotion`, and only if the user asks.

**Vault PR: not an independent gate.**
- Claude reviews the note, and Claude merges it.
- The preconditions below *require* that no server-side protection exists: the flow is built on the absence of an independent check.
- This is acceptable only because the vault PR carries a documentation note, not code. Never present it as a second review.

The PR is the review record for the note. It lands on the brain default branch. That push does not move the project `main`. The merge does not go through `gh pr merge`: the merge guard denies a merge aimed at another repo. Instead:

1. **Review record.** Write the note verdict to `$run/vault-review.md`: sections checked, Verification counts matched, findings. Post it with `gh pr comment <VAULT_PR url> --body-file "$run/vault-review.md"`. You cannot approve your own PR, because Claude opens it under your GitHub account, so the comment is the record.
2. **Preconditions.** All must hold. Otherwise stop, and give the PR to the user to merge in the web UI.
   - The vault repo has no branch protection, ruleset or required check. `gh api repos/<owner>/<repo>/branches/main/protection` must return 404, or 403 "Upgrade to GitHub Pro" on a free private repo, where none can exist. Verified for `ldom1/developer-brain` on 2026-10-12.
   - `gh pr view <url> --json headRefOid` equals the SHA you reviewed.
   - `gh pr view <url> --json files` lists only the note file.
3. **Merge.** Fast-forward only. Retry at most 3 times if `main` moves:
   ```bash
   for i in 1 2 3; do
     git -C "$BRAIN_PATH" fetch origin || break
     if ! git -C "$BRAIN_PATH" merge-base --is-ancestor origin/main "$br"; then   # main moved: rebase in the clone, not in the vault tree
       git -C "$run/vault" fetch -q "$BRAIN_PATH" "+refs/remotes/origin/main:refs/heads/upstream" && git -C "$run/vault" rebase -q upstream "$br" \
         && git -C "$BRAIN_PATH" fetch -q "$run/vault" "+$br:$br" && git -C "$BRAIN_PATH" push -q --force-with-lease origin "$br" || break
       # the rebase must not change the note: compare `git -C "$run/vault" diff upstream "$br"` with the reviewed note
     fi
     git -C "$BRAIN_PATH" merge --ff-only "$br" && git -C "$BRAIN_PATH" push origin main && ok=1 && break
   done
   ```
   - If `ok` is not set after 3 tries, stop and report.
   - Do not pre-check `index.lock`: that check races. Git takes the lock itself and fails atomically ("Another git process seems to be running"). Treat that failure as a stop, and retry later.
   - Then run `git -C "$BRAIN_PATH" push origin --delete "$br"`. GitHub marks the PR merged, because its commits are now on `main`.

**Clean up:** `git -C "$BRAIN_PATH" branch -D "$br"`, then delete `$run`. It holds the 2 clones and the container's home, which keeps Cursor's session.

## 6. Close

1. Report the ledger to the user. Per task: rounds, findings by source and severity, model, wall time, cost, conformance, merged PR links. Before the "evaluated" stage, never say the kill criterion passed. Say "smoke run: no failure signal".
2. Run `/capture`. The session log links each note as `[[<note_slug>]]`. These notes stay in `checkpoints/`: they are not the PreCompact `<date>.md` file that `/capture` deletes.

## Safety

- Base every safety check on raw values: exit codes, hashes, and paths compared inside the command. Never base one on displayed text. The RTK Bash hook rewrites command output, even when you redirect it to a file. For example, `diff` printed `[ok] Files are identical` in the trial. Use `rtk proxy '<cmd>'` when you must read output.
- Before and after each Cursor run, record these values. They must match:
  - `readlink -f ~/.claude ~/.cursor/hooks.json | md5sum`, and each path must start with `$HOME/ai-dotfiles/`. Check that with `case` or `grep -c`, using the exit code.
  - `git -C ~/ai-dotfiles status --porcelain | md5sum`
  - `git -C "$BRAIN_PATH" rev-parse HEAD`
  - Nothing else on the host should change: Cursor sees only `$run`. A change elsewhere means the container boundary failed. Stop the plan.
- Confinement is the container (step 2), not hooks and not Cursor's `--sandbox`. Keep the host checks above as a second line: they detect a failed boundary, they do not prevent one.
- Never merge on a red gate, a stale local-ci status or an unverified claim.
- Never merge, push, or fast-forward the project `main`. A project PR whose base is `main` stays open.
- Stop and ask before anything irreversible beyond these PRs: a force push to `main` or to `$base`, a branch you did not create, a deleted file outside the task.

## Open issues: blockers, in this order

1. **Sandbox first (closed by the container, 2026-10-12).** Without confinement, `--force` is the main risk of this skill: an evaluation run would expose the real repo and the shared vault for hours.
   - **Tested 2026-10-12, result FAIL.** Setup: Cursor CLI 2026.10.01, WSL2 kernel 6.18 with Landlock ABI 7, a canary prompt, ground truth checked on disk.
   - With `--sandbox enabled`, Cursor *requested* the policy `TYPE_WORKSPACE_READWRITE`, but did not enforce it. These writes all landed: `$HOME`, `~/ai-dotfiles/.git`, the vault's `.git`, and a file-tool write into `~/ai-dotfiles`. The result was the same with and without `--force`.
   - `git push` and `gh pr create` worked.
   - The control run, with `--sandbox disabled`, gave identical results. So Cursor's own sandbox gives no confinement here.
   - **Fix, 2026-10-12:** a container (step 2, `run-cursor.sh`). It mounts only `$run`, reuses the host's Cursor CLI read-only, and holds no GitHub credentials.
     - Checked by hand: the host's `~/ai-dotfiles` and `/mnt/c` are invisible inside it, and a write into `/home/lgiron` fails.
     - **Canary re-run through `run-cursor.sh`, 2026-10-12: PASS.** The criteria were written before the run, and the ground truth was checked on the host.
       - Shell writes to `$HOME`, `~/ai-dotfiles/.git` and the vault's `.git` failed, and so did a file-tool write into `~/ai-dotfiles/.git`. No target exists on the host.
       - Writes into `/work/project` and `/work/vault` landed, and a local commit worked.
       - `~/.config/gh/hosts.yml` was not visible. `git push` failed with no credentials, and the remote branch does not exist.
       - The Cursor API answered (`gpt-5.3-codex`, 40 s). The host's symlinks, the `ai-dotfiles` status and the vault HEAD did not change.
     - Not covered: the network stays open (the container reached `api.github.com`), and the API key is visible inside the container.
2. **Hook origin, in the same investigation.** Claude's commit-scope check fired inside Cursor, from an unknown source.
   - If Cursor loads `~/.claude` or `~/ai-dotfiles` config through symlinks, other hooks may also run with Cursor's rights. "Brain hooks off" may then be only half true.
   - Find the mechanism, and list every hook that runs inside Cursor.
3. **Merge-guard false positives.** `local-ci-merge-guard.py` denied Bash calls that only *mentioned* a merge, 3 times in one session. Make it match the parsed command, not the text, before an evaluation run multiplies the blocks. Repeated workarounds end with someone turning the guard off.
4. **Evaluation run,** in a repo with an integration branch, under the "Evaluation protocol" above.
