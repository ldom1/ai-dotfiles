# Skills layout (`skills/`)

Every skill lives in **`skills/<name>/`** with a **`SKILL.md`** (and optional scripts). Sources are **not** duplicated under `.claude/` or `.vibe/`.

## Claude Code

Claude Code loads skills from **`~/.claude/skills/<name>/`**. In this repo each skill is a **symlink**:

```
.claude/skills/<name>  →  ../../skills/<name>
```

After `install.sh`, `~/.claude` points at this tree, so **all** skills under `skills/` with a `SKILL.md` are discoverable (names + descriptions in context; full body when invoked or auto-loaded per skill settings).

You do **not** have to `plugin install brain-sync` / `brain-load` if these symlinks are already present — the marketplace is optional (e.g. another machine without this repo layout).

## Mistral Vibe

Vibe discovers **`SKILL.md`** under **`.vibe/skills/<name>/`**. Same rule:

```
.vibe/skills/<name>  →  ../../skills/<name>
```

## Cursor

Cursor has **no** skill directory compatible with `SKILL.md`. Session behavior for Local Brain uses **rules**: `.cursor/rules/brain-sync.mdc`, `.cursor/rules/brain-load.mdc`, etc. Those rules tell the agent **when** to run `sync.sh` / `load.sh`; they are **not** symlinks into `skills/` because Cursor does not load that format as a first-class “skill”.

Adding a new **Cursor-only** workflow still belongs in a **new `.mdc` rule** if you want it always or selectively applied.

## Adding a new skill

1. Create **`skills/<name>/SKILL.md`** (and scripts beside it if needed).
2. Run **`bash scripts/install.sh`** (or only the skill-link loop from it), **or** manually:
   ```bash
   ln -sfn ../../skills/<name> .claude/skills/<name>
   ln -sfn ../../skills/<name> .vibe/skills/<name>
   ```
3. Commit the **folder** + **both symlinks** so clones stay consistent.

`install.sh` links **every** directory under `skills/` that contains `SKILL.md`, so new skills are wired automatically on install.

## Current skills

| Name        | Role                          |
|-------------|-------------------------------|
| brain-sync  | Vault git sync start/end      |
| brain-load  | Load / instantiate project note |
| create-pr   | GitHub PR + commit conventions |
