---
name: connect
description: >-
  Two-phase vault connection step. Phase A: reads recent inbox/daily/
  implementation notes, clusters cross-project patterns by topic (Docker,
  Python, deployment, AI), and synthesizes new knowledge files in
  resources/knowledge/ with [[wikilinks]] back to source projects.
  Phase B: uses QMD query to find additional related vault notes for each new
  knowledge file and adds [[wikilinks]]. Use when: "find connections",
  "link my notes", "synthesize patterns", "create knowledge files".
user-invocable: true
---

# brain-audit:connect

Two phases: **synthesize** cross-project knowledge files, then **link** them to related vault notes via QMD.

> **Wikilink rule:** ALL internal vault references in every file written by this skill MUST use Obsidian wikilinks: `[[path/to/file]]` (vault-relative path, no `.md` extension, no leading slash). Never use markdown links `[text](path.md)` or plain paths — only wikilinks create backlinks in Obsidian's graph view. A broken or non-wikilink reference is invisible to the graph.

## Prerequisites

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
command -v qmd || { echo "qmd not installed — run: npm install -g @tobilu/qmd"; exit 1; }
[[ -f "$QMD_INDEX_PATH" ]] || { echo "QMD index not found — run brain-audit:qmd-sync first"; exit 1; }
```

---

## Phase A — Synthesize cross-project knowledge files

### Step A1 — Cluster patterns from recent implementation notes

Read all files in `$BRAIN_PATH/inbox/daily/implementation/` modified in the last 30 days. Group recurring patterns by topic:

| Topic | What to look for |
|---|---|
| **docker-patterns** | Docker/Podman volumes, compose, container file extraction, slim images |
| **python-patterns** | venv symlinks, uv in containers, asyncio/event loop, mypy, pylint |
| **deployment-patterns** | Vite base URL, Ansible, nginx sub-paths, static file extraction |
| **ai-agent-patterns** | Claude hooks, QMD, brain sync, session management, MCP |

Only create a knowledge file if **2 or more projects** hit the same pattern.

If you find a pattern that doesn't fit any existing topic file, create a new one in `$BRAIN_PATH/resources/knowledge/<topic>.md` using the same template. Good candidates: `ci-patterns.md`, `auth-patterns.md`, `database-patterns.md`, `frontend-patterns.md`. Use your judgment — if it recurred across projects, it deserves a file.

### Step A2 — Create or update knowledge files

For each cluster with ≥2 projects, write to `$BRAIN_PATH/resources/knowledge/<topic>.md`:

```markdown
---
title: <Topic> Patterns
created: YYYY-MM-DD
tags: [knowledge, patterns, <topic>]
---

# <Topic> Patterns

## <Pattern name>

<2-3 sentence description of the pattern and why it matters>

**Fix / best practice:** <concrete instruction>

### Observed in
- [[inbox/daily/implementation/<project>/<file>]] — <one-line context>
- [[inbox/daily/implementation/<project>/<file>]] — <one-line context>

---
```

If the file already exists, append new patterns only — do not duplicate existing ones.

### Step A3 — Add ## See also to project notes

For each project whose implementation notes contributed a pattern, add a `## See also` link in `$BRAIN_PATH/projects/<project>.md`:

```markdown
## See also
- [[resources/knowledge/<topic>]] — <pattern that applies>
```

Only add if the project note exists and the link is not already there.

---

## Phase B — Link knowledge files to related vault notes

For each knowledge file created or updated in Phase A:

### Step B1 — Run QMD hybrid query

Use `qmd query` (not `qmd vsearch`) — it uses LLM expansion for better precision on specific topics:

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd query "<topic summary, 1-2 sentences describing the pattern>" 2>&1
```

### Step B2 — Select links

From results, select up to **3 matches** that:
- Have score ≥ 0.70
- Are not already linked in the knowledge file
- Are specs, plans, architecture docs, or project notes (not raw implementation notes already in `## Observed in`)

Convert `qmd://brain/path/to/file.md` → `[[path/to/file]]`.

### Step B3 — Append ## Related to knowledge file

```markdown
## Related
- [[resources/knowledge/architecture/clawvis-architecture]]
- [[inbox/daily/specs/artelys-crystal-hpc/2026-04-29-dynamic-partition-management]]
```

---

## Step C — Show consolidated diff

```bash
cd "$BRAIN_PATH" && git diff
```

Show the diff to the user and ask: "Apply these knowledge files and links? (yes / no / edit)"

- **yes** → proceed to Step D
- **no** → `git checkout -- .`, report "no changes applied"
- **edit** → user specifies which to keep/remove, re-show diff

## Step D — Commit to vault

```bash
cd "$BRAIN_PATH"
git add resources/knowledge/ projects/
git commit -m "brain-audit:connect — synthesize cross-project patterns $(date +%Y-%m-%d)"
```

## Summary

```
brain-audit:connect complete
  Knowledge files created: N
  Knowledge files updated: N
  Project notes linked: N
  Phase B links added: N
```
