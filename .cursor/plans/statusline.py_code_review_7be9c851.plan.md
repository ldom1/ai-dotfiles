---
name: statusline.py code review
overview: The pasted “pyccsl” script and the repository’s current [.claude/statusline.py](.claude/statusline.py) are not the same file. This plan documents a technical review of the pasted pyccsl implementation and calls out the mismatch so you can reconcile versions before any edits.
todos:
  - id: reconcile-target
    content: Confirm whether review applies to pasted pyccsl, workspace .claude/statusline.py, or a merge/replace goal
    status: completed
  - id: verify-usage-semantics
    content: Validate transcript usage fields (cumulative vs delta) against a real JSONL sample before trusting token totals and cache hit rate
    status: completed
  - id: harden-edge-cases
    content: "If implementing fixes: timestamp parsing, powerline ANSI nesting, unknown model pricing display, optional transcript tailing"
    status: completed
isProject: false
---

# Review: pasted pyccsl vs workspace `statusline.py`

## File mismatch (read this first)

- **Workspace file** [.claude/statusline.py](.claude/statusline.py) is a ~445-line, typed script: 3-line status output, `last_ctx_tokens` via tail read of `transcript_path`, session block math from `~/.claude/projects/*.jsonl`, weekly totals, `git -C`, and optional `--debug` JSON dump. It does **not** contain `PRICING_DATA`, `THEMES`, `FIELD_ORDER`, or `__version__ = "0.9.36"`.
- **Your paste** is a standalone “pyccsl” statusline (themes, powerline, embedded pricing table, `argparse`, `parse_env_file`, `calculate_total_cost`, performance badge, etc.).

If the goal is to change the repo’s hook script, confirm whether you intend to **replace** the current file with pyccsl, **merge** behaviors, or keep pyccsl elsewhere and only wanted a review of the paste.

---

## Review of the pasted pyccsl (strengths)

- **Clear contract**: stdin JSON, exit codes documented, `read_input` rejects TTY/empty input.
- **Env file hardening**: [`parse_env_file`]( pasted ) only ingests keys prefixed with `PYCCSL_`, which reduces arbitrary config injection compared to sourcing arbitrary shell.
- **Cost attribution**: [`calculate_total_cost`]( pasted ) walks transcript in order, tracks `last_model_id`, and uses `parentUuid` → parent assistant message to price [`toolUseResult.usage`]( pasted )—this is the right shape for mixed-model sessions.
- **Git isolation**: [`extract_git_status`]( pasted ) uses `cwd` from input JSON (`input_data.get("cwd", os.getcwd())`), which matches typical hook payloads better than always using process CWD.

---

## Issues and risks (ordered by severity)

### 1) Token totals may be wrong if usage is cumulative (not per-turn delta)

[`calculate_token_usage`]( pasted ) sums `usage.*` across every assistant / tool result line. Many systems emit **cumulative** session usage on each assistant message; summing then **overcounts** badly. Same risk for [`cache_hit_rate`]( pasted ) built from those totals.

**Mitigation direction**: use only the **last** assistant `message.usage` snapshot (or last line with usage), or diff consecutive snapshots if the format is cumulative—verify against a real Claude Code transcript JSONL sample.

### 2) `avg_response_time` pairing logic can skew or be zero incorrectly

[`calculate_performance_metrics`]( pasted ) pairs each assistant message with `max(user_timestamps before assistant)`. That ignores tool-only turns, parallel assistants, or multiple users before one assistant; it can attribute latency to the wrong user message. The `0 < response_time < 300` filter drops long runs entirely from the average.

### 3) Bare `except` when parsing timestamps

Same function uses `except: continue` around `datetime.fromisoformat`, which hides bugs and can silently drop all timing data.

### 4) Powerline badge path vs segment builder mismatch

[`calculate_performance_badge(..., powerline=True)`]( pasted ) returns a **prefix string that intentionally omits `RESET`**, while non-powerline badge uses `apply_color` with `RESET` per dot. [`format_output`]( pasted ) powerline branch then wraps badge text in `apply_color(f" {text} ", fg=0, bg=...)` which may **nest/override** ANSI state in surprising ways depending on terminal. Comments in the badge function also say “white background” while using gray `48;5;244m`.

### 5) Configuration precedence is easy to misread

Comment says env file overrides are “higher priority than command line”, but `argparse` already consumed argv; the code then overwrites selected fields from the env file. That is consistent with the comment, but **surprising UX** (CLI flags partially ignored when `--env` sets the same key).

### 6) Theme value from env file is not validated

If `PYCCSL_THEME` in the env file is misspelled, `THEMES.get(config["theme"], {})` yields `{}` and behaves like “no colors” for many paths—not the same as explicit `"none"` theme handling everywhere.

### 7) Embedded pricing drifts

[`PRICING_DATA`]( pasted ) will inevitably fall behind [Anthropic pricing](https://docs.anthropic.com/en/docs/about-claude/pricing) and behind **new model IDs** (Sonnet 4.5, etc.). Unknown models yield **$0** cost silently (except debug), which is worse than showing “unknown”.

### 8) Performance: full-file transcript read

[`load_transcript`]( pasted ) reads the entire JSONL. Large sessions can make the statusline feel sluggish; your repo’s current `statusline.py` already uses tailing strategies for hot paths.

### 9) Minor / polish

- **Detached HEAD**: `git rev-parse --abbrev-ref HEAD` often returns `HEAD`; you may want `git symbolic-ref -q --short HEAD` fallback messaging.
- **`parse_env_file` exception scope**: broad `except Exception` swallows `KeyboardInterrupt` only if raised during read (rare), but pattern is otherwise acceptable for a statusline.
- **`FIELD_ORDER` vs user field order**: user cannot reorder fields via CLI beyond filtering; documented or accepted limitation.

---

## Suggested verification (before changing production hook)

- Capture one real `transcript_path` JSONL and assert whether `message.usage` values are **per-step** or **cumulative** (diff consecutive assistant lines).
- Golden tests for: cost split across model switch mid-session; tool result usage priced via `parentUuid`; powerline output byte length/ANSI state; git clean/dirty and not-a-repo.

---

## If you want implementation follow-up

Tell me which target you want:

1. **Review-only** of the paste (no repo changes), or  
2. **Align repo** [.claude/statusline.py](.claude/statusline.py) with pyccsl (replace/merge), or  
3. **Fix specific bugs** in pyccsl in a new file / branch.
