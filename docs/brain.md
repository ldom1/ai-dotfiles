# Local Brain, hooks and rules

The memory layer (an Obsidian vault), the session hooks of each tool, and the shared agent rules. Back to the [README](../README.md).

## Project brain sync

Each project can carry a persistent knowledge layer — git-tracked in the project repo and mirrored in the Local Brain vault. Where session hooks run (Claude Code, Cursor Agent CLI), the agent loads it without manual prompting.

### Prerequisites

| Tool | Install | Required for |
|------|---------|--------------|
| `jq` | `apt install jq` / `brew install jq` | Central + per-project MCP settings merge |
| `uvx` | `pip install uv` | Running code-index-mcp (zero install) |
| `qmd` | `npm install -g @tobilu/qmd` | Semantic search over brain vault |

### QMD vault setup (one-time)

First, add `source ~/ai-dotfiles/config/brain.env` to your `~/.zshrc` (or `~/.bashrc`) so that `BRAIN_PATH` and `QMD_INDEX_PATH` are exported into every shell and inherited by Claude Code hooks:

```bash
echo 'source ~/ai-dotfiles/config/brain.env' >> ~/.zshrc
```

Then initialise the central embedding database:

```bash
source ~/ai-dotfiles/config/brain.env
mkdir -p "$(dirname "$QMD_INDEX_PATH")"
INDEX_PATH="$QMD_INDEX_PATH" qmd collection add "$BRAIN_PATH" --name brain
INDEX_PATH="$QMD_INDEX_PATH" qmd context add "qmd://brain" "Local Brain vault"
INDEX_PATH="$QMD_INDEX_PATH" qmd update --collection brain
INDEX_PATH="$QMD_INDEX_PATH" qmd embed --collection brain
```

After this, Claude can query vault notes semantically from any initialized project. The index and embeddings refresh automatically at session end via `brain-sync` (`qmd update` then `qmd embed`).

`qmd` must run on the same Node major that compiled its native deps (`better-sqlite3`). If Cursor (or another tool) injects a different `node` earlier on `PATH`, `qmd doctor` / `qmd embed` fail with `NODE_MODULE_VERSION` mismatch. Keep nvm's default Node first (`.zshenv` / end of `.zshrc` prepend `$NVM_BIN`); `brain-sync` also prepends the directory that hosts the `qmd` shim before embed.

### Setup

```bash
# 1. Tag the project
echo "my-project" > /path/to/project/.brain-project

# 2. Initialise
ai-dotfiles init /path/to/project
```

This creates `<project>/.claude/memory/` with template files, mirrors them to `$BRAIN_PATH/projects/my-project/`, and registers the project in `config/brain-projects.tsv`. `brain-sync` keeps both sides in sync when session hooks run (Claude Code always; Cursor Agent CLI with prewarm wrapper) — not automatically in Cursor IDE Agent.

### Centrally-managed MCP servers

`qmd`, `code-index-mcp`, and `graphify` are registered once, globally, instead of
being copy-pasted into every project:

- Claude Code: `~/.claude.json` (user scope) — all three servers
- Cursor: `~/.cursor/mcp.json` (global scope) — `qmd` only (see note below)

`ai-dotfiles init` / `ai-dotfiles upgrade` apply this automatically. Run
`ai-dotfiles mcp-sync` any time to re-apply by hand — e.g. after editing
`config/memory-templates/mcp-central-claude.json.tpl` or
`mcp-central-cursor.json.tpl`, or as a first-time bootstrap on a new machine. Each
sync fully replaces its own managed keys and leaves every other `mcpServers` entry
untouched; a `.bak` copy of the target file is written before every merge.

Project-specific servers (e.g. a project's own RapidAPI key) stay in that project's
own `.mcp.json` / `.cursor/mcp.json` — only servers meant for every project belong in
the central templates.

`code-index-mcp` and `graphify` rely on `${CLAUDE_PROJECT_DIR}` (Claude Code's own
per-session path variable) to resolve the active project from a global-scope entry.
Cursor's equivalent global-scope behavior is unconfirmed, so those two stay
per-project there instead: `graphify`'s Cursor entry is written by the graphify skill
per project; there's no Cursor entry for `code-index-mcp` at all.

### Knowledge files

| File | Purpose | When to update |
|------|---------|----------------|
| `OBJECTIVES.md` | Goals, scope, non-goals | Written once, refined rarely |
| `DESIGN.md` *(on demand)* | Original application intent, UX, and durable product workflows | When product/design intent changes |
| `ARCHITECTURE.md` | Stack decisions, key modules | When architecture changes |
| `DECISIONS.md` | Append-only ADR log | After every significant decision |
| `CONTEXT.md` | Current state: done / in-progress / open questions | At session end |
| `ROADMAP.md` | Feature backlog and priorities | When priorities shift |
| `API.md` *(on demand)* | External contracts and endpoints | When API changes |

`init` skips the two *on demand* files: copy them from `config/memory-templates/on-demand/` when a project has a product UX or a public API. `DESIGN.md` is the durable product/application baseline: original intent, UX, and workflows. `ARCHITECTURE.md` is the live technical map: stack, modules, data flow, and implementation trade-offs.

`settings.json` controls which files are injected by `brain-load` at session start (`read_on_session_start`, defaults to `OBJECTIVES.md` + `CONTEXT.md`). The rest are loaded on demand.

### Memory format

Each knowledge file follows [Open Knowledge Format](https://cloud.google.com/blog/products/data-analytics/how-the-open-knowledge-format-can-improve-data-sharing) conventions, adapted for agentic context (see also [Interpretable Context Methodology, 2025](https://arxiv.org/abs/2603.16021)):

- **Typed frontmatter** — `type:` and `updated:` fields on every file, enabling version-aware tooling and graph-level queries across the vault
- **Token budget** — a `<!-- keep this file under ~N words -->` comment per template guides Claude to keep context files lean for session injection
- **Backward-compatible evolution** — `upgrade` backfills missing frontmatter and new `## sections` from the template into existing files without touching content (`scripts/merge-memory-md.py`)
- **Cross-links over duplication** — `brain-init-project` instructs Claude to link related entries across files (e.g., `DECISIONS.md → ARCHITECTURE.md`) instead of repeating content

### Commands

```bash
ai-dotfiles init <path>              # initialise + register
ai-dotfiles upgrade <path>           # add missing files, backfill frontmatter and sections
ai-dotfiles upgrade --all            # upgrade all registered projects
ai-dotfiles sync <path>              # manual bidirectional rsync
ai-dotfiles sync --all               # sync all registered projects
ai-dotfiles merge-memory <path>      # backfill OKF frontmatter + missing sections only (no file additions)
ai-dotfiles merge-memory --all       # merge all registered projects
ai-dotfiles mcp-sync                 # (re)apply centrally-managed MCP servers (qmd, code-index, graphify)
```

`merge-memory` is the focused variant of `upgrade`: it runs only the structural backfill step (`merge-memory-md.py`) on existing files, without adding new files or touching MCP settings. Use it when you want to bring an older project's memory files up to the current template structure without triggering a full upgrade.

### Automatic sync (brain-sync)

`brain-sync start` pulls vault → project for all registered paths. `brain-sync end` pushes project → vault before the vault git commit. Strategy: `rsync --update` (newer mtime wins, no merge). If both copies of one file changed since the last sync, the older edit is overwritten; the vault's git history keeps committed versions. Unregistered projects are skipped silently.

**Who runs it:**

| Tool | Session automation |
|------|-------------------|
| **Claude Code** | Automatic — `.claude/hooks/brain-session-start.sh` / `brain-session-end.sh` (unchanged) |
| **Cursor IDE Agent** | **Off** — no automatic sync, load, or pitfalls injection |
| **Cursor Agent CLI** | **On by default** — see [Cursor Agent CLI brain hooks](#cursor-agent-cli-brain-hooks) below |

Invoke the `brain-sync` / `brain-load` skills manually when hooks are off or the user asks.

### Claude Code hooks

All hooks are declared in `.claude/settings.json.tpl` and always on:

- **SessionStart** `brain-session-start.sh`: settings drift check, vault pull, project note, pitfalls, vendored-skill update check, `/brain-audit` nudge. Output stays under 9.5 KB: Claude Code (observed on 2.1) swaps longer hook output for a file and a 2 KB preview, so pitfalls get only the bytes left and are cut at a line break. The last-exit log shrinks to one status line. Pitfalls are capped at 6,000 B when written (`scripts/check-pitfalls-budget.sh`); if the budget still runs out, whole sections are dropped and named.
- **SessionEnd** `brain-session-end.sh`: appends the session's metrics line (`scripts/harness-metrics.py`: counts, duration, cost, no conversation text) to `$BRAIN_PATH/meta/harness-sessions/<YYYY-MM>-<host>.jsonl`, then vault commit + push, warning if today has no session log. SessionStart exports `CLAUDE_SESSION_ID` to Bash calls. It gives the model no turn: run `/capture` before you quit.
  - `python3 -I scripts/harness-metrics.py history --vault "$BRAIN_PATH"` prints one JSON aggregate over all transcripts, the skill-usage log and the vault. Each number carries a label (`mesuré`, `déduit`, `incomplet`) and its source.
- **PreToolUse (Bash)** `hardline-check.py` (runs first): a tripwire for a short list of destructive commands. It is not a security boundary: it does not see variables, other interpreters or scripts written to a file.
  - Tier 1 (`deny`, in every mode): `rm -rf` on `/` or home, `mkfs`, `dd` or a redirect to a device, `find -delete` from `/` or home, a fork bomb. If you really want one, check the target, then run it yourself with `!`. The deny reason never repeats the command, so you cannot paste it by mistake.
  - Tier 2 (`ask`): force push to `main`/`master`, `git clean -x`/`-d` on the whole tree, `docker system|volume prune`, `docker volume rm`, `chmod -R 777`, a download piped to a shell. A tier-1 shape with a `$` or backtick target also asks.
  - Rules: `.claude/hooks/hardline-rules.json`. The hook header lists the known bypasses, and the tests assert that they pass.
  - `scripts/replay-bash-rules.py --days 14` replays past Bash calls through the rules and the template `ask` list. It prints the prompts per rule, session and day, and every prompt with an empty TP/FP label column.
- **PreToolUse (Bash)** `rtk-rewrite.sh`: rewrites commands to shrink their output.
- **PreToolUse (Bash)** `git-commit-check.sh`: rejects an off-list `type(scope)` in a `git commit -m` message. A heredoc or file message only gets a reminder.
- **PreToolUse (Skill)** `log-skill-usage.sh`: appends to `~/.claude/skill-usage.log`.
- **Stop / PreCompact**: the three sensor hooks below.

#### Sensor hooks

| Event | Script | What it does |
|-------|--------|--------------|
| Stop | `stop-check.sh` | If the repo has `.claude/stop-check` (one shell command) and the git tree has changes, runs it (`STOP_CHECK_TIMEOUT`, default 120 s). On failure it blocks the stop and returns the last 40 lines to the agent. It never blocks twice in a row (`stop_hook_active`); a timeout warns only. Runs are logged to `~/.claude/logs/stop-check.log`. |
| Stop | `compact-nudge.sh` | Reads the last request's context size from the transcript. Past 250k tokens (`COMPACT_NUDGE_START`), then every 100k (`COMPACT_NUDGE_STEP`), shows a one-line `/compact` reminder. Once per step per session. |
| PreCompact | `precompact-checkpoint.sh` | Appends a resume note to `$BRAIN_PATH/inbox/daily/checkpoints/<slug>/YYYY-MM-DD.md`: trigger, context size, branch, recent and unpushed commits, changed and edited files, running background agents, a recent tool error, user decisions, the last 5 requests with the assistant text they answer, and the last assistant message. Tokens are masked. `/capture` folds it into the session log, then deletes it. |

Opt a project into the Stop check:

```bash
echo 'ruff check . && pytest -x -q' > .claude/stop-check   # this repo uses shellcheck on changed *.sh
```

`.claude/stop-check` is a shell command that runs with your user's permissions at the end of every agent turn that left changes. A cloned repo can ship one, so the hook runs it only after you approve it:

```bash
! stop-check-trust          # in the Claude Code prompt, from the repo: prints the command, records the approval
stop-check-trust --list     # show all approvals
stop-check-trust --revoke   # remove the approvals of this repo
```

- Before approval, the hook skips the check, never blocks, and shows one message per session.
- The approval covers the command, not the file. A new command needs a new approval. Comment, blank-line, indentation and CRLF edits do not.
- Approvals live in `~/.claude/stop-check-trust` (`<sha256> <repo id>`). Worktrees of one repo share them.
- The template denies `stop-check-trust` to the agent. Read the command before you approve it.

Tests: `.claude/hooks/tests/` (part of the git-promotion gate). Run from the repo root: `uvx -q pytest -q -p no:cacheprovider .claude/hooks/tests`. The repo does not install `pytest`; `uvx` fetches it. CI does not run these tests.

### Shared agent rules (AGENTS.md)

`AGENTS.md` at the repo root is the single source of the rules Claude Code, Cursor and Mistral Vibe share. `.claude/CLAUDE.md` imports it (`@~/ai-dotfiles/AGENTS.md`) and adds Claude-only lines. `scripts/build-agent-rules.sh` (run by `install.sh`) generates `.cursor/rules/agents.mdc` (alwaysApply) and `.vibe/AGENTS.md` (`.vibe/bootstrap.md` + `AGENTS.md`); `install.sh` links `~/.vibe/AGENTS.md` to it, so Vibe gets the rules in every project. CI fails if a generated copy is stale. Edit `AGENTS.md`, never the generated files.

### Stack rules by path (Claude Code)

Stack rules live in the vault at `resources/knowledge/patterns/*-patterns.md`. A note with a `paths:` list in its frontmatter becomes a Claude Code rule:

- `install.sh` runs `scripts/link-pattern-rules.sh`. It symlinks each such note into `.claude/rules/<name>.md` (gitignored) and removes links whose note lost `paths:`.
- Claude Code loads the rule when Read, Write or Edit touches a matching file under the session's working directory. It does not load at launch, so SessionStart output does not grow.
- A Bash command such as `cat Dockerfile` or `git add .gitignore` does not trigger a rule. A file outside the working directory does not trigger a user-level rule.
- The links point at the notes, so rule edits are live. Run `install.sh` again after you add or remove `paths:` on a note.

Cursor and Vibe get no equivalent.

### Cursor Agent CLI brain hooks

Cursor **user hooks** (`.cursor/hooks.json`) run brain sync on the **Agent CLI** — not IDE Agent, not Cloud/remote IDE (`CURSOR_CODE_REMOTE=true` → skip).

**Turn-1 context:** use the zsh alias from **any directory** (no `cd` required):

```bash
alias agent='~/ai-dotfiles/scripts/cursor-agent-brain.sh'   # already in ~/.zshrc
agent   # from anywhere
```

Prewarm writes a global user rule `~/.cursor/rules/brain-hooks-session-inject.mdc` (alwaysApply) + sidecar. It does **not** touch repo-root `AGENTS.md` (the single source of shared rules). Verify: quote `[brain-hooks] sessionStart OK` without Reading files.

### Mistral Vibe hooks

`install.sh` links `~/.vibe/hooks.toml` to `.vibe/user-hooks.toml`. Vibe then runs three Claude Code sensors:

| Vibe hook | Type | Claude Code hook |
|-----------|------|------------------|
| `hardline` | `pre_tool` (bash), `strict` | `hardline-check.py` |
| `commit-scope` | `pre_tool` (bash), `strict` | `git-commit-check.sh` |
| `stop-check` | `post_agent`, 180 s | `stop-check.sh` |

`scripts/vibe-claude-hook.py <hook>` runs each one and translates the protocol:

- A Claude `deny` or Stop `block` becomes a Vibe `deny`. Exit 2 also becomes a `deny`, with stderr as the reason.
- A Claude `ask` becomes a `deny` that tells the model to ask the user. Vibe has no ask decision.
- `allow` and empty output pass. `systemMessage` becomes `system_message`.
- Any other output, or another exit code, is an adapter error (exit 1, details on stderr). The two `strict` hooks then deny the bash call.

Differences from Claude Code:

- A `stop-check` deny injects a retry message. Vibe allows 3 retries per hook per turn, then ends the turn.
- Vibe has no session-start hook. The vault sync and load stay manual (`.vibe/bootstrap.md`).

The file is not named `.vibe/hooks.toml`. In this trusted repo, Vibe would load it twice and warn about each duplicate hook name.
