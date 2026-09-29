# Notion

Project: [Medium writer - Write 1 article / month](https://app.notion.com/p/21c6c45194658086aa2adf9a2b1ad980)

| Thing | ID |
|---|---|
| Project page | `21c6c45194658086aa2adf9a2b1ad980` |
| Tasks data source | `collection://6b291223-939b-4520-b77d-8b6217e72835` |
| Projet relation value | `https://app.notion.com/p/21c6c45194658086aa2adf9a2b1ad980` |

Authenticate Notion MCP if `needsAuth`. Then `notion-query-data-sources` / `notion-fetch` / `notion-update-page`.

## next query

SQL against the Tasks collection. Filter `Projet` LIKE the project page id. Exclude `État` in (`Done`, `Cancelled`, `Archived`). Order by `date:Échéance:start`. Limit 20.

Status values: `Backlog`, `To start`, `In progress`, `Blocked`, `Done`, `Cancelled`, `Archived`.

## write-notion

1. Fetch the task page. If it has child `<page>` / `<database>` tags, stop and ask before replace.
2. Read `notion://docs/enhanced-markdown-spec` via `notion-fetch` if this session has not.
3. Convert `articles/<slug>.md` → Notion-flavored markdown:
   - Do **not** put the H1 in the body. Title is property `Tâche`.
   - Keep ` ```language ` fences literal. Do not escape inside code blocks.
   - H5/H6 → `####`.
   - Pipe tables → `<table header-row="true">` / `<tr>` / `<td>`. Cells are rich text only.
   - `>` quotes stay. Use `<br>` inside a multi-line quote, not extra `>` lines.
   - Skip decorative blank lines (Notion strips them). Horizontal rules `---` are fine.
   - Callouts: `<callout>` for the one-box asides.
   - Images: `![caption](url)`.
4. `notion-update-page`: `command=replace_content`, `new_str` = converted body, `allow_async=true`. Poll `notion-get-async-task` if returned.
5. Same call or follow-up: `update_properties` `État` = `In progress`.
6. Fetch again. Confirm a known fence is a code block. Re-push if it rendered as escaped text.

## publish

After the user gives the Medium URL: `État` = `Done`, `Résumé` = URL.
