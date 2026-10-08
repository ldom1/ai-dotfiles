# Changelog

## [Unreleased]

### Added
- `bin/local-ci`: runs a repo's listed GitHub workflows locally with `act` v0.2.89 in `local-ci-runner:24.04`, on a clean clone of one commit. Spec: vault `2026-10-07-local-ci-replication-design` (rev 5).
  - `local-ci install --workflows ci.yml` adds a `pre-push` hook. A push to a deploy branch (`main`, `preprod`) runs the `full` tier. Other branches run the `fast` tier, which is partial and never a merge gate.
  - A push run keeps a local record only (`~/.cache/local-ci/<owner>__<repo>/results.jsonl`). GitHub returns 422 for a status on a commit it does not have.
  - `local-ci run --event pull_request --pr N` tests the merge commit. It posts `local-ci/pull_request`: `pending`, then always `success` or `failure`.
  - A `pull_request` run that already passed re-posts its `success` status. A failed final status post exits non-zero.
  - Skip counts above the recorded baseline fail the run. The run reads skip counts from pytest summaries with or without `=` padding (`pytest -q`).
  - A fast-tier `fast-jobs` list that matches no job fails.
- `docker/ci-runner.Dockerfile` and `docker/ci-runner.manifest`: a slim runner image (Node, Git, Git LFS, GitHub CLI and jq at the versions of `actions/runner-images` `ubuntu24/20261004.327`). `scripts/build-ci-runner.sh` checks every version. `scripts/install-act.sh` installs `act` after a checksum check.
  - The image builds git with `NO_RUST=1` and installs gh with `--ignore-depends=git`, because git comes from source.
- `.claude/hooks/local-ci-merge-guard.py`: denies a Claude `gh pr merge` unless the PR head has a fresh `local-ci/pull_request` success. Fresh means same base tip, same image and the `gh` user as creator. It is off until `git config local-ci.guard true`. It guards only merges run by Claude Code.
  - The guard denies a `gh pr merge` it cannot parse (subshell, `bash -c`, `sudo`, `$(...)`, unbalanced quotes).
  - It denies a `cd` or `pushd` before the merge, `-R`, `--repo` or `GH_REPO` for another repo, and any error.
- Template `permissions.deny`: `git push --no-verify` for Claude.
- `scripts/check-ci-runner-drift.sh`: SessionStart prints one warning when the runner manifest differs from the latest `ubuntu24` release. It caches for 7 days and never edits the manifest.

### Fixed
- `bin/local-ci`: an interrupt (SIGINT, SIGTERM, SIGHUP) now removes every `act-*` container and network before exit.
- `bin/local-ci`: a second signal during cleanup is ignored, so the `failure` status is always posted. `uv run` forwards SIGINT, so Ctrl-C and `timeout -s INT` send two.
- `bin/local-ci`: a `pull_request` run checks out submodules after the merge, so it tests the merge commit's submodule commits.
- `bin/local-ci`: the "already passed" record now also matches the ref, the `workflows` list and, for the fast tier, `fast-jobs`.
  - A push run needs `--ref refs/heads/<branch>`. A `pull_request` run uses `refs/pull/<N>/merge`.
- `bin/local-ci`: the skip baseline key is `<workflow>/<job>@<ref>` (`@pull_request` for PR runs). A plain `<workflow>/<job>` key is the fallback.
- `bin/local-ci`: it ignores `GIT_DIR` and related variables, so `git --git-dir=… push` cannot move the source repo's HEAD.
- `bin/local-ci`: a run with no job left after filtering fails with "no job to run".
- Merge guard: in every directory, it denies a merge with `-R`/`GH_REPO` for another repo or a `cd` before it.
- Merge guard: in every directory, it denies a merge through `gh api` (`pulls/<N>/merge` or the GraphQL merge mutation).
- Merge guard: a crash on bad input denies when the input looks like a merge. A status response without `total_count` denies.
- `scripts/check-ci-runner-drift.sh`: the `gh` call stops after 5 s, so SessionStart cannot hang.
- Merge guard: it reads the status creator from `commits/<sha>/statuses` (entry with the same `id`). The combined status has no `creator`, so every success was denied.
- `scripts/install-act.sh`: it creates `~/.local/bin` when it is missing.
- Template `permissions.deny`: `git -C <dir> push --no-verify` and `git -c core.hooksPath` for Claude.
- `bin/local-ci`: it passes `-s GITHUB_TOKEN=` to `act`. Without it, act v0.2.89 runs `gh auth token` and gives the user's token to the job as `secrets.GITHUB_TOKEN` and `github.token`. Public actions still download without a token.
- `docker/ci-runner.Dockerfile`: `/opt/hostedtoolcache` is owned by `runner` and `AGENT_TOOLSDIRECTORY` points to it, as on GitHub. Before, `actions/setup-node` failed with `EACCES`. `scripts/build-ci-runner.sh` checks that the directory is writable.
- `bin/local-ci`: the log directory name contains the ref (`<sha>-refs_heads_<branch>-<event>-<tier>`), so runs of one commit on two refs keep separate logs.
- `bin/local-ci`: it sets `UV_LINK_MODE=copy` in the job, which removes the uv hardlink warning.
- `bin/local-ci`: a baseline recorded on a feature branch also covers new feature branches (`@branch` key). Deploy branches and PR runs keep their own keys.
- Merge guard: in every directory, it denies a PR URL for another repo, `env -C`/`--chdir` before the merge, and a `gh api` merge through a variable (`pulls/$N/merge`).
- Merge guard: in every directory, it denies bundled or abbreviated `env` options (`-iC`, `--chd`), a PR selector or repo built by the shell (`$URL`, `$(...)`), and quoted `gh api` merge paths.

## [0.10.1] - 2026-10-08

### Fixed
- Central `graphify` MCP server runs `uvx --from "graphifyy[mcp]==0.9.79"` instead of `uv run --project <project>`.
  - Before, it failed to connect in every project without `graphifyy` in its own uv environment.
  - Now it starts in any project. Without `graphify-out/graph.json` it starts but has no graph.
  - Bump the pin together with `skills/graphify/.graphify_version`.

## [0.10.0] - 2026-10-08

### Added
- git-commit: `compose` project type (detected by `docker-compose.yml` / `compose.yml`), scopes `core`, `alerts`, `dashboards`, `config`, `tests`, `docs`, `ci`.

## [0.9.1] - 2026-10-07

### Fixed
- `install.sh` exits with code 2 on an unknown argument and in a linked git worktree, before it changes anything. Before, an older copy in a worktree ignored `--dry-run-settings`, ran a full install and linked `~/.claude`, `~/.cursor` and `~/.vibe/AGENTS.md` into the worktree. The links broke when the worktree was removed. Tests: `.claude/hooks/tests/test_install_guard.py`.

### Changed
- Statusline runs a pinned `ccstatusline@2.2.30` from `~/.local/bin` instead of `npx -y ccstatusline@latest`.
  - `npx` resolved the package on every repaint: about 1 s. The pinned binary takes about 0.35 s.
  - `install.sh` installs it with `npm i -g --prefix ~/.local`. No sudo is necessary.
  - `statusLine.refreshInterval` is `10`, so the reset timers update while the session is idle.
- `.claude/ccstatusline-settings.json`:
  - Line 1 adds the `git-branch` and `git-changes` widgets.
  - Line 2 drops `tok used`, which overlapped with the context bar.
  - Line 3 fixes the missing space in `3.0%resets`. Both timers now read `resets`.
  - Line 1 adds a harness check: `.claude/statusline-health.sh` (custom-command widget). It shows a green `✓ harness`, or a red `✗ N hooks missing` / `✗ vault ↑N`. It checks that each hook script in `settings.json` is executable, and counts unpushed vault commits.
  - Line 2 adds `effort` (thinking effort), `cache` (prompt cache hit rate for the last turn) and `compacted` (compaction count).
  - Line 4 adds `.claude/statusline-counts.sh`. It shows `skills used N/M` (Skill calls / skills loaded), the last skill, `mcp N` (MCP servers loaded) and a red `✗ <server> failed`.
    - It reads the session transcript. `skill_listing` and `deferred_tools_delta` are undocumented Claude Code records (checked on 2.1.293), so a Claude Code update can break it.
    - A skill run through a typed slash command is not counted, only Skill tool calls.
  - `customCommandCacheTtlSeconds` is `10`: ccstatusline adds about 0.15 s per custom command, and the cache keeps a repaint at about 0.35 s.
- `graphify` skill synced from `v0.9.49` to upstream `v0.9.79` (Graphify-Labs/graphify).
  - `.graphify_root` is written without shell interpolation, and `--watch` reads it instead of the raw `INPUT_PATH` (shell-injection fix).
  - Fully cached reruns still run the Step B3 merge (fixes the missing `.graphify_semantic.json` crash) and clear stale chunk files.
  - `--update` loads the old graph with `graphify.paths.load_node_link_graph`, which keeps edge direction.
  - The ai-dotfiles additions (`GRAPHIFY_PROJECT` local-clone fallback, Step 8.5 agent-MCP auto-wiring, `reference/` dir name) are re-applied. `.graphify_version` tracks `0.9.79`.
- `settings.json.tpl` sets `env.GRAPHIFY_NO_AUTO_REFRESH` to `1`. Since `0.9.72`, any `graphify` CLI run copies the upstream `SKILL.md` over an older installed skill, which would erase the ai-dotfiles additions. The variable applies to Claude Code only, not to Cursor or Vibe.
- `ponytail` pin bumped to `v4.13.0`. The vendored `SKILL.md` is unchanged upstream since `v4.9.0`. `.claude-plugin/plugin.json` follows the pin.
- `marketingskills` pin bumped to `v2.11.18` (six vendored skills).
  - `copywriting` adds a "No AI Tells" rule set (`references/ai-tells.md`).
  - `competitors` adds evidence discipline and a competitive asset audit.
  - `directory-submissions` puts the official MCP Registry first and adds a pre-submission safety gate.
  - `launch` adds `references/site-launch-qa.md`. It mentions `conversion-tracking` and `site-architecture`, which are not vendored.
  - `product-marketing` and `marketing-psychology` are unchanged. The Introw link in `launch/SKILL.md` stays pinned to the release tag.

## [0.9.0] - 2026-10-07

### Added
- `brain-audit:promote`: after `compile`, counts `**Pitfall hit:**` lines per rule id (`skills/brain-audit/scripts/count-pitfall-hits.py`, retired ids mapped) and drafts a sensor in vault `inbox/sensors/` for each rule hit in 2 or more sessions. It never installs anything. The digest lists the drafts.
- Stack rules load by path: `install.sh` runs `scripts/link-pattern-rules.sh`, which symlinks each vault `*-patterns.md` note with `paths:` frontmatter into `.claude/rules/` (gitignored). Claude Code loads a rule when Read, Write or Edit touches a matching file in the working directory. Bash commands do not trigger it.
- Vault: `paths:` added to the docker, python, deployment, observability, infisical, claude-code, shell and git pattern notes. The pitfalls header now says "Stack rules load when a matching file is read or edited".
- `.claude/agents/lookup.md` (Haiku) and `.claude/agents/reviewer.md` (Sonnet): read-only subagents with fixed models. `lookup` answers grep, find and fact questions. `reviewer` reports findings on a diff and never edits.
- `settings.json.tpl` sets `env.CLAUDE_CODE_SUBAGENT_MODEL` to `sonnet`. Delegations without a `model` key, including `general-purpose`, run on Sonnet. `install.sh` merges the key into live settings.
- `.claude/hooks/tests/test_agent_files.py` checks the agent frontmatter and the template `env` key.
- Limit: agent files set the model of a delegation. They do not make the main model delegate.
- Stop-check trust gate. `stop-check.sh` runs `.claude/stop-check` only if the hash of its normalized command is approved for the repo in `~/.claude/stop-check-trust`.
  - Normalized means: no comment or blank lines, no leading or trailing whitespace, no `\r`. A comment or indentation edit keeps the approval.
  - The repo id is the absolute `git rev-parse --git-common-dir`, so worktrees share approvals. Several hashes per repo are valid.
  - An unapproved command never runs and never blocks. The hook shows one `systemMessage` per repo and hash per session (marker `$TMPDIR/stop-check-warned-<session_id>`). The model gets no `reason`.
- `bin/stop-check-trust [path]` approves the command with no prompt and prints the command and hash. `--list` prints the store. `--revoke [path]` removes the approvals of a repo. `install.sh` links it into `~/.local/bin`.
- Template `permissions.deny` blocks `Bash(stop-check-trust *)` and `Bash(*/stop-check-trust *)`, so the agent cannot approve. The user runs `! stop-check-trust`.
- `install.sh` approves this repo's own `.claude/stop-check` once.
- `PreToolUse` (Bash) `hardline-check.py`, first in the list: a tripwire for destructive commands, not a security boundary. Rules are data in `hardline-rules.json`.
  - It reads the command with `shlex`. It drops heredoc bodies, except a body fed to `bash`/`sh`/`zsh`. It skips `VAR=x` and wrappers (`sudo`, `env`, `timeout`, `rtk proxy`, …) and parses `bash -c` one level deep.
  - Tier 1 `deny`: `rm -rf` on `/`, home, `.` or `..`; `mkfs`; `dd of=/dev/*`; a redirect to `/dev/sd*` or `/dev/nvme*`; `find -delete` from `/` or home; a fork bomb. The reason tells the user to check the target and run it with `!`. It never repeats the command, so it cannot be pasted by mistake.
  - Tier 2 `ask`: force push to `main`/`master`, `git clean -x`/`-d` without a path, docker prune and volume removal, `chmod -R 777`, `curl|wget … | sh`. A tier-1 shape with a `$` or backtick target asks too. Unbalanced quotes ask only near `rm`, `dd` or `mkfs`.
  - Known bypasses (variables, other interpreters, scripts in a file, nested `bash -c`, aliases and functions) are listed in the hook header and tested as passing.
- `permissions.ask` in the template: `ansible-playbook`, `kubectl apply|delete`, `docker compose down`, `terraform apply|destroy`.
- Mistral Vibe hooks: `.vibe/user-hooks.toml` runs `hardline-check.py` and `git-commit-check.sh` as strict `pre_tool` (bash) hooks, and `stop-check.sh` as a `post_agent` hook (180 s). `install.sh` links `~/.vibe/hooks.toml` to it.
  - `scripts/vibe-claude-hook.py <hook>` adapts the protocol. A Claude `deny`, Stop `block` or exit 2 becomes a Vibe `deny`. A Claude `ask` becomes a `deny` that tells the model to ask the user.
  - Any other output or exit code is an adapter error (exit 1, details on stderr). The strict hooks then deny the bash call.
  - A `stop-check` deny injects a retry message. Vibe allows 3 retries per hook per turn.
  - Vibe has no session-start hook: the vault sync and load stay manual (`.vibe/bootstrap.md`).
- `scripts/replay-bash-rules.py [--days N]`: replays past Bash calls from `~/.claude/projects` through the hook and the template `ask` list. It prints prompts per rule, session and day, and every prompt with an empty TP/FP label column.

### Changed
- `AGENTS.md`: new "Soul of the Agent" section — reports to the user are extremely concise, facts and sources over inference. Cursor and Vibe copies rebuilt.
- `AGENTS.md` FinOps: keeps the "state the model you are on" rule, points Claude Code to `.claude/agents/` and `CLAUDE_CODE_SUBAGENT_MODEL`, and keeps the Haiku/Sonnet/Opus list for Cursor and Vibe only. `.cursor/rules/agents.mdc` and `.vibe/AGENTS.md` regenerated.
- `install.sh` merges `permissions.deny`, `permissions.ask`, `env` and `hooks` from the template into an existing `settings.json`, not only plugins and marketplaces. The merge is `scripts/merge-settings.py` (stdlib, replaces the `jq` block).
  - It adds missing template entries and keeps local-only entries.
  - It writes atomically and keeps `settings.json.bak` when it changes the file.
  - A semantic conflict stops it before writing, with exit 3 and one `CONFLICT` line per conflict. Conflicts: an `env` value differs; the same hook command has another event, matcher or timeout; live `disableAllHooks: true`.
  - A template `deny`/`ask` rule also in live `allow` is added with a note. It is not a conflict.
- `install.sh --dry-run-settings` prints the planned settings changes and conflicts, then exits. It changes no file.
- SessionStart drift check: plugin or marketplace drift alone still auto-runs `install.sh`. Drift in permissions, `env` or hooks prints `[install-check] template adds: <keys> — run scripts/install.sh` and runs nothing. An auto-run that exits 3 prints its `CONFLICT` lines in the hook output.
- `/capture` step 4 writes a `**Pitfall hit:** [[pitfalls#^<id>]]` line to the session log for each Absorb or Improve verdict.
- Pitfalls budget is enforced at write time: `scripts/check-pitfalls-budget.sh` fails `/capture` and `brain-audit:compile` when `pitfalls.md` exceeds 6,000 B or a rule has no stable id (`^g3`).
- SessionStart: the last-exit log is one `[last exit]` status line plus up to 5 warnings (was the last 30 lines, ~2.2 KB). The full log stays in `~/.claude/logs/brain-sync-end.log.prev`.
- SessionStart: if pitfalls still exceed the room, whole sections are dropped and named in the truncation line (was a byte cut mid-rule).
- Vault: the "Git and GitHub", "Claude Code" and "Shell" pitfalls sections moved to `git-patterns`, `claude-code-patterns` and `shell-patterns`; the Wi-Fi scan rule moved to `deployment-patterns`. Six rules were merged (no fact dropped). Every rule has a stable id. `pitfalls.md` is 5,106 B.

### Fixed
- `git-commit-check.sh`: commit detection now looks only at simple commands that start with `git [-C dir | -c k=v | --no-pager] commit` (split on `&& || ; |` and newlines outside quotes and heredoc bodies). Commit-like text inside heredocs, quoted strings, `echo` or `grep` arguments no longer triggers a block. `-m "$(cat <<'EOF' … EOF)"` still yields the heredoc as the message. The scope is checked on the subject line only. Parse failure still fails open. New regression tests in `test_git_commit_check.py`.
- `config/brain-projects.tsv`: `telegram-to-notion` entry renamed to `notion-pilot` at `/home/lgiron/lab_perso/notion-pilot`. The repo was renamed on 2026-05-28, so `sync-project.sh --all` skipped it and its `.claude/memory` never synced to the vault.

## [0.8.1] - 2026-10-05

### Changed
- `AGENTS.md` Development: prefer the smallest change that works via the `ponytail` skill (YAGNI, reuse, stdlib, installed deps).
- `medium-writer`: every article must end with the fixed Medium support closing (applause / follow / @louis_10840).
- `medium-writer`: keep `## Contents` + Notion `<table_of_contents/>` when present in the article source.
- `medium-writer`: no Markdown/`<table>` data tables in articles (Medium has none); use bullets instead.
- `medium-writer`: each article carries a `**Topics:**` line (≤ 5 Medium tags) under the H1; review checks it, publish moves it into Medium's topics box.
- README aligned with the harness article: vault loading per tool, full Claude Code hook list, SessionStart 9.5 KB budget, `git-commit-check` scope, Stop-check permissions warning, `rsync --update` overwrite caveat, `brain.env` step in quick start.

### Fixed
- Cursor `qmd` MCP: `INDEX_PATH` points at the `brain.db` index.

## [0.8.0] - 2026-10-05

### Added
- Claude Code **sensor hooks**:
  - `Stop` → `stop-check.sh` runs the repo's `.claude/stop-check` command when the git tree has changes, blocks the stop on failure with the output tail, and never blocks twice in a row.
  - `Stop` → `compact-nudge.sh` reminds the user to `/compact` past 250k tokens of context, then every 100k.
  - `PreCompact` → `precompact-checkpoint.sh` writes a breadcrumb to `inbox/daily/checkpoints/<slug>/` before each compaction.
  - Tests are in `.claude/hooks/tests/`. ai-dotfiles dogfoods the Stop check with `shellcheck` on changed scripts (`.claude/stop-check`).
- `AGENTS.md` (repo root) is the single source of shared agent rules. `.claude/CLAUDE.md` imports it and keeps only Claude-specific lines. `scripts/build-agent-rules.sh` generates `.cursor/rules/agents.mdc` and `.vibe/AGENTS.md` (`.vibe/bootstrap.md` + `AGENTS.md`), and CI checks they are current. `install.sh` links `~/.vibe/AGENTS.md`, which Vibe reads as user-level instructions: Vibe now gets the shared rules outside the ai-dotfiles repo.
- `## Docs style (80% ASD-STE100)` block in `AGENTS.md`, and the `asd-ste100` skill vendored from danyuchn/asd-ste100-skill at commit `32511c6992ec`.
- `check-vendored-skill-updates.sh`: an entry with `"branch"` tracks the branch head (commit-SHA pin) for upstreams without releases.

### Changed
- Cursor rules `development-principles`, `docs-hygiene`, `graphify-context` and `specs-location` merged into the generated `agents.mdc`.
- `capture` skill: reads and folds today's pre-compaction checkpoint. Before touching `pitfalls.md` it states a verdict: Absorb into an existing rule (default), Improve, Save or Drop.
- Memory templates: `DESIGN.md` and `API.md` moved to `config/memory-templates/on-demand/` (`init`/`upgrade` no longer create them). Each template header asks for one fact per line, ≤ 20 words, active voice.
- `ponytail` pin bumped to `v4.12.0`. The vendored `SKILL.md` is unchanged upstream since `v4.9.0`.
- `skipDangerousModePermissionPrompt` removed from `settings.json(.tpl)`: `--dangerously-skip-permissions` shows its confirmation screen again.
- `settings.json.tpl` now wires `git-commit-check.sh`. It was only in the tracked `settings.json`, so fresh installs missed it.
- `impeccable`, `taste-skill` and `vercel` plugins disabled globally (`settings.json`, and `settings.json.tpl` so `install.sh` does not re-enable them): they loaded skill listings, and impeccable a PostToolUse/Stop hook, into every session, including Python/infra ones. Enable them per frontend project via `enabledPlugins` in the project's `.claude/settings.json` (README → plugins).

### Fixed
- `git-promotion` tests failed locally when `init.defaultBranch=main` (`git branch -f main` on the checked-out branch): test repos now start on a `scratch` branch. CI passed only because its default branch is `master`.
- `test_git_commit_check.py` used a `dashboard` scope that is not in `scopes.json`; it uses `api` (Python-only) now.

## [0.7.1] - 2026-10-02

### Fixed
- `git-commit-check.sh` validates the scope against the repo the commit targets (`git -C <dir> commit`, or the last `cd <dir>` before `git commit`) instead of the session cwd, and now also checks `git -C <dir> commit`, which it used to skip entirely. Tests in `.claude/hooks/tests/`, added to the git-promotion gate.

## [0.7.0] - 2026-09-29

### Added
- `git-promotion` skill, generalised from prosper's: `scripts/promote.py` moves code onto a stage branch with a semver tag (from `feat`/`fix`/`enh`/breaking commit types) and a GitHub Release, dry run by default. Stages, tag prefix, gate commands and changelog come from a per-repo `.git-promotion.json`: `develop → preprod → main` (alpha tags on preprod), `develop → main`, or `main` alone, where `--pr N` squash-merges the PR, tags the merge commit and uses the CHANGELOG `## [X.Y.Z]` section as release notes. Stdlib-only (prosper's `packaging` dependency is gone); tests under `scripts/tests/`.
- `.git-promotion.json` for ai-dotfiles: single `main` stage, `v` tags, the git-promotion tests as gate, CHANGELOG notes.
- `medium-writer` skill: drafts a Medium article from real repo code into `articles/`, then writes it onto its Notion task page.

### Changed
- `.claude/ccstatusline-settings.json` saved in ccstatusline's v4 format; HyperFrames CLI-installed skills (`hyperframes*`, `media-use`) gitignored under `.claude/skills/` and `.cursor/skills/`.
- Prompt audit of the global config. `.claude/CLAUDE.md` rewritten (946 → 500 words): same rules, stale facts removed (wrong vault path, `.claude/brain/`, an "automatic" brain-route flow no hook runs), the duplicated wikilink/commit/plan-location rules said once, shouting removed. `.claude/LocalBrain.md` rewritten against the real vault layout.
- `capture` skill: reads only this session's log (not every past note), rewrites `CONTEXT.md` in place as a snapshot, keeps `DECISIONS.md` one line per live decision, and records pitfalls **and** lessons as one-line cross-project rules in `pitfalls.md`; project-specific traps go to `CONTEXT.md` → Gotchas. The slug comes from `load.sh --slug-only`.
- `git-commit` skill states its reason (the PreToolUse hook rejects off-list scopes) instead of shouting; the "Hard Rules" block, which repeated Steps 1–3 and referred to a scope table that no longer exists, is gone. Cursor `graphify-context` gives the reason for leaving `graphify-out*` alone instead of "Hard constraints"; `session-implementation-log` drops a warning about the long-removed `index/implementation/` path.
- Stack-specific rules (Docker/Coolify, Python/Postgres/pandas, Ansible/network, Prometheus) live in the `## Rules` list of the vault's `resources/knowledge/patterns/*-patterns.md`, not in `pitfalls.md`, so the injected file stays under its ~6 KB share of the SessionStart budget. `capture`, `brain-audit:compile` and `.claude/CLAUDE.md` route rules accordingly; `LocalBrain.md` drops the removed `todo/`, `kanban/` and `docs/memory/` entries.
- `brain-audit:connect` adds pattern links under a project note's existing `## Links` (the one-pager shape has no `## See also`); `connect` and `insights` fall back to `qmd vsearch` when `qmd query` outlives the Bash timeout on CPU.
- `lessons-learned.md` merged into `pitfalls.md` (a distilled rule list); the old incident logs are frozen under `resources/operational/ai-agents/archive/`. `brain-audit` compile/digest/insights and the Cursor `claude-pitfall` rule follow the same format.

- No journals outside session logs: vault `projects/<slug>.md` notes and repo `.claude/memory/*` are snapshots. Rule stated in `.claude/CLAUDE.md` and the always-on Cursor `specs-location` rule; the vault project template's `## Journal` became a pointer to the session logs; `load.sh` warns at session start when a project note has a journal section or exceeds 600 words, or `CONTEXT.md` exceeds 1,200 words. Claude's SessionStart hook no longer prints `.claude/memory/` (the project CLAUDE.md @-imports it; Cursor/Vibe still get it).

- Vault `projects/<slug>.md` is a one-pager with a fixed shape — one-sentence summary, Idea, Objectives (goal, users, success, non-goals), How it works, Where, Memory, Links — and no current-state or journal section. `ai-dotfiles init` and `upgrade` now create the skeleton via `skills/brain-load/scripts/instantiate.sh` (idempotent, `--cap` optional); `/brain-init-project` fills it; the vault Templater template matches.

### Fixed
- `.cursor/skills/medium-writer` symlink pointed at itself (`../skills/…`).
- SessionStart hook injected the whole 50K-word `pitfalls.md`; the oversized output was saved to a file and only a 2 KB preview reached the model. Pitfalls now get whatever the hook's ~9.5 KB output budget leaves after the project note, cut at a line boundary with a truncation notice (a fixed 10 KB pitfalls cap still overflowed once the note was added); the lessons block is gone (merged).
- `brain-audit/scripts/_brain_env.sh` failed when sourced from zsh (`BASH_SOURCE[0]: parameter not set`) and leaked `set -euo pipefail` into the caller's shell.
- `brain-load/scripts/load.sh` looked for project memory in `.claude/brain/` — it lives in `.claude/memory/`.
- The `AGENTS.md` template (`init`/`upgrade`) had every `@.claude/memory/` import commented out, while Claude's SessionStart hook now skips memory — new projects loaded none. `OBJECTIVES.md` and `CONTEXT.md` (the `read_on_session_start` defaults) are imported by default; the stale `# CLI / VSCode` heading lines are gone.
- `.claude/CLAUDE.md` is generated only when the root `CLAUDE.md` is not the `AGENTS.md` symlink (it loaded `AGENTS.md` twice otherwise); its template is now just `@../AGENTS.md`, without the stale "hooks don't fire in VSCode" header.
- Cursor `finops-claude` rule: `claude-finops.md` path matches `.claude/CLAUDE.md` (`resources/operational/ai-agents/`), retired `/create-pr` reference removed. `brain-load/reference/VAULT-LAYOUT.md`: mode detection checks `_templates/project-template.md`, as `load.sh` does.
- `.vibe/AGENTS.md` pointed at `skills/brain-sync/sync.sh` / `skills/brain-load/load.sh`; the scripts are under `scripts/`.

### Removed
- `.github/workflows/release.yml`: releases are created by `git-promotion` (notes from the CHANGELOG section); the tag-triggered workflow would race it, and its notes listed plugins that no longer exist.
- `brain-route` skill, its `sync.sh start` call and `brain-audit/scripts/audit.sh`: the "automatic maintenance" only created folders and wrote an empty digest every 7 days, resetting the clock without doing any work. `/brain-audit` is manual; the SessionStart hook prints "maintenance due" when `meta/last-maintenance.md` is older than 7 days.
- `.claude/SKILLS_INDEX.md` — stale (two skills that no longer exist, ten missing) and redundant with the skill list Claude Code injects.

## [0.6.0] - 2026-09-10

### Added
- `marketingpowers` — a router plugin over six vendored marketing skills. `skills/marketingpowers/SKILL.md` (local, not upstream) picks the right sub-skill, enforces `product-marketing` first, and routes away requests that are not marketing tasks; `references/campaign-sequence.md` holds the ordered full-campaign playbook (front door → comparison pages → launch → directories → psychology pass). Symlinked into Claude / Cursor / Vibe as one plugin.
- Six marketing skills vendored from [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) `v2.11.1` (MIT, © Corey Haines) under `skills/marketingpowers/skills/`: `product-marketing`, `launch`, `copywriting`, `directory-submissions`, `competitors`, `marketing-psychology` — surfacing as `marketingpowers:<name>`. `SKILL.md` + `references/` only (upstream `evals/` fixtures dropped). Selected for promoting **notion-pilot** (self-hosted OSS dev tool, no ad budget) — the paid/sales/mobile skills in the upstream set were deliberately left out.
- Shared vendor pin `skills/marketingpowers/.marketingskills_version` (one pin for all six) registered in `config/vendored-skills.json` as `marketingskills`, so SessionStart flags upstream releases.

### Changed
- Local patch in `skills/marketingpowers/skills/launch/SKILL.md`: the `../../tools/integrations/introw.md` partner link is rewritten to an absolute upstream URL, since the upstream `tools/` tree is not vendored.
- Six separate top-level skills folded into the single `marketingpowers` plugin: the per-skill `.claude-plugin/plugin.json` files are dropped in favour of one at the plugin root, and the 18 per-skill Claude/Cursor/Vibe symlinks collapse to 3. Re-syncing the six no longer touches the router.
- Runtime `.claude/feedback/` and `.claude/remote-settings.json` gitignored.
- Nested sub-skills are discoverable only in Claude Code (as `plugin:name`) — Cursor CLI and Mistral Vibe scan skills one level deep, so they see a router and nothing under it. Both the `marketingpowers` and `brain-audit` routers now carry an "Invoking a sub-skill" section giving the relative `skills/<name>/SKILL.md` path and telling the agent to read it directly when the namespaced form is unavailable, rather than reporting the sub-skill as missing.

## [0.5.0] - 2026-09-08

### Added
- `ponytail` skill vendored from [DietrichGebert/ponytail](https://github.com/DietrichGebert/ponytail) `v4.9.0` into `skills/ponytail/` (core only; on-demand). Symlinked into Claude / Cursor / Vibe via `install.sh`. Always-on `.mdc` deferred (re-check 2026-10-01).
- Skill-usage telemetry: Claude `Skill` PreToolUse now calls `.claude/hooks/log-skill-usage.sh` (source `claude:Skill`). Cursor `preToolUse`/`Read` logs `**/skills/**/SKILL.md` loads as `cursor:skill-read` (heuristic; B0 in `spikes/cursor-b0-*`).
- SessionStart check for vendored skills: `scripts/check-vendored-skill-updates.sh` + `config/vendored-skills.json` (graphify, ponytail). Cached GitHub latest-release compare (24h, parallel fetches, short retry on fetch failure); injects a WARNING when behind (Claude + Cursor). Does not auto-upgrade.

## [0.4.0] - 2026-09-08

### Added
- Gitignored `articles/` for local Medium/blog drafts (not published from this repo).
- `scripts/log-skill-usage.sh` — Claude + Cursor session hooks append `brain-sync` / `brain-load` runs to `~/.claude/skill-usage.log` (with source tag). Skill-tool PreToolUse logging alone never counted hook-driven runs.
- Cursor user hooks + `scripts/cursor-agent-brain.sh` / `brain-hooks-prewarm.sh` for Agent CLI Local Brain session lifecycle (global user-rule inject; works from any cwd).

### Changed
- Cursor brain hooks: turn-1 via global user rule (prewarm; **any cwd**, no `cd`); stop writing repo-root `AGENTS.md` (Vibe symlink); IDE hard-off not alwaysApply.
- Cursor: brain-sync / brain-load session lifecycle moved from always-apply rules to user hooks. IDE Agent hard-off; `@claude-pitfall` manual only. Bounded pitfalls excerpt on CLI sessionStart. Claude Code hooks unchanged. Claude↔Cursor hook bridge unsupported for brain automation (disable bridge when using Cursor brain hooks).
- Cursor: add `cursor-brain-ide-hard-off` rule and tighten brain-sync/load skill wording so IDE Agent does not bash-compensate when hooks skip.
- Cursor: `session-implementation-log` is no longer always-apply — IDE Agent must not auto-write implementation notes; use `/capture` (or explicit ask) only.
- Cursor brain hooks: fix pitfalls excerpt packing (newest 3 first, then truncated index); do not plant `.started` on JSON emit failure; RUN logs include VSCODE_*/remote; warn against exporting `BRAIN_AGENT_HOOKS` from shell profile; unit test script for libs.

## [0.3.1] - 2026-08-27

### Fixed
- `brain-sync` qmd PATH fix: use the shim directory from `command -v qmd` (nvm's `.../bin`) instead of `readlink -f` into the package tree — the resolved package `bin/` has no `node`, so the old check never prepended and Cursor agent's Node 24 broke `better-sqlite3` (ABI 137 vs 141). Shell startup (`.zshenv` / `.zshrc`) now also keeps `$NVM_BIN` ahead of injected runtimes.

### Added
- `photo-archive-triage` skill — non-destructively triages messy photo/video collections (PhotoRec `recup_dir.N` dumps, phone backups, duplicated exports) into a clean set ready for an Immich import: resumable SQLite-ledger pipeline for validity screening and exact SHA-256 dedup, junk/thumbnail routing to a human-reviewed folder, and exiftool-based capture-date recovery with either an `--apply-mtime` or a post-upload destination-patch path. Includes `reference/destination-patch-immich.md`, documenting the verified Immich API contract and an SSO/reverse-proxy trap that makes the API unreachable while the web UI still works.
- Six frontend/design skills available by default via two mechanisms: `impeccable` ([pbakaus/impeccable](https://github.com/pbakaus/impeccable)) and `taste-skill` (third-party, [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill)) as Claude Code plugins in `.claude/settings.json.tpl`/`extraKnownMarketplaces`; `web-artifacts-builder`, `canvas-design`, `algorithmic-art`, and `mcp-builder` vendored as local skills under `skills/<name>/` (cherry-picked from Anthropic's `example-skills` plugin / [anthropics/skills](https://github.com/anthropics/skills), which bundles 17 skills total — most not wanted here), auto-symlinked into `.claude/skills/` by `scripts/install.sh`. See README "Frontend & design skills" for how the six compose.
- `brain-session-start.sh` (SessionStart hook) now detects when `settings.json` is behind `settings.json.tpl` (new `enabledPlugins`/`extraKnownMarketplaces` keys) and automatically re-runs `scripts/install.sh` — so forgetting to re-run install after a `git pull` self-heals on the next session instead of silently missing new plugins.
- `find-security-vulnerabilities-in-code` and `fix-security-vulnerabilities-with-strix` skills, vendored from [usestrix/strix](https://github.com/usestrix/strix) (2 of its 9 skills — white-box code review + fix/verify, the pair that fits a single-user personal-projects setup). Wraps the self-hosted `strix` CLI (Docker sandbox, BYO LLM key); the vendored SKILL.md adds an explicit authorization gate on top of Strix's own README disclaimer, since Strix itself doesn't enforce target ownership at runtime. See README "Security review & pentesting skills".

### Changed
- Frontend/design plugin tooling swapped: retired `frontend-design` (Anthropic) and `ui-ux-pro-max` (third-party design-intelligence lookup) in favor of `impeccable` (successor to `frontend-design`; 59 deterministic anti-pattern detectors plus a live-browser polish/audit loop, targeting generic "AI slop" output) and `taste-skill` (14 bundled opinionated style-direction skills, replacing manual palette/font-pairing lookup). `impeccable` installs a `PostToolUse`(Edit\|Write)+`Stop` hook that scans touched UI files every session (requires Node ≥22; self-disables with a message otherwise, never blocks a turn on error) — see README "Frontend & design skills".
- `graphify` skill synced from vendored `v0.4.2` to upstream `v0.9.49` (Graphify-Labs/graphify) — `SKILL.md` dropped from 1347 to 783 lines via upstream's own `reference/` split (8 files: add-watch, exports, extraction-spec, github-and-merge, hooks, query, transcribe, update), removed the dead `trigger: /graphify` frontmatter field, and picked up numerous upstream fixes (Windows/PowerShell JSON-encoding bug, sensitive-file reporting, GitHub-URL/multi-repo ingestion, graph health check, FalkorDB export, Gemini backend). The two ai-dotfiles-specific additions (`GRAPHIFY_PROJECT` local-clone fallback, default-on agent-MCP auto-wiring via `scripts/setup_agent_mcp.py`) were re-applied on top after diffing the old vendored copy against the exact `v0.4.2` baseline to isolate them precisely. `.graphify_version` now tracks the synced release.

### Removed
- `create-pr` skill (redundant with the mandatory `git-commit` skill; PR creation left to `gh pr create` directly).
- `review` skill (rarely used; also resolved a triggering collision with the separate `code-review` skill).
- Dead `token-watch`/`token-guard` entries in `.claude-plugin/marketplace.json` — retired, but the entries pointed at `skills/` directories that no longer existed.

### Changed
- CI skill validation now rejects duplicate entries in `skills/git-commit/scopes.json` and verifies shared skills are symlinked in `.claude/skills/` and `.cursor/skills/`.
- `review` skill moved to canonical `skills/review/` with Claude/Cursor/Vibe symlinks; `git-commit` SKILL.md no longer carries a stale scope snapshot table.
- `scripts/install.sh`'s skill-linking loop now symlinks `skills/<name>` into `.cursor/skills/<name>` per-skill (same as `.claude/skills/`/`.vibe/skills/`), replacing the old single `.cursor/skills -> ../skills` directory symlink. The loop now also skips any skill matching `coe-*` for all three tools, so internal/company skills synced locally (via the separate, gitignored `scripts/sync-coe-skills.sh`) are excluded from Claude Code, Vibe, and Cursor's runtime view alike — previously the `coe-*` `.gitignore` rules only kept them out of git, not out of any tool's local skill list. See README "Skill discovery across tools".
- Added `.vibe/skills/coe-*` to `.gitignore` (previously only `.claude/skills/coe-*` and `.cursor/skills/coe-*` were listed).

### Fixed
- `scripts/install.sh`'s `settings.json` generation now merges instead of overwriting. It previously did `sed ... "$TPL" > "$OUT"` unconditionally — a full overwrite from the template on every run — despite `brain-session-start.sh`'s auto-heal comment claiming "local-only additions in settings.json are left untouched." That claim only held for the auto-heal's *decision* to re-run install.sh (which does correctly diff only `enabledPlugins`/`extraKnownMarketplaces`); the *action* it took wiped everything else the template doesn't define — `permissions.allow`, extra `PreToolUse` hooks, other enabled plugins/marketplaces, `effortLevel`, `pluginConfigs`, `tui`, `skipWorkflowUsageWarning`, `autoMode`, and any other machine-local key. Discovered by triggering it directly this session; now `install.sh` merges only `enabledPlugins`/`extraKnownMarketplaces` into an existing `settings.json` (backing it up to `settings.json.bak` first) and leaves every other key alone, matching what the hook's comment already claimed.
- `code-index` and `graphify`'s central MCP entries (`config/memory-templates/mcp-central-claude.json.tpl`) now use `${CLAUDE_PROJECT_DIR:-.}` instead of bare `${CLAUDE_PROJECT_DIR}`. Claude Code only sets `CLAUDE_PROJECT_DIR` in the *spawned server's* environment, not in its own env used to expand `${VAR}` in user-scoped `~/.claude.json` entries — so the bare form always showed a "Missing environment variables" warning and failed to connect. Run `ai-dotfiles mcp-sync` (or restart Claude Code) to pick up the fix.
- Added missing Claude plugin metadata for `sop-builder` so the skill structure CI check passes.
- Allowed standard merge commit messages in the git-commit hook.
- Added `ansible/server-setup` detection markers to the git-commit scope registry.
## [0.3.0] - 2026-07-18

### Added
- `DESIGN.md` project memory template for original application intent, UX, and durable workflows, kept distinct from live technical `ARCHITECTURE.md`
- `grill-me` skill for stress-testing plans and designs through one-question-at-a-time interrogation with recommended answers
- `brain-audit` refactored as a plugin with 6 independent subskills (`compile`, `connect`, `insights`, `queries`, `qmd-sync`, `digest`) following the superpowers plugin pattern
- `brain-audit:compile` — reads `inbox/daily/` (last 30 days), promotes cross-project pitfalls/lessons to `resources/operational/ai-agents/`, asks inline for ambiguous entries
- `brain-audit:connect` — QMD `vsearch` per note → appends `[[wikilinks]]`, shows git diff for review
- `brain-audit:insights` — QMD hybrid query per template → writes `inbox/insights/YYYY-MM-DD.md`
- `brain-audit:qmd-sync` — `qmd update` with prune reporting, triggers re-embed if stale
- `brain-audit:queries` — two structured vault analyses: knowledge-gaps (coverage survey vs. recent implementation notes) and roadmap (consolidated status from `projects/*/ROADMAP.md` + recent follow-ups); archives to `resources/queries/archive/`
- `brain-audit:digest` — weekly summary to `meta/digest-YYYY-MM-DD.md`, resets maintenance clock
- **MCP server centralization**: `qmd`, `code-index-mcp`, and `graphify` are now registered once at Claude Code's user scope (`~/.claude.json`) and — `qmd` only — Cursor's global scope (`~/.cursor/mcp.json`), instead of being copy-pasted into every project. New `ai-dotfiles mcp-sync` command (re)applies them by hand. `ai-dotfiles init`/`ai-dotfiles upgrade` no longer write `qmd`/`code-index` into a new project's `.claude/settings.json`; the graphify skill no longer writes a per-project Claude Code entry into `.mcp.json` either (its Cursor entry is unchanged, still per-project). Forward-only: already-initialized projects keep their existing per-project entries untouched. Corrects the claim above — `~/.claude/claude.json` (note the extra `.claude/` segment) is not a path Claude Code actually reads; the real global-scope location is `~/.claude.json` (home root, confirmed via https://code.claude.com/docs/en/mcp).

### Changed
- `.gitignore` now excludes Claude daemon/job runtime state plus last cleanup/update result markers
- `/capture` now reviews project implementation notes against `ARCHITECTURE.md`, `DECISIONS.md`, `ROADMAP.md`, and `CONTEXT.md`, updating only relevant project-brain files and asking before breaking changes.
- `grill-me` now explicitly forbids reflexive praise and requires skeptical challenge before approving an idea
- Per-project memory directory renamed from `.claude/brain/` to `.claude/memory/` to align with pratique-ia standard
- `config/brain-templates/` renamed to `config/memory-templates/`
- `.claude/CLAUDE.md` VSCode fallback simplified to `@../AGENTS.md` (AGENTS.md contains memory @-imports)
- AGENTS.md template now includes `## Memory` and `## Standards` sections with commented @-imports

### Migration
- Run `ai-dotfiles upgrade <project-path>` or `upgrade --all` on existing projects to auto-migrate `.claude/brain/` → `.claude/memory/`

### Added
- `ai-dotfiles merge-memory <path|--all>` — new CLI subcommand that backfills OKF-style `type:` / `updated:` frontmatter and any missing `## sections` from current templates into existing project memory files, without adding new files or changing content (uses `scripts/merge-memory.sh` + `scripts/merge-memory-md.py`)
- `scripts/merge-memory.sh` — focused backfill script; wraps `merge-memory-md.py` for a full project or all registered projects

### Fixed
- `brain-audit/scripts/audit.sh`: phases now skip gracefully when `compile.sh`, `connect.sh`, or `qa.sh` are absent instead of exiting with an error — allows the orchestrator to run with only the implemented phase scripts
- QMD embed/update failures in `brain-sync` now logged to `~/.claude/logs/brain-sync.log` instead of silenced with `2>/dev/null`

### Fixed (prior unreleased)
- **`brain-session-end.sh`**: removed broken `systemMessage` emission. `SessionEnd` hooks do NOT give Claude a final turn — that is `Stop` hook behavior. The message was emitted but never received. Replaced with a log-only warning written after sync (so `tail -30` in SessionStart catches it).
- **`brain-session-start.sh`**: `tail -20` → `tail -30` to ensure the 4-line missing-notes warning is visible (sync output is 23 lines; previous window cut the warning entirely).

### Added (prior unreleased)
- **`skills/capture/SKILL.md`**: added full skill content to `skills/` directory so Claude Code discovers `/capture` as a user-invocable skill. Previously the skill was only in the plugin marketplace stub and cache, not in the discoverable `skills/` tree.
- **`/capture` skill** (`capture@ldom1-ai-dotfiles`): new user-invocable skill that runs the full end-of-session workflow — write implementation notes, check pitfalls/lessons, run `sync.sh end`, prompt user to close. This is the primary path for session documentation; the SessionEnd hook is now a fallback only. (Renamed from `/exit` then `/wrap` — both are reserved or conflict-prone names.)

### Changed (prior unreleased)
- **SessionEnd implementation note enforcement**: `brain-session-end.sh` now scans `$BRAIN_PATH/inbox/daily/implementation/` for today's notes before syncing. Fallback warning is appended to the end-session log (shown in `LAST EXIT` at next `SessionStart`).

### Removed
- `clawvis-skills` MCP reference (pointed to non-existent file)
- `skills/brain-audit/scripts/compile.sh`, `connect.sh`, `qa.sh` (logic moved to SKILL.md)
- `skills/brain-audit/.claude-plugin/plugin.json` (replaced by root `plugin.json`)

## [0.2.0] - 2026-05-20

### Added

- **Per-project MCP wiring**: `ai-dotfiles init` and `ai-dotfiles upgrade` now configure both `code-index-mcp` (AST code search) and `qmd` (semantic vault search) in `<project>/.claude/settings.json`. Only brain-initialized projects get these MCPs.
- **Central QMD database**: vault indexed at `${HOME}/vault-qmd/index.sqlite` (controlled via `QMD_INDEX_PATH` in `brain.env`). One collection: `brain → $BRAIN_PATH`. Embeddings refresh automatically at session end via `brain-sync`.
- `config/brain-templates/mcp-settings.json.tpl` — MCP config template with `__PROJECT_PATH__` and `__QMD_INDEX_PATH__` placeholders; excluded from brain template copy.
- `scripts/lib-mcp.sh` — idempotent MCP config injection helper sourced by init + upgrade scripts.
- `brain-sync` end hook now runs `qmd update` (re-index new/changed files) then `qmd embed` after vault push (non-blocking; skipped if qmd not installed or `QMD_INDEX_PATH` unset).
- `brain.env` now exports `BRAIN_PATH` and `QMD_INDEX_PATH` so hooks and child processes inherit them without re-sourcing.
- **`brain-search` skill**: semantic/keyword vault search via qmd. Claude invokes it mid-session to retrieve past decisions, specs, lessons learned, or any vault knowledge relevant to the current task.

### Prerequisites (new)
- `jq` — `apt install jq` / `brew install jq`
- `uvx` — `pip install uv`
- `qmd` — `npm install -g @tobilu/qmd` (one-time vault setup required, see README)

- **Project Brain Sync**: per-project persistent knowledge layer synced bidirectionally between `<project>/.claude/brain/` and `$BRAIN_PATH/projects/<slug>/`.
  - `ai-dotfiles init <path>` — creates `.claude/brain/` with template files, mirrors to vault, registers in `config/brain-projects.tsv`
  - `ai-dotfiles upgrade <path|--all>` — adds missing template files without overwriting existing content
  - `ai-dotfiles sync <path|--all>` — manual bidirectional rsync (mtime wins via `rsync --update`)
  - Template files: `settings.json`, `OBJECTIVES.md`, `ARCHITECTURE.md`, `DECISIONS.md`, `CONTEXT.md`, `ROADMAP.md`, `API.md` under `config/brain-templates/`
  - `brain-sync` start/end hooks now auto-sync all registered projects (vault→project on start, project→vault on end)
  - `brain-load` now detects `.claude/brain/settings.json` and injects `read_on_session_start` files (default: OBJECTIVES.md, CONTEXT.md) into session context
  - CLI entry point: `bin/ai-dotfiles` (symlinked to `~/.local/bin/` by `install.sh`)
  - Registry: `config/brain-projects.tsv` (header-only on fresh install; append-only from scripts)

- **Versioned Git hooks**: `git-hooks/pre-commit` (same behavior as local `.git/hooks/pre-commit`: block commits under `.cursor/plans|projects|plugins|skills-cursor` except tracked `.gitignore`, secret scan on staged diffs). `scripts/install.sh` sets `core.hooksPath` to `git-hooks`; `scripts/install-git-hooks.sh` does only that for fresh clones. `core.hooksPath` is per-clone local config — not stored in commits — so each machine runs install once.
- **Custom Claude Code statusline** (`.claude/statusline.py`) replacing `ccstatusline@latest`. Three lines: model + project + git branch (with dirty marker) · context compaction progress bar (`[████░░░░░░] NN%`) + `tok used` + cost · session % / reset + weekly % + `resets Fri … (N days)` (via cached `ccusage blocks`/`daily --json`). `CLAUDE_WEEKLY_LIMIT_TOK` defaults to 100M (Max-style); set `5000000` for Pro-style caps. Also `COMPACT_PCT`, `CTX_WINDOW`, `CCUSAGE_TOKEN_LIMIT`, `STATUSLINE_CACHE_TTL`. Wired into `.claude/settings.json`, `.claude/settings.json.tpl`, and `scripts/install.sh`.
- **Statusline fixes**: session `%` now defaults to current usage from `totalTokens/limit` without forcing `--token-limit max` (uses `CCUSAGE_TOKEN_LIMIT` only when explicitly set), and `.claude/statusline.py --debug` now prints a JSON diagnostic block with chosen session/week sources and raw denominators.

- **finops-audit**: JSON export capability with `--json`, `--both`, `--quiet` flags
  - Structured JSON reports with token aggregates (year/month/week/day)
  - Project and session-level breakdown
  - Configurable output path via `.claude/settings.json`
  - Backward compatible with existing markdown reports
  - Support for external tool integration (e.g., techspend visualizer)

- **Cursor rule** `.cursor/rules/graphify-context.mdc`: when `graphify-out*` exists at the project root (file or `graphify-out/` with `graph.json`), treat it as canonical architecture context; do not overwrite those artifacts.
- **CLAUDE.md**: same Graphify `graphify-out*` context rules plus existing `/graphify` skill trigger, under `## Graphify`.
- **graphify skill**: moved from `.claude/skills/graphify/` to `skills/graphify/`; `.claude/skills/graphify` and `.vibe/skills/graphify` are symlinks (same pattern as other skills). Cursor picks it up via `.cursor/skills` → `../skills`. Added `skills/graphify/.claude-plugin/plugin.json`, nested `skills/graphify/skills/graphify/SKILL.md` symlink, and marketplace entry.
- **graphify skill**: removed hardcoded uv clone path; resolve `GRAPHIFY_PROJECT` via env, `config/graphify.env`, `graphify-out/.graphify_project`, or **ask the user once** for the clone root. Added `config/graphify.env.example`, gitignore + `install.sh` bootstrap for `config/graphify.env`.

- **brain-route skill**: Session mode decision router that determines whether to run maintenance (brain-audit) or normal context load (brain-load) based on vault state
  - Decision rules: >7 days since last maintenance, >50 unprocessed raw files, or explicit --maintenance flag
  - Logs decision + reason to session context
  
- **brain-audit skill**: Comprehensive four-phase maintenance pipeline for Local Brain vault
  - **Phase 1**: Raw data compilation (raw → drafts → archive)
  - **Phase 2**: Connection detection (find orphaned notes, suggest semantic links)
  - **Phase 3**: Templated Q&A (run saved queries, auto-file results)
  - **Phase 4**: Digest generation + maintenance clock reset
  - All results appear in /inbox/ for human review + approval

- **Inbox/Journaling workflow**: New directory structure
  - `/inbox/drafts/` — raw data compiled into wiki articles (pending approval)
  - `/inbox/connections/` — suggested semantic links (pending approval)
  - `/inbox/qa/` — auto-filed query results (pending approval)
  - `/meta/last-maintenance.md` — tracks maintenance timestamp (7-day clock)
  - `/meta/queries/` — templated Q&A queries for automated synthesis

- **Integration**: brain-route wired into brain-sync session flow
  - brain-sync pull → brain-route decision → brain-audit OR brain-load
  - Seamless session start with no user configuration needed

### Removed

- **`notion-brain-sync` skill**: removed (`skills/notion-brain-sync/`). Notion ingest is no longer part of the standard workflow.
- **`token-watch` skill**: removed (`skills/token-watch/`).
- **`token-guard` skill**: removed (`skills/token-guard/`).

### Changed

- **Wiki source of truth**: switched from `docs/wiki/` stubs to direct `.wiki/` repository workflow. `scripts/update-wiki.sh` now commits/pushes local `.wiki/` changes.
- **CI**: removed dedicated wiki publish job from `ci.yml`; wiki updates are now explicit/manual via `scripts/update-wiki.sh` when needed.
- **Cleanup**: removed `docs/wiki/`, `.pre-commit-config.yaml`, and `requirements-dev.txt` from the wiki workflow path.
- **README**: Skills table updated; wiki process now points to local `.wiki/` + `scripts/update-wiki.sh`.
- **brain-sync**: Now calls brain-route after successful pull to determine session mode
- **brain-route / brain-audit**: ShellCheck clean — `SC1090`/`SC2155`/`SC2034` fixes in `_brain_env.sh`, `route.sh`, and `connect.sh`
- **finops-audit**: removed unused local variables in `skills/finops-audit/scripts/finops-audit.sh` to resolve ShellCheck `SC2034`.

## 2026-04-09

### Added
- New `server-audit` skill at `skills/server-audit/`.
- Robust audit script at `skills/server-audit/scripts/audit.sh` for local or SSH targets.
- Marketplace metadata for `server-audit` in `skills/server-audit/.claude-plugin/plugin.json`.
- Marketplace skill symlink at `skills/server-audit/skills/server-audit/SKILL.md -> ../../SKILL.md`.

### Changed
- `.claude/skills/*` now includes symlinks for all current repo skills, including `server-audit`.
- `.cursor/skills` symlink now points to shared `skills/`.
- `.claudeignore` now explicitly keeps `skills/`, `.claude/skills/`, and `.cursor/skills/` includable.
- `.gitignore` updated to version `.claude/settings.json` (while generation from `.claude/settings.json.tpl` is still supported).
- `.claude/settings.json` includes a `pre-commit` hook that blocks staged `.cursor` / `.vs` IDE files.
- `.gitignore` now ignores `.claude/logs/` and `.claude/usage-data/` runtime artifacts.
- `.claude/CLAUDE.md` adds operational guidance for remote-server verification and git hygiene.
- `server-audit` is upgraded to a config-driven parallel audit workflow with six dedicated check scripts and JSON aggregation.
- `.gitignore` now ignores `skills/server-audit/config/targets.json` and `skills/server-audit/out/` local runtime artifacts.
- Added documentation hygiene rules in both `.claude/CLAUDE.md` and `.cursor/rules/docs-hygiene.mdc`.
- `server-audit` now supports interactive startup prompts to choose checks/targets first, making the skill generic for marketplace users.
