# Local Brain System: Comprehensive Guide

## Overview

The Local Brain System is an autonomous knowledge management system that grows your personal vault of research, ideas, and project context through structured ingestion, intelligent synthesis, and human-driven curation.

### Vision

Your vault evolves automatically through a four-phase maintenance pipeline:
- **Raw data** (research notes, logs, captures) flows into `/inbox/`
- **Compilation** transforms raw data into structured wiki articles
- **Connection detection** finds orphaned notes and suggests semantic links
- **Synthesis** runs the `queries` analyses (knowledge gaps, roadmap) to generate insights and actionable summaries
- **Human approval** lets you review and integrate all changes

Between sessions, your vault stays lightweight—only when maintenance is triggered does the heavy lifting happen. Maintenance is manual: the SessionStart hook says when `/brain-audit` is due (last run over 7 days ago).

### How It Works

#### Session Start Flow

1. **brain-sync start** pulls your vault from remote (git)
2. **brain-load** loads your current project context and the pitfalls
3. If `meta/last-maintenance.md` is older than 7 days, the hook prints "maintenance due" — run `/brain-audit` when convenient
5. **notion-brain-sync** (optional): when you paste Notion exports or ask to compile decisions into the vault, agents use L1/L2/L3 routing and append `$BRAIN_PATH/log.md` per change
6. **Your work**: Continue your session as normal
7. **brain-sync end** commits and pushes vault changes

#### Normal Mode

Quick session with project context loaded:
- Pulls vault
- Runs `brain-load` to instantiate current project notes
- Loads decision reasoning into Claude context
- Session proceeds

#### Maintenance Mode

Full maintenance pipeline (typically 5-15 min):
- Pulls vault
- **Phase 1 - Compile**: `brain-audit:compile` reads recent session notes → writes cross-project rules to `pitfalls.md` and stack rules to `resources/knowledge/patterns/*-patterns.md`
- **Phase 2 - Connect**: `brain-audit:connect` finds related vault notes via QMD → adds `## Related` links to the pattern notes
- **Phase 3 - Queries**: `brain-audit:queries` writes knowledge-gaps and roadmap analyses → `/resources/queries/archive/YYYY-MM-DD-*.md`
- **Phase 4 - Digest**: `brain-audit:digest` writes `/meta/digest-YYYY-MM-DD.md` and resets the 7-day clock in `/meta/last-maintenance.md` (`digest.sh` does only the clock)
- All inbox items ready for human review
- Commits, resets clock, pushes

---

## Inbox Workflow: Review & Approval

The inbox is your staging ground for all automated changes. Everything goes here first—your job is to review and decide.

### Directory Structure

The folder layout lives in `LocalBrain.md` in `~/ai-dotfiles`. It is the one vault map.

### Review Timeline

**Typical inbox review takes 10-20 min per maintenance cycle:**

1. **Check the digest** (`cat $BRAIN_PATH/meta/digest-*.md`)
   - Summary of what changed
   - Count of new drafts, connections, query results
   - Which raw files were processed

2. **Review drafted articles** (`ls $BRAIN_PATH/inbox/drafts/`)
   - Read each new article
   - Approve: move to `/published/` (or merge into existing note)
   - Reject: delete or move to `/raw/` for revision

3. **Review suggested connections** (`cat $BRAIN_PATH/inbox/connections/*.md`)
   - Suggested wikilinks between orphaned notes
   - Approve: add to relevant published notes
   - Reject: delete file

4. **Review query results** (`ls $BRAIN_PATH/resources/queries/archive/`)
   - Query results ready to integrate
   - Copy relevant sections into published notes
   - Delete after integration or archive if valuable

5. **Finalize & commit**
   ```bash
   cd $BRAIN_PATH
   git add .
   git commit -m "inbox: approve maintenance digest YYYY-MM-DD"
   git push
   ```

---

## Raw Data Pipeline

Raw data is any unstructured information you want the system to process: research notes, logs, captures, experiments, ideas.

### Adding Raw Files

Put anything into `/raw/` and the next maintenance will process it:

```bash
# Copy a research note
cp ~/Downloads/research-paper-notes.md $BRAIN_PATH/raw/

# Create a capture
echo "Idea: use xyz approach for problem abc" > $BRAIN_PATH/raw/idea-xyz.md

# Log experimental results
cat > $BRAIN_PATH/raw/experiment-2026-04-10.log << 'EOF'
Test run #3 (2026-04-10 14:30)
- Baseline: 1200ms
- With optimization A: 980ms
- With optimization B: 750ms
Recommendation: use B
EOF
```

### What Becomes an Article

brain-audit's Phase 1 (Raw Data Compilation) turns raw files into structured wiki articles:

- **One raw file → one article** (unless explicitly split)
- **Naming**: `original-filename.md` → `Article Title.md`
- **Structure**: Extracted from content or inferred from context
- **Inbox location**: `/inbox/drafts/Article Title.md`
- **Your decision**: approve → move to `/published/`, reject → delete or refine in `/raw/`

Example:

```
# Before (raw/)
experiment-2026-04-10.log
    Test run #3 (2026-04-10 14:30)
    - Baseline: 1200ms
    - With optimization A: 980ms
    - With optimization B: 750ms
    Recommendation: use B

# After (inbox/drafts/)
Performance Testing - Optimization Strategies.md
    ## Experiment Run #3 (2026-04-10)
    
    ### Setup
    - Baseline: 1200ms
    - With optimization A: 980ms
    - With optimization B: 750ms
    
    ### Conclusion
    Recommend optimization B for deployment.
```

---

## Queries

`brain-audit:queries` runs two analyses during maintenance. Each is a skill step, not a YAML template.

- **knowledge-gaps**: surveys `resources/knowledge/` and recent implementation notes. It finds topics with no knowledge file.
- **roadmap**: aggregates the active project folders and recent implementation logs into one status view.

Results go to `resources/queries/archive/YYYY-MM-DD-knowledge-gaps.md` and `YYYY-MM-DD-roadmap.md`. Review them, then copy what matters into project notes. The old YAML templates in `meta/queries/` are archived in the vault (`archive/meta-queries/`).

---

## Manual Triggers & Commands

### Force Maintenance Mode

```bash
# In Claude Code / Cursor
/brain-audit
```

### View Maintenance History

```bash
# Last maintenance timestamp
cat $BRAIN_PATH/meta/last-maintenance.md

# All maintenance digests
ls -lt $BRAIN_PATH/meta/digest-*.md | head -5

# Latest digest content
cat $(ls -t $BRAIN_PATH/meta/digest-*.md | head -1)
```

### Manual Phases

Run one subskill without full maintenance. Ask for it by name:

- `brain-audit:compile`, `brain-audit:promote`, `brain-audit:connect`
- `brain-audit:insights`, `brain-audit:queries`, `brain-audit:qmd-sync`
- `brain-audit:digest` (writes the digest note and resets the clock)

### Reset Maintenance Clock

```bash
# Resets meta/last-maintenance.md (the SessionStart hook reads Epoch Seconds). No commit: brain-sync end commits the vault.
bash ~/ai-dotfiles/skills/brain-audit/scripts/digest.sh
```

---

## Directory Structure Reference

The folder layout and the order of truth live in `LocalBrain.md` in `~/ai-dotfiles`. It is the one vault map.

---

## Troubleshooting

### Q: Why didn't maintenance run at session start?

**Possible causes:**

1. **Not yet 7 days since last maintenance**
   - Check: `cat $BRAIN_PATH/meta/last-maintenance.md`
   - Fix: run `/brain-audit`

2. **Fewer than 50 raw files waiting**
   - Check: `ls $BRAIN_PATH/raw/ | wc -l`
   - Fix: run `/brain-audit`

3. **Last maintenance failed**
   - Check: `cat $BRAIN_PATH/meta/digest-*.md` (most recent)
   - Fix: Review error logs and run again manually

### Q: I accidentally deleted something from inbox. Can I recover it?

Yes—the vault is a git repo with full history:

```bash
cd $BRAIN_PATH
git log --oneline | head -20        # Recent commits
git show <commit>:inbox/drafts/...  # View deleted file at that commit
git checkout <commit> -- inbox/     # Restore entire inbox/ at that commit
```

### Q: A raw file didn't compile into an article. Why?

Possible reasons:

1. **File format not recognized** — brain-audit processes `.md`, `.txt`, `.log`. Other formats ignored.
2. **File is empty or malformed** — check the file contents
3. **File was already archived** — check `/archive/` first
4. **Phase 1 failed silently** — check logs: `ls -la $BRAIN_PATH/.audit-logs/`

**Fix**: Move the file back to `/raw/` with corrected content, run Phase 1 again.

### Q: How do I exclude certain raw files from processing?

Prefix with underscore (`_filename.md`) or move to `/raw/.skip/`:

```bash
# Won't be processed
mv $BRAIN_PATH/raw/temp-file.md $BRAIN_PATH/raw/_temp-file.md

# Or
mkdir -p $BRAIN_PATH/raw/.skip
mv $BRAIN_PATH/raw/temp-file.md $BRAIN_PATH/raw/.skip/
```

### Q: Can I customize the 7-day maintenance cycle?

Yes—edit `$BRAIN_PATH/meta/last-maintenance.md` to backdate it:

```bash
# Force maintenance to trigger next session
echo "$(date -u -d '8 days ago' +'%Y-%m-%d %H:%M:%S UTC')" > $BRAIN_PATH/meta/last-maintenance.md
```

Or set an environment variable:

```bash
export BRAIN_MAINTENANCE_DAYS=14  # Maintenance every 2 weeks instead
```

### Q: The queries analysis did not run. How do I debug?

```bash
# Results land here
ls -lt $BRAIN_PATH/resources/queries/archive/ | head
```

Ask for `brain-audit:queries` by name. It reads `resources/knowledge/` and the recent implementation notes.

---

## Next Steps Checklist

Get started with the Local Brain System:

- [ ] **Understand the vision** — Read the Overview section above
- [ ] **Set up vault path** — Verify `$BRAIN_PATH` is set: `echo $BRAIN_PATH`
- [ ] **Check the vault layout** — Read `LocalBrain.md` (the one vault map) in `~/ai-dotfiles`
- [ ] **Initialize git** — `cd $BRAIN_PATH && git init && git add . && git commit -m "init: local brain vault"`
- [ ] **Add starter raw files** — Put research notes, ideas, or logs into `/raw/`
- [ ] **Run first maintenance** — `/brain-audit` (takes 5-15 min)
- [ ] **Review inbox** — Check `/inbox/drafts/`, `/inbox/connections/`, `/inbox/sensors/`
- [ ] **Approve changes** — Move approved articles from `/inbox/drafts/` to `/published/`
- [ ] **Commit & push** — `cd $BRAIN_PATH && git add . && git commit -m "inbox: approve first maintenance" && git push`
- [ ] **Future sessions** — System will auto-detect when maintenance is needed
- [ ] **Refine structure** — Organize `/published/` with subdirectories as your vault grows

---

## Reference

**Related documentation:**
- [brain-sync wiki](https://github.com/ldom1/ai-dotfiles/wiki/Brain-Sync)
- [brain-load wiki](https://github.com/ldom1/ai-dotfiles/wiki/Brain-Load)
- [Claude Code session hooks](~/.claude/CLAUDE.md#hooks)

**Key files:**
- System integration: `~/.claude/CLAUDE.md` (Brain System Integration section)
- Skill scripts: `~/ai-dotfiles/skills/brain-audit/`
- Configuration: `~/ai-dotfiles/config/brain.env`
- Vault root: `$BRAIN_PATH` (usually `/mnt/c/Users/lgiron/Documents/developer-brain/`)
