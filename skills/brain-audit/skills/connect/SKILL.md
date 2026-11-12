---
name: connect
description: >-
  Link step. Uses QMD query to find vault notes related to each recently
  written patterns note and adds up to 3 [[wikilinks]] under ## Related.
  Use when: "find connections", "link my notes".
user-invocable: true
---

# brain-audit:connect

Link each pattern note that `compile` wrote to related notes. Vault references are `[[slug]]` wikilinks (filename, no folder, no `.md`) — Obsidian's graph only sees wikilinks. `compile` writes the notes. `brain-sync end` commits the vault. This step does neither.

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
command -v qmd || { echo "qmd not installed — run: npm install -g @tobilu/qmd"; exit 1; }
[[ -f "$QMD_INDEX_PATH" ]] || { echo "QMD index not found — run brain-audit:qmd-sync first"; exit 1; }
```

## Link

For each file changed in `resources/knowledge/patterns/` (the notes `compile` wrote or extended; list them with `git -C "$BRAIN_PATH" status --short resources/knowledge/patterns/`):

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd query "<1–2 sentence pattern summary>" 2>&1
```

`qmd query` (hybrid, LLM expansion) is more precise than `vsearch` here, but on CPU one query can take several minutes and outlive the Bash timeout: then use `qmd vsearch "…" -n 12` (seconds; its scores run lower, so take ≥ 0.45). Take up to 3 results with score ≥ 0.70 (`query`) that are specs, plans, architecture docs or project notes not already linked, and append them under `## Related` as `[[<slug>]]` (`qmd://brain/a/b/<slug>.md` → `[[<slug>]]`).

Report: notes linked, links added.
