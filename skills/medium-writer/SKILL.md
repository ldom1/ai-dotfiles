---
name: medium-writer
description: Draft a tech Medium article from real repo code into articles/*.md, then write the full article onto the Notion task page via MCP. Use when the user asks to write, draft, outline, review, or publish a Medium article, run /medium-writer, or work the Medium writer calendar.
user-invocable: true
---

# medium-writer

Workshop = `articles/<slug>.md` (gitignored). **An article is written only when it is on the Notion task page.** Medium comes after that page.

Read [voice.md](voice.md) before draft/review. Read [notion.md](notion.md) before calendar or write-notion.

## Process

Copy and track:

```
- [ ] next
- [ ] outline (human gate)
- [ ] draft
- [ ] review (human gate)
- [ ] write-notion
- [ ] publish (human Medium URL)
```

**next.** Query the Tasks data source in [notion.md](notion.md). Filter `Projet` = Medium writer, `État` not in Done/Cancelled/Archived, sort `Échéance`. Show the next 3. Do not pick one alone if several are `In progress`.

**outline.** Fetch the task page + relevant repo files + Local Brain. Bullets only. Wait for approval before draft.

**draft.** Write `~/ai-dotfiles/articles/<slug>.md`. Every snippet is copied from a real file (cite path). Do not invent code. If the repo does not contain the fact, say so.

**review.** Apply the review prompt in [voice.md](voice.md). Output concrete diffs, then apply them to the `.md`. Wait for approval before write-notion.

**write-notion.** Required. Convert the `.md` per [notion.md](notion.md). `replace_content` on the **task page**. Set `État` = `In progress`. Re-fetch and check one code block survived as a code block. Fix and re-push if not.

**publish.** Checklist: copy/import Medium **from the Notion page**; cover via [cover-prompt.md](cover-prompt.md). After the user pastes the Medium URL: `État` = `Done`, `Résumé` = that URL.

## Non-goals

Do not auto-publish to Medium. Do not mark the Notion page as a Notion AI skill. Do not create a new Articles database. Do not skip write-notion.
