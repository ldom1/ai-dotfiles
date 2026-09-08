# Cursor B0 — skill invoke observation (2026-09-08)

## Procedure

1. Registered `spikes/cursor-b0-pretooluse-logger.sh` on `preToolUse` (unmatched) and `beforeReadFile`.
2. Ran: `cursor-agent-brain.sh -p "Read … skills/grill-me/SKILL.md …"` (workspace ai-dotfiles).
3. Unregistered spike; kept this sample + logger script.

## Live sample (`cursor-b0-live.ndjson`)

Skill read emitted **two** hook events for the same load:

1. `preToolUse` / `tool_name=Read` / `tool_input.file_path=…/skills/grill-me/SKILL.md`
2. `beforeReadFile` / `file_path=…/skills/grill-me/SKILL.md` (includes full `content`)

No dedicated `Skill` tool. Payload keys observed: `tool_name`, `tool_input.file_path`, `hook_event_name`, `session_id`, …

## Conclusion

`proceed-H1` — stable Read-of-SKILL.md signal via `preToolUse` matcher `Read`.

**Implementation note:** do **not** also wire `beforeReadFile` for the same filter — double-counts. Prefer `tool_input.file_path` (live) and fall back to `.path` / `.target_file`.

Treat exploratory Reads of `SKILL.md` as false positives (heuristic ceiling); README states Cursor lines are approximate.
