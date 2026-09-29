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

QMD finds which notes are relevant; you read them in full and write the synthesis. QMD excerpts are chunks, so always open the source before drawing a conclusion. Vault references are `[[slug]]` wikilinks.

```bash
source ~/ai-dotfiles/skills/brain-audit/scripts/_brain_env.sh
command -v qmd || { echo "qmd not installed"; exit 1; }
[[ -f "$QMD_INDEX_PATH" ]] || { echo "QMD index not found — run brain-audit:qmd-sync first"; exit 1; }
```

## Questions

1. What failure patterns repeat across projects?
2. What architectural decisions were reversed or regretted?
3. What follow-ups in implementation notes are still unresolved?
4. What new tools or approaches were adopted this month?
5. What cross-project blockers remain open (incl. security debt such as unrotated credentials)?

## Retrieve

Open-ended questions (1, 2, 4) → semantic search, then read the top ~5 results (score ≥ 0.60) in full. The first `qmd query` run downloads its expansion model; on CPU a query can outlive the Bash timeout — use `qmd vsearch` (seconds, scores ~0.1 lower) if so.

```bash
INDEX_PATH="$QMD_INDEX_PATH" qmd query "<question>"
```

Enumerable questions (3, 5) → scan directly; grep surfaces exact items where semantic search returns look-alikes. Session logs use a `**Follow-ups:**` field (older ones a `## Follow-ups` heading).

```bash
CUTOFF=$(date -d '-30 days' +%Y-%m-%d 2>/dev/null || date -v-30d +%Y-%m-%d)
find "$BRAIN_PATH/inbox/daily/implementation" -name '*.md' -newermt "$CUTOFF" | sort | while read -r f; do
  items=$(awk '/^(## |\*\*)Follow-ups/{on=1; next} on && /^(## |\*\*[A-Z])/{on=0} on && /^- / && !/[Nn]one/' "$f")
  [[ -n "$items" ]] && printf '=== %s\n%s\n' "${f#$BRAIN_PATH/}" "$items"
done
cat "$BRAIN_PATH/resources/operational/ai-agents/pitfalls.md"          # current cross-project rules
grep -h '^- \[ \]' "$BRAIN_PATH/inbox/insights/"*.md 2>/dev/null | tail -20   # carry-over action items
```

## Write `inbox/insights/YYYY-MM-DD.md`

Per question: 2–4 sentences naming the projects, notes and dates that evidence the answer, ending with the implication; then `Sources: [[slug]], [[slug]]`. Don't quote chunk text or cite "QMD". Finish with `## Action Items` — specific `- [ ]` items, carry-overs from the previous report included if still open.

```markdown
---
date: YYYY-MM-DD
type: insights
source: brain-audit:insights
---

# Vault Insights — YYYY-MM-DD

## <Question>
<synthesis>
Sources: [[slug]], [[slug]]

## Action Items
- [ ] <specific, named item>
```

Report: questions answered, sources read, action items.
