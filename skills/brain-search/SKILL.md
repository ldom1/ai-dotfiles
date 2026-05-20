---
name: brain-search
description: >
  Search the Local Brain Obsidian vault semantically to retrieve past decisions,
  architecture docs, specs, lessons learned, project history, or any knowledge
  stored in the vault. Use this skill proactively whenever the conversation touches
  something that may have been documented or decided before — even if the user
  hasn't explicitly asked to search. Trigger on: "what did we decide about X",
  "is there a spec for Y", "how did we handle Z before", "check the brain",
  "look up in the vault", "do we have notes on", "what does the brain say about",
  or whenever retrieving past context would improve your answer.
user-invocable: true
---

# brain-search

Retrieve relevant notes from the Local Brain vault using semantic or keyword search.

## How to run a search

Use the bundled script — it handles env loading, validation, and mode selection:

```bash
bash ~/ai-dotfiles/skills/brain-search/scripts/search.sh "<query>"
```

| Mode flag | When to use | Speed |
|-----------|-------------|-------|
| _(none / `--search`)_ | Exact term lookup, known file names | Instant — default |
| `--vsearch` | Semantic concept search | Fast after first run* |
| `--query` | Best quality, ambiguous queries | Slower after first run* |

```bash
# Keyword (instant, no models)
bash .../search.sh "QMD_INDEX_PATH hook export"

# Semantic (downloads reranker ~600MB on first use, then cached)
bash .../search.sh --vsearch "session start context injection pitfall"

# Hybrid best-quality (downloads expansion model ~1.3GB on first use, then cached)
bash .../search.sh --query "why did we replace the statusline script"

# Limit results
bash .../search.sh --vsearch --limit 5 "auth middleware compliance"
```

\* ML models are downloaded to `~/.cache/qmd/models/` on first use. Subsequent runs are local and fast.

Formulate a focused query that captures the concept, not just keywords. Prefer `"auth middleware session token storage compliance decision"` over `"auth"`.

## Reading a full document

If a result looks relevant but the excerpt is truncated:

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd get qmd://brain/<path/to/file.md>
```

## Interpreting results

- Score ≥ 85 %: highly relevant — treat as authoritative context
- Score 65–84 %: probably relevant — skim the excerpt to confirm
- Score < 65 %: weak match — use only if nothing better surfaced

Each result shows the vault-relative path (`qmd://brain/...`) and a context window around the match. The path tells you which area of the vault the note lives in:

| Path prefix | Content |
|-------------|---------|
| `resources/operational/ai-agents/` | Claude operating rules, pitfalls, finops |
| `projects/<slug>.md` | Per-project notes (brief, decisions) |
| `inbox/daily/implementation/` | Session implementation logs |
| `inbox/daily/specs/` | Design docs and brainstorming |
| `inbox/daily/plans/` | Implementation plans (task lists) |
| `resources/knowledge/` | Deep reference knowledge |
| `consolidation/` | Periodic synthesis digests |

## Presenting results to the user

Summarise what you found — don't dump raw qmd output. Cite the source path so the user can verify. If a result directly answers their question, quote the relevant passage. If nothing useful surfaced, say so explicitly rather than speculating.
