---
name: notion-brain-sync
description: >-
  Curates the Local Brain vault from Notion exports and user-provided decisions:
  PARA/CAPS placement, L1/L2/L3 routing, append-only log.md on every vault write,
  no hallucinated context. Use when the user shares Notion content, asks to ingest
  or sync notes into the Obsidian vault, or wants BrainSync-style maintenance of
  projects, CAPS, and resources.
user-invocable: true
---

# notion-brain-sync (BrainSync)

**Notion** = human workspace (raw, lived). **Local Brain** (`$BRAIN_PATH`) = git-backed Obsidian vault, AI-compiled memory. Do **not** merge the two into one tool or suggest replacing either.

## Source of truth

- Answer questions from vault files first; cite path and heading. Never invent project names, decisions, or personal facts absent from the Brain.
- Resolve `$BRAIN_PATH` like `brain-load` / `brain-sync`: `BRAIN_ENV_FILE`, `brain.env` beside skill scripts, or `config/brain.env` under ai-dotfiles.

## L1 / L2 / L3

| Layer | When | Examples |
|-------|------|----------|
| **L1** | Always hot | `IDENTITY.md`, `breadcrumbs.md`, active goals |
| **L2** | On demand | `caps/*.md`, `resources/` |
| **L3** | Depth / history | `projects/<slug>.md`, `index/implementation/<slug>/` (`YYYY-MM-DD-topic.md`), `archive/`, long specs under `resources/knowledge/...` |

**L1:** no edits without **explicit user confirmation**.

Routing table: `reference/LAYER-ROUTING.md`. Expected tree: `brain-load/reference/VAULT-LAYOUT.md`.

## `log.md` (required on every vault write)

- Path: **`$BRAIN_PATH/log.md`** (vault root).
- After **any** create or update of a file under the vault, append one line:
  `[YYYY-MM-DD] — <relative/path> — <short summary>`
- If `log.md` is missing, recreate a short header (purpose + format) then append the line.

## Ingestion workflow

1. Parse the user’s raw input (Notion export, paste, bullet decisions).
2. Classify **L1 / L2 / L3**; pick an **existing** target path—preserve PARA/CAPS; do not restructure or flatten notes unless the user explicitly asks.
3. Write **minimal, structured** content (no prose padding).
4. **Append `log.md`** for that change.
5. If appropriate, remind that **`brain-sync`** handles git pull/commit/push—do not duplicate `sync.sh` logic here.

## Proactive suggestions

When the user discusses recent work or shares Notion material, offer bullets: **item → proposed layer (L1/L2/L3) → target file**—without applying L1 changes without confirmation.

## Reply format (when applying this skill)

- **Full-file vault edits:** return the complete updated file in a fenced block; first line of the fence = file path.
- **Ingestion suggestions:** bullet list with layer + target file.
- **Log:** show the new `log.md` line(s) to append (or the tail of `log.md` if returning full file).
- **Structural advice:** numbered list, **max 5** steps, scoped and actionable.

## Constraints (checklist)

- Do not rename or reorganize vault folders/files unless the user explicitly requests it.
- Do not edit L1 files without explicit confirmation.
- Do not hallucinate Brain content.
- Keep Brain writes concise and structured.

## Manual trigger

**`/notion-brain-sync`** loads this skill. It does not run shell by itself.

## Files

```
skills/notion-brain-sync/
├── SKILL.md
├── .claude-plugin/plugin.json
└── reference/
    └── LAYER-ROUTING.md
```
