---
name: notion-brain-sync skill
overview: Add `notion-brain-sync` under `~/ai-dotfiles/skills/`, create vault-root `log.md` in the Local Brain with a documented format, run a read-only audit of the vault tree vs `VAULT-LAYOUT.md`, and deliver a short structural review (gaps, L1/L2/L3 fit, max five actions).
todos:
  - id: vault-structure-audit
    content: Inventory Local Brain top-level + key subtrees; compare to `brain-load/reference/VAULT-LAYOUT.md`; map to L1/L2/L3; note drift (e.g. `index/`, `inbox/`, `raw/`, `meta/`, `archive/processed/`, `daily/` status); output concise review + max 5 recommendations
    status: completed
  - id: vault-log-md
    content: Create `/mnt/c/Users/louis/Documents/Local Brain/log.md` with 2–5 line purpose header + format rule; append first entry `[YYYY-MM-DD] — log.md — init Brain change log (notion-brain-sync)`
    status: completed
  - id: add-skill-md
    content: Create `skills/notion-brain-sync/SKILL.md` with YAML frontmatter + BrainSync rules (L1/L2/L3, log.md path + append rule, constraints, output formats, index/implementation L3 note)
    status: completed
  - id: optional-reference
    content: Add `reference/LAYER-ROUTING.md` optional routing table if SKILL.md would be too long
    status: completed
  - id: optional-plugin-readme
    content: Add `.claude-plugin/plugin.json` and/or README skill row for discoverability, matching repo patterns
    status: completed
isProject: false
---

# Add `notion-brain-sync` skill to ai-dotfiles

## Goal

1. **Skill**: Create [`/home/lgiron/ai-dotfiles/skills/notion-brain-sync/SKILL.md`](file:///home/lgiron/ai-dotfiles/skills/notion-brain-sync/SKILL.md) (and optional `reference/` + `plugin.json`) so agents loading it behave as **BrainSync**.
2. **Vault `log.md`**: Add [`log.md`](/mnt/c/Users/louis/Documents/Local Brain/log.md) at the **vault root** as the append-only ledger for every Brain file create/update the agent performs (not a substitute for git history—operational trace for “what changed and why”).
3. **Structure audit**: Before or alongside the skill write, **review the current Local Brain layout** against the expected PARA layout in [`VAULT-LAYOUT.md`](file:///home/lgiron/ai-dotfiles/skills/brain-load/reference/VAULT-LAYOUT.md) and produce a **short audit** (present vs missing vs unexplained dirs, L1/L2/L3 mapping, inconsistencies with `index/README.md` / CAPS / `projects/`), ending with **at most five** actionable, scoped recommendations (no restructure unless the user later approves).

## Conventions to mirror

- **Frontmatter**: Same pattern as [`brain-sync/SKILL.md`](file:///home/lgiron/ai-dotfiles/skills/brain-sync/SKILL.md) and [`brain-load/SKILL.md`](file:///home/lgiron/ai-dotfiles/skills/brain-load/SKILL.md): `name`, `description` (third person, trigger-rich: Notion, export, ingest, PARA, CAPS, L1/L2/L3), optional `user-invocable: true` for a **`/notion-brain-sync`**-style manual load (consistent with `.vibe` docs).
- **Optional plugin stub**: [`brain-sync/.claude-plugin/plugin.json`](file:///home/lgiron/ai-dotfiles/skills/brain-sync/.claude-plugin/plugin.json) — duplicate structure for `notion-brain-sync` if you want parity with other packaged skills (name/version/description/homepage).
- **No shell script required** unless you later automate something; this workflow is agent-driven (contrast with `brain-sync/scripts/sync.sh`).

## Vault alignment (from existing docs)

- **Layout reference**: [`brain-load/reference/VAULT-LAYOUT.md`](file:///home/lgiron/ai-dotfiles/skills/brain-load/reference/VAULT-LAYOUT.md) — PARA paths (`projects/`, `caps/`, `resources/`, `archive/`, `IDENTITY.md`, `breadcrumbs.md`, etc.).
- **Implementation history**: Your vault’s [`index/README.md`](/mnt/c/Users/louis/Documents/Local Brain/index/README.md) says session writeups belong under `index/implementation/<project-slug>/` with `YYYY-MM-DD-topic.md` — the skill should treat **deep session / implementation logs** as L3 aligned with that tree (not the old `daily/implementation/` path).
- **`log.md` (vault file, created during execution)**  
  - **Path**: `$BRAIN_PATH/log.md` (same as [`Local Brain`](/mnt/c/Users/louis/Documents/Local Brain) repo root).  
  - **Top of file**: Brief note that each line is one change; format `[YYYY-MM-DD] — <relative/path> — <summary>`.  
  - **First line after header**: One log entry recording creation of `log.md` itself (meta bootstrap).  
  - **Skill text**: Reiterate that any future Brain write must append a new line (same format); if the file is missing, recreate header + continue.

## Vault structure audit (execution deliverable)

Read-only steps (no renames/moves):

1. **Inventory**: List vault root directories and notable files (`IDENTITY.md`, `breadcrumbs.md`, `projects/`, `caps/`, `resources/`, `index/`, `inbox/`, `raw/`, `meta/`, `archive/`, `todo/`, `daily/`, etc.).
2. **Compare**: Check each against [`VAULT-LAYOUT.md`](file:///home/lgiron/ai-dotfiles/skills/brain-load/reference/VAULT-LAYOUT.md) (expected PARA tree) and your [`index/README.md`](/mnt/c/Users/louis/Documents/Local Brain/index/README.md) convention for L3 implementation notes.
3. **Classify**: Tag major areas as **L1 / L2 / L3** (hot vs on-demand vs deep) and call out **orphan or ambiguous** trees (e.g. untracked `inbox/` vs `resources/`).
4. **Git-aware context**: Note obvious drift from snapshot status if still relevant (e.g. deleted `daily/*.md`, new folders) without treating git as the only source of truth.
5. **Output**: A compact **audit section** in the session summary (bullet findings + **numbered recommendations, max 5**). Do **not** add a new vault doc for the audit unless the user asks—default is conversational deliverable only, to avoid extra markdown surface area.

## SKILL.md body — sections to include

1. **Role & split**: Notion = human workspace / raw; Local Brain = AI-readable compiled memory. Never merge the two systems into one tool.
2. **Source of truth**: Answer from Brain files first; cite path/section; do not invent projects, decisions, or personal facts.
3. **L1 / L2 / L3 model** (map to concrete paths, consistent with your message + vault):
   - **L1** (always hot): e.g. `IDENTITY.md`, active goals, current project pointers (`breadcrumbs.md` or equivalent). **Require explicit user confirmation before any L1 edit.**
   - **L2** (on demand): `caps/`, `resources/` (and similar reference notes).
   - **L3** (implementation / depth): `projects/<slug>.md`, `index/implementation/…`, archives, long specs.
4. **Ingestion workflow** (stepwise): parse raw input → classify layer → pick target file under existing folders → **minimal, structured** insert (no prose padding) → **append `log.md`** → suggest `brain-sync` / git when appropriate (point to existing `brain-sync` skill, no duplication of `sync.sh` logic).
5. **Constraints** (bullet checklist): no vault-wide renames/restructures without explicit ask; no L1 without confirmation; no hallucination; preserve PARA/CAPS; do not flatten or restructure existing notes without instruction.
6. **Output format contract** (for the agent’s replies): match your spec — full file in fenced block with path header when replacing a whole file; bullet ingestion suggestions with layer + target file; separated log block; numbered structural recommendations (max 5) when giving vault advice.

## Optional `reference/` file

- **`reference/LAYER-ROUTING.md`**: One-page table (decision type → L1 vs L2 vs L3 → example paths). Keeps `SKILL.md` shorter and easier to maintain.

## Repo integration (after file creation)

- If your install flow symlinks skills into `.claude/skills/` or `.vibe/skills/`, add **`notion-brain-sync`** the same way as `brain-load` / `brain-sync` (verify your local installer or README in ai-dotfiles — paths differ per machine).
- Optionally add one line to [`README-BRAIN-SYSTEM.md`](file:///home/lgiron/ai-dotfiles/README-BRAIN-SYSTEM.md) or [`README.md`](file:///home/lgiron/ai-dotfiles/README.md) under the skills table so the skill is discoverable for humans.

## Out of scope for this change

- **Vault edits beyond `log.md`** (no bulk moves, no L1 edits without confirmation, no fixing git working tree unless explicitly requested).
- Cursor workspace skill copy under `~/.cursor/skills/` — only if you want Cursor-native discovery outside ai-dotfiles; primary deliverable is **`~/ai-dotfiles/skills/notion-brain-sync/`**.
