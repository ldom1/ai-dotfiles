---
name: brain-audit
description: >-
  Autonomous four-phase maintenance pipeline for the Local Brain vault.
  Use when brain-route decides maintenance mode, when the user runs /brain-audit,
  or whenever vault maintenance, brain cleanup, or weekly digest generation is
  requested. Trigger on: "clean up my brain", "run vault maintenance", "generate
  the weekly digest", "audit my notes", or any request to process raw notes.
user-invocable: true
---

# brain-audit

Four-phase pipeline that keeps the Local Brain vault organized and current. Run when `brain-route` decides maintenance mode, or on demand.

## Quick start

```bash
# Full audit (all 4 phases)
bash ~/ai-dotfiles/skills/brain-audit/scripts/audit.sh

# Individual phases
bash ~/ai-dotfiles/skills/brain-audit/scripts/compile.sh   # raw → articles
bash ~/ai-dotfiles/skills/brain-audit/scripts/connect.sh   # orphan detection
bash ~/ai-dotfiles/skills/brain-audit/scripts/qa.sh        # templated Q&A
bash ~/ai-dotfiles/skills/brain-audit/scripts/digest.sh    # weekly digest
```

## What each phase does

| Phase | Script | Input | Output |
|-------|--------|-------|--------|
| 1 — Compile | `compile.sh` | Raw markdown in `raw/`, inbox clippings | Draft articles in `inbox/drafts/` |
| 2 — Connect | `connect.sh` | All vault files | Orphan list + suggested links in `inbox/connections/` |
| 3 — Q&A | `qa.sh` | Vault state snapshot | Structured answers in `inbox/qa/` |
| 4 — Digest | `digest.sh` | Phases 1–3 counts | Weekly summary in `resources/queries/archive/`; resets maintenance clock |

## Configuration

`BRAIN_PATH` must point to a git repository (your Obsidian vault). Loaded from the first match:

1. `BRAIN_ENV_FILE` env var → env file containing `BRAIN_PATH=…`
2. `brain.env` beside `scripts/` — standalone usage
3. `config/brain.env` at the ai-dotfiles root — default install

```bash
grep BRAIN_PATH ~/ai-dotfiles/config/brain.env
```

## Human review checkpoints

After running, present results to the user at each phase output:

1. **Phase 1:** Drafts in `inbox/drafts/` — ask to review, approve, or revise before publishing.
2. **Phase 2:** Orphans and suggestions in `inbox/connections/` — let the user decide: merge, archive, or keep.
3. **Phase 3:** Q&A results in `inbox/qa/` — validate, extract action items.
4. **Phase 4:** Digest in `resources/queries/archive/` — confirm accuracy, then remind user to run `brain-sync end` to commit.

## On failure

- Missing or invalid `BRAIN_PATH` → warn once, stop.
- Individual phase failure → report the error, ask whether to continue with remaining phases.
- `audit.sh` exits 1 on any phase failure; individual scripts can be re-run standalone.

## Files

```
skills/brain-audit/
├── SKILL.md
├── scripts/
│   ├── audit.sh          ← orchestrates all 4 phases
│   ├── compile.sh        ← phase 1: raw data → draft articles
│   ├── connect.sh        ← phase 2: orphan detection + link suggestions
│   ├── qa.sh             ← phase 3: templated Q&A queries
│   ├── digest.sh         ← phase 4: digest generation + clock reset
│   └── _brain_env.sh     ← config loader (sourced by all scripts)
└── reference/
    ├── PHASES.md         ← detailed phase documentation
    ├── brain.env.example ← configuration template
    └── queries/          ← Q&A templates for phase 3
```

Read `reference/PHASES.md` for detailed documentation on each phase.

## Integration

- **brain-route** → calls this skill when maintenance mode is triggered
- **brain-sync** → run before and after; `audit.sh` does not pull/push itself
