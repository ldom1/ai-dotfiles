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

## Ontologie

Check the three levels of `$BRAIN_PATH/ontologie/` (concepts, sujets, technologies):

```bash
uv run --script ~/ai-dotfiles/scripts/ontologie.py activity
uv run --script ~/ai-dotfiles/scripts/ontologie.py check
uv run --script ~/ai-dotfiles/scripts/ontologie.py mentions
```

- Fix every `FAIL` line: correct the link or the line of the project note. Never fix a `FAIL` by creating a note.
- Report every `WARN` line: an element that no project and no ontologie note links.
- `mentions` writes the last section `## Dans le vault` of each element again: the projects that use it and the notes that name it. It takes one to four minutes on a vault of 1,700 notes. Never edit that section: write your own text above it. To correct a wrong match, edit the property `match` of the element (a list of regular expressions).
- Look for two notes that are one element (a synonym, an English and a French name). Do not merge them yourself: propose the pair in a review item (`type: arbitrage`). After the owner agrees, keep one note, add the other name to its `aliases`, repoint the links and move the other note to `archive/`.
- Never create a note in `ontologie/` that the owner did not accept, and never write `level`.

Report: notes linked, links added, ontologie `FAIL` and `WARN` counts, pairs proposed.
