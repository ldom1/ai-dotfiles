# Claude Module Audit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix portability gaps, publish `create-pr` to marketplace, and clean up quality issues in the Claude module of ai-dotfiles.

**Architecture:** Targeted file edits only — no restructuring. New files for `create-pr` marketplace structure mirror brain-sync/brain-load exactly. `install.sh` gets one new step. CLAUDE.md and example files get minor cleanups.

**Tech Stack:** bash, JSON, Markdown, symlinks

---

## File Map

| File | Action |
|------|--------|
| `skills/create-pr/.claude-plugin/plugin.json` | create |
| `skills/create-pr/skills/create-pr/SKILL.md` | create (symlink → `../../SKILL.md`) |
| `.claude-plugin/marketplace.json` | modify — add create-pr entry |
| `scripts/install.sh` | modify — add brain.env bootstrap + fix next steps |
| `.claude/CLAUDE.md` | modify — remove "Copy table" artifact |
| `.claude/settings.local.json.example` | modify — add gh, bash permissions |
| `docs/create-pr.md` | create |

---

### Task 1: `create-pr` — add `.claude-plugin/plugin.json`

**Files:**
- Create: `skills/create-pr/.claude-plugin/plugin.json`

- [ ] **Step 1: Create the directory and plugin.json**

```bash
mkdir -p skills/create-pr/.claude-plugin
```

Content of `skills/create-pr/.claude-plugin/plugin.json`:
```json
{
  "name": "create-pr",
  "version": "1.0.0",
  "description": "Open a GitHub PR using gh and ai-dotfiles git conventions (branch prefix, conventional commits)",
  "author": {
    "name": "Louis Giron",
    "github": "ldom1"
  },
  "homepage": "https://github.com/ldom1/ai-dotfiles"
}
```

- [ ] **Step 2: Verify file is valid JSON**

```bash
python3 -c "import json,sys; json.load(open('skills/create-pr/.claude-plugin/plugin.json')); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add skills/create-pr/.claude-plugin/plugin.json
git commit -m "feat(marketplace): add plugin.json to create-pr skill"
```

---

### Task 2: `create-pr` — add internal skill symlink

**Files:**
- Create: `skills/create-pr/skills/create-pr/SKILL.md` (symlink)

This mirrors the structure in `skills/brain-sync/skills/brain-sync/SKILL.md` → `../../SKILL.md`.

- [ ] **Step 1: Create nested skills dir and symlink**

```bash
mkdir -p skills/create-pr/skills/create-pr
ln -sfn ../../SKILL.md skills/create-pr/skills/create-pr/SKILL.md
```

- [ ] **Step 2: Verify symlink resolves**

```bash
ls -la skills/create-pr/skills/create-pr/SKILL.md
# Expected: ... SKILL.md -> ../../SKILL.md
cat skills/create-pr/skills/create-pr/SKILL.md | head -3
# Expected: first 3 lines of skills/create-pr/SKILL.md
```

- [ ] **Step 3: Commit**

```bash
git add skills/create-pr/skills/
git commit -m "feat(marketplace): add internal skill symlink to create-pr"
```

---

### Task 3: Add `create-pr` to `marketplace.json`

**Files:**
- Modify: `.claude-plugin/marketplace.json`

- [ ] **Step 1: Add create-pr to the plugins array**

Current `.claude-plugin/marketplace.json` has two entries (brain-sync, brain-load). Add a third:

```json
{
  "name": "create-pr",
  "description": "Open a GitHub PR using gh and ai-dotfiles git conventions — branch prefix (feature/, fix/, enh/), conventional commits, gh pr create workflow.",
  "source": "./skills/create-pr",
  "category": "productivity",
  "homepage": "https://github.com/ldom1/ai-dotfiles"
}
```

Full resulting `plugins` array:
```json
"plugins": [
  {
    "name": "brain-sync",
    "description": "Sync your Local Brain (Obsidian vault) at session start and end via git pull/push. Stashes dirty state, rebases, commits and pushes automatically.",
    "source": "./skills/brain-sync",
    "category": "productivity",
    "homepage": "https://github.com/ldom1/ai-dotfiles"
  },
  {
    "name": "brain-load",
    "description": "Load your Local Brain project note into Claude context at session start. Auto-instantiates a new project note from template if missing, with CAP (area of responsibility) mapping.",
    "source": "./skills/brain-load",
    "category": "productivity",
    "homepage": "https://github.com/ldom1/ai-dotfiles"
  },
  {
    "name": "create-pr",
    "description": "Open a GitHub PR using gh and ai-dotfiles git conventions — branch prefix (feature/, fix/, enh/), conventional commits, gh pr create workflow.",
    "source": "./skills/create-pr",
    "category": "productivity",
    "homepage": "https://github.com/ldom1/ai-dotfiles"
  }
]
```

- [ ] **Step 2: Validate JSON**

```bash
python3 -c "import json,sys; json.load(open('.claude-plugin/marketplace.json')); print('OK')"
```
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add .claude-plugin/marketplace.json
git commit -m "feat(marketplace): add create-pr to marketplace.json"
```

---

### Task 4: `install.sh` — bootstrap `config/brain.env`

**Files:**
- Modify: `scripts/install.sh`

- [ ] **Step 1: Add brain.env bootstrap step**

In `scripts/install.sh`, after the block `# ── 3. Bootstrap settings.local.json if missing` and before `# ── 4. Hook permissions`, insert:

```bash
# ── 4. Bootstrap config/brain.env if missing ──────────────────────────────────
header "Checking config/brain.env"

BRAIN_ENV="$DOTFILES/config/brain.env"
BRAIN_ENV_EXAMPLE="$DOTFILES/config/brain.env.example"

if [[ ! -f "$BRAIN_ENV" ]]; then
  cp "$BRAIN_ENV_EXAMPLE" "$BRAIN_ENV"
  warn "config/brain.env created from example — edit BRAIN_PATH to your vault path before using Claude Code"
else
  log "config/brain.env already exists, skipping"
fi
```

(Renumber the old `# ── 4. Hook permissions` to `# ── 5. Hook permissions`.)

- [ ] **Step 2: Update Next steps**

Replace the current "Next steps" block at the bottom of `install.sh`:

```bash
echo "  Next steps:"
echo "  1. Edit config/brain.env — set BRAIN_PATH to your Obsidian vault (absolute path)"
echo "  2. Install rtk if not present: cargo install rtk"
echo "  3. Edit ~/.claude/settings.local.json to add your machine permissions"
echo "  4. Install Claude Code plugins: claude plugins install superpowers"
```

- [ ] **Step 3: Test dry-run (no vault needed)**

```bash
bash scripts/install.sh 2>&1 | grep -E "brain.env|Next steps|1\.|2\.|3\.|4\."
```
Expected: lines mentioning brain.env creation/skip and updated next steps.

- [ ] **Step 4: Commit**

```bash
git add scripts/install.sh
git commit -m "fix(install): bootstrap config/brain.env and update next steps"
```

---

### Task 5: Quality fixes — CLAUDE.md + settings.local.json.example

**Files:**
- Modify: `.claude/CLAUDE.md`
- Modify: `.claude/settings.local.json.example`

- [ ] **Step 1: Remove "Copy table" from CLAUDE.md**

In `.claude/CLAUDE.md`, under the `## Skills` section, find and remove the line `Copy table` (appears between the introductory sentence and the table). The section should read:

```markdown
## Skills

Plugins may add more slash commands; this list covers ai-dotfiles only.

| Command | Purpose | Notes |
```

(No `Copy table` line between the paragraph and the table.)

- [ ] **Step 2: Expand settings.local.json.example**

Replace current content of `.claude/settings.local.json.example`:

```json
{
  "permissions": {
    "allow": [
      "Bash(git:*)",
      "Bash(gh:*)",
      "Bash(bash:*)",
      "Bash(npm install:*)",
      "Bash(npm test:*)",
      "Bash(python3:*)"
    ]
  }
}
```

- [ ] **Step 3: Verify JSON**

```bash
python3 -c "import json,sys; json.load(open('.claude/settings.local.json.example')); print('OK')"
```
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add .claude/CLAUDE.md .claude/settings.local.json.example
git commit -m "fix(claude): remove Copy table artifact; expand settings.local.json.example"
```

---

### Task 6: Create `docs/create-pr.md`

**Files:**
- Create: `docs/create-pr.md`

- [ ] **Step 1: Write the doc**

```markdown
# create-pr

Skill for opening GitHub PRs following ai-dotfiles conventions. Canonical skill: [`skills/create-pr/SKILL.md`](../skills/create-pr/SKILL.md).

## Branch naming

| Change type | Prefix | Example |
|-------------|--------|---------|
| Feature | `feature/` | `feature/oauth-login` |
| Bugfix | `fix/` | `fix/null-ref-cache` |
| Improvement | `enh/` | `enh/faster-sync` |

Use kebab-case. If already on a suitably named branch, keep it.

## Commit format

```
type(scope): imperative description
```

Quick types: `feat`, `fix`, `enh`, `doc`, `ci`. Full reference: [`docs/git-commits.md`](git-commits.md).

## Workflow

1. `git status` — check working tree
2. Run tests if the project has them
3. `git fetch origin` + rebase onto primary branch
4. Commit uncommitted changes (conventional message)
5. `git push -u origin HEAD`
6. `gh pr create` — `--fill` when commits carry good titles, else `--title` + `--body`

## Usage

Invoke with `/create-pr` in Claude Code or Mistral Vibe.

Not published on the marketplace by default — install from ai-dotfiles:

```
/plugin install create-pr@ldom1/ai-dotfiles
```
```

- [ ] **Step 2: Commit**

```bash
git add docs/create-pr.md
git commit -m "doc(skills): add create-pr skill documentation"
```

---

### Task 7: Commit spec + plan

- [ ] **Step 1: Commit the spec and plan files**

```bash
git add docs/superpowers/
git commit -m "doc(superpowers): add claude module audit spec and implementation plan"
```

---

## Self-Review

**Spec coverage:**
- ✓ create-pr marketplace: Tasks 1–3
- ✓ install.sh brain.env: Task 4
- ✓ CLAUDE.md artifact: Task 5
- ✓ settings.local.json.example: Task 5
- ✓ docs/create-pr.md: Task 6

**Placeholder scan:** No TBD, all steps have exact commands and file content.

**Type consistency:** N/A (config/scripts, no type system).
