---
name: connect
description: >-
  Two-phase vault connection step. Phase A: reads recent inbox/daily/
  implementation notes, clusters cross-project patterns by topic (Docker,
  Python, deployment, AI), and synthesizes knowledge files in
  resources/knowledge/ with [[wikilinks]] back to source notes.
  Phase B: uses QMD query to find additional related vault notes for each new
  knowledge file and adds [[wikilinks]]. Use when: "find connections",
  "link my notes", "synthesize patterns", "create knowledge files".
user-invocable: true
---

# brain-audit:connect

Turn patterns that recur across projects into knowledge files, then link them to related notes. Vault references are `[[slug]]` wikilinks (filename, no folder, no `.md`) — Obsidian's graph only sees wikilinks.

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
command -v qmd || { echo "qmd not installed — run: npm install -g @tobilu/qmd"; exit 1; }
[[ -f "$QMD_INDEX_PATH" ]] || { echo "QMD index not found — run brain-audit:qmd-sync first"; exit 1; }
```

## A — Synthesize

Read `inbox/daily/implementation/` notes from the last 30 days. A pattern earns a knowledge file only when **2+ projects** hit it (Docker, Python, deployment, observability, CI, auth, AI-agent tooling…). Say how many notes you actually read if you sampled.

Extend the matching existing file (`resources/knowledge/*-patterns.md`, `resources/knowledge/patterns/`) — append new patterns, never duplicate. Otherwise create `resources/knowledge/patterns/<topic>-patterns.md`:

```markdown
---
title: <Topic> Patterns
created: YYYY-MM-DD
tags: [knowledge, patterns, <topic>]
---

# <Topic> Patterns

## <Pattern name>

<2–3 sentences: the pattern and why it matters>

**Fix / best practice:** <concrete instruction>

### Observed in
- [[<session-log-slug>]] — <one-line context>
```

For each contributing project with a `projects/<slug>.md` note, add (if absent) `## See also` → `- [[<topic>-patterns]] — <pattern that applies>`.

## B — Link

For each file touched in A:

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd query "<1–2 sentence pattern summary>" 2>&1
```

`qmd query` (hybrid, LLM expansion) is more precise than `vsearch` here. Take up to 3 results with score ≥ 0.70 that are specs, plans, architecture docs or project notes not already linked, and append them under `## Related` as `[[<slug>]]` (`qmd://brain/a/b/<slug>.md` → `[[<slug>]]`).

## C — Review, then commit

The vault may hold other uncommitted work (today's session logs, other agents), so scope every git command to this run's files:

```bash
cd "$BRAIN_PATH"
git status --short resources/knowledge/ projects/
git diff -- resources/knowledge/ projects/
```

Show the diff plus new files and ask "Apply these knowledge files and links? (yes / no / edit)".

- **yes** → `git add <files touched> && git commit -m "brain-audit:connect — synthesize cross-project patterns $(date +%Y-%m-%d)"`
- **no** → `git checkout -- <modified files>` and delete the new files you created; never `git checkout -- .`
- **edit** → apply the user's changes, re-show the diff

Report: knowledge files created / updated, project notes linked, Phase B links added.
