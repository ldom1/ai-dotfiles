---
name: Telegram Task Creation Fix
overview: The Telegram → Agent → Kanban flow is broken because the agent service is a pure LLM proxy with no intent-to-API wiring. Fix by adding deterministic intent routing directly in the Telegram service, bypassing the agent for known task/project commands.
todos:
  - id: docker-kanban-url
    content: Add KANBAN_URL=http://kanban-api:8090 to telegram service env in docker-compose.yml
    status: pending
  - id: config-kanban-url
    content: Add kanban_url field to TelegramSettings in services/telegram/core/config.py
    status: pending
  - id: kanban-bridge
    content: Create services/telegram/core/kanban_bridge.py with intent regex, project resolution, and POST /tasks call
    status: pending
  - id: bot-bridge-hook
    content: Update on_message in services/telegram/core/bot.py to call try_create_task before falling back to agent
    status: pending
isProject: false
---

# Fix Telegram Task Creation

## Root Cause Analysis

```mermaid
flowchart TD
    User["User: 'Create a new task for project...'"]
    Bot["bot.py on_message()"]
    Agent["agent /chat — pure LLM proxy"]
    LLM["LLM (Anthropic/Mammouth/CLI)"]
    Formatter["format_reply()"]
    Kanban["kanban-api POST /tasks"]
    Snag["'I ran into a snag'"]

    User --> Bot
    Bot --> Agent
    Agent --> LLM
    LLM -->|"[No LLM provider] OR plain text"| Agent
    Agent --> Formatter
    Formatter -->|"error sentinel detected"| Snag
    Kanban -.->|"NEVER called"| Kanban
```

**Problem 1 — Agent is a dumb proxy:** `/chat` in `router.py` calls the LLM and streams back raw text. It has zero code to call `POST /tasks` on the Kanban API. The LLM generates words, not API calls.

**Problem 2 — Error sentinel → snag message:** `format_reply()` in `formatter.py` converts any response starting with `[No LLM`, `[CLI error:`, `[CLI:`, etc. to the "I ran into a snag" message. The agent is likely returning `[No LLM provider configured...]` because no API key is set and/or CLI is unavailable.

**Problem 3 — Free-text bypasses enricher:** The `enrich()` router in `telegram/core/router.py` only fires for `/tasks`, `/projects`, `/status` Telegram commands. Free-text messages in `on_message` are sent raw to the agent with no enrichment.

**Problem 4 — Telegram has no Kanban URL:** The `telegram` container has `AGENT_URL` but no `KANBAN_URL`. It can't call the Kanban API directly.

## Fix: Deterministic Intent Routing in the Telegram Layer

Instead of relying on the LLM to "know" how to call the Kanban API, add a direct bridge in the Telegram service that pattern-matches known intents and calls the Kanban API itself.

```mermaid
flowchart TD
    User["User: 'Create a new task...'"]
    Bot["bot.py on_message()"]
    Bridge["kanban_bridge.try_create_task()"]
    Projects["GET /hub/projects — resolve name→slug"]
    TaskPost["POST /tasks — create task"]
    Confirm["'Task created: #task-id'"]
    Agent["agent /chat (fallback)"]

    User --> Bot
    Bot --> Bridge
    Bridge -->|"pattern matched"| Projects
    Projects --> TaskPost
    TaskPost --> Confirm
    Bridge -->|"no match"| Agent
```

## Files to Change

**1. [`docker-compose.yml`](docker-compose.yml)** — add `KANBAN_URL` to the `telegram` service environment:
```yaml
environment:
  - AGENT_URL=http://agent-service:8092
  - KANBAN_URL=http://kanban-api:8090   # add this
```

**2. [`services/telegram/core/config.py`](services/telegram/core/config.py)** — add `kanban_url` field to `TelegramSettings`:
```python
class TelegramSettings(BaseModel):
    agent_url: str
    kanban_url: str = "http://kanban-api:8090"
    ...
```
Read from `os.environ.get("KANBAN_URL", "http://kanban-api:8090")`.

**3. NEW: [`services/telegram/core/kanban_bridge.py`](services/telegram/core/kanban_bridge.py)** — deterministic intent router:
- Regex patterns for task creation: `create.*task|add.*task|nouveau.*task|ajouter.*tâche|new.*task`
- Project name extraction (text after "project|projet", before ":", or "add|:|-")
- Fuzzy project resolution: `GET /hub/projects` → lowercase/accent-strip match on name
- Task title extraction (text after ":" or after project name)
- `POST /tasks` with `{title, project: slug}`
- Returns formatted confirmation or `None` if no match

**4. [`services/telegram/core/bot.py`](services/telegram/core/bot.py)** — update `on_message` to try bridge first:
```python
from core.kanban_bridge import try_create_task

async def on_message(update, _):
    incoming = incoming_from_update(update)
    if incoming is None:
        return
    settings = get_settings()
    direct = await try_create_task(incoming.text, settings.kanban_url)
    if direct is not None:
        await update.message.reply_text(direct)
        return
    # existing agent fallback...
```

## Intent Patterns to Support

- `"Create a new task for project Epidemie des mots: add a Rendez vous page"`
- `"create a new task in the project epidemie des mots ! ajouter une page rendez vous"`
- `"Ok create a new task in the project epidemie des mots ! ajouter une page rendez vous"`
- `/tasks create Fix login bug` (already handled by `_cmd_routed` but should also use bridge)

## Project Name Resolution

The `POST /tasks` body requires `project` as a **slug** (e.g., `epidemie-des-mots`), not a display name. Bridge calls `GET /hub/projects`, then matches by:
1. Exact slug match
2. Lowercase display name match
3. Normalized match (remove accents, punctuation, extra spaces)

`TaskCreate` required field is only `title`; `project` defaults to `""`.
