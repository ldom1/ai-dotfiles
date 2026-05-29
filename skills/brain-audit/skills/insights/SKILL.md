---
name: insights
description: >-
  Retrieves relevant vault notes via QMD + direct grep, then Claude synthesizes
  cross-project insights and writes a dated report to inbox/insights/YYYY-MM-DD.md.
  QMD is the retrieval layer only — Claude reads the returned files and generates
  all synthesis. Use when: "insights", "what patterns", "what blockers",
  "synthesize vault", "weekly insights".
user-invocable: true
---

# brain-audit:insights

## How this works

**QMD = retrieval only. Claude = synthesis.**

QMD finds which vault files are relevant to each question. Claude reads those files in full, combines them with direct grep findings, and writes the synthesized prose. QMD never generates text — it returns scored file excerpts with paths. Do not summarize QMD excerpts directly; always follow the paths and read the full source.

**ALL internal vault references MUST be Obsidian wikilinks: `[[path/to/file]]`** (vault-relative path, no `.md` extension, no leading slash). Never use markdown links (`[text](path.md)`) or plain paths for internal references — only wikilinks create the Obsidian backlink graph. A link that isn't a wikilink is invisible to Obsidian's graph view and backlinks panel.

---

## Prerequisites

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
command -v qmd || { echo "qmd not installed"; exit 1; }
[[ -f "$QMD_INDEX_PATH" ]] || { echo "QMD index not found — run brain-audit:qmd-sync first"; exit 1; }
```

---

## Step 1 — Discover query templates

```bash
find "$BRAIN_PATH/meta/queries" -name "*.md" 2>/dev/null | sort
```

If no templates exist, use these defaults:

```
1. What patterns of failure appear repeatedly across projects?
2. What architectural decisions were reversed or regretted?
3. What unresolved follow-ups exist in implementation notes?
4. What new tools or approaches were adopted this month?
5. What cross-project blockers remain unresolved?
```

---

## Step 2 — Retrieve for each query

Use the right retrieval method per question type:

### QMD — for conceptual / semantic questions

Use when the question is open-ended: "what patterns", "what was adopted", "what decisions".

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd query "<question text>"
```

- Take the top 5 results (score ≥ 0.60)
- For each result, note the `qmd://brain/...` path
- **Read those files in full** using the Read tool — the excerpt shown by QMD is a chunk, not the whole note
- Do NOT synthesize from QMD excerpts alone

**First-run note:** `qmd query` downloads a ~640MB LLM expansion model to `~/.cache/qmd/models/` on first use (~5–10 min on slow connection). Subsequent runs are fast (model is cached).

### Direct scan — for structured / enumerable questions

Use when the question asks for lists: "what follow-ups", "what decisions", "what blockers".

```bash
# Unresolved follow-ups in implementation notes
grep -rn "^## Follow-ups" "$BRAIN_PATH/inbox/daily/implementation/" --include="*.md" -l \
  | sort -r | head -20 \
  | xargs -I{} bash -c \
    'echo "=== {} ===" && grep -A 15 "^## Follow-ups" "{}" | grep "^- " | grep -iv "none"'

# Recent decisions (lessons-learned)
grep -A 4 "^## 202" "$BRAIN_PATH/resources/operational/ai-agents/lessons-learned.md" | head -60

# Open action items in insights (carry-forward from previous run)
grep "^- \[ \]" "$BRAIN_PATH/inbox/insights/"*.md 2>/dev/null | tail -20
```

Direct grep is more reliable than QMD for structured list content — it surfaces exact items, not semantic matches.

---

## Step 3 — Claude synthesizes each answer

For each query:
1. Combine: QMD-returned files (read in full) + direct scan output + knowledge of the vault from the current audit session
2. Write 2–4 sentences. Be specific: name projects, files, dates, concrete items
3. List the source `[[wikilinks]]` you drew from
4. Extract any concrete action items

**What good synthesis looks like:**
- Names 2+ specific projects/files that evidence the answer
- Includes a date or recency signal ("last 30 days", "this month", "2026-05-27")
- Ends with a concrete implication or next step
- Does NOT say "according to QMD" or quote chunk text verbatim

---

## Step 4 — Write insights file

Write to `$BRAIN_PATH/inbox/insights/YYYY-MM-DD.md`:

```markdown
---
date: YYYY-MM-DD
type: insights
source: brain-audit:insights
---

# Vault Insights — YYYY-MM-DD

## <Query title>

<2-4 sentences. Specific projects, dates, files. Concrete implication.>
Sources: [[path/to/note1]], [[path/to/note2]]

---

## <Next query title>

<synthesis>
Sources: [[path/to/note]]

---

## Action Items
- [ ] <Specific, named, actionable item — not vague>
- [ ] <Another item>
```

---

## Step 5 — Summary

```
brain-audit:insights complete
  Queries run: N
  Sources read: N files
  Insights written to: inbox/insights/YYYY-MM-DD.md
  Action items identified: N
```
