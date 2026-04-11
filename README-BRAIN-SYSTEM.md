# Local Brain System: Comprehensive Guide

## Overview

The Local Brain System is an autonomous knowledge management system that grows your personal vault of research, ideas, and project context through structured ingestion, intelligent synthesis, and human-driven curation.

### Vision

Your vault evolves automatically through a four-phase maintenance pipeline:
- **Raw data** (research notes, logs, captures) flows into `/inbox/`
- **Compilation** transforms raw data into structured wiki articles
- **Connection detection** finds orphaned notes and suggests semantic links
- **Synthesis** runs templated Q&A queries to generate insights and actionable summaries
- **Human approval** lets you review and integrate all changes

Between sessions, your vault stays lightweight—only when maintenance is triggered does the heavy lifting happen. The system decides autonomously whether to run a full maintenance or simply load project context, based on vault health metrics.

### How It Works

#### Session Start Flow

1. **brain-sync start** pulls your vault from remote (git)
2. **brain-route** analyzes vault state to decide:
   - **Maintenance mode**: If >7 days since last maintenance, >50 raw files waiting, or explicit `--maintenance` flag
   - **Normal mode**: Otherwise, proceed with normal session
3. **brain-audit** (maintenance only) runs the four-phase pipeline
4. **brain-load** (normal mode) loads your current project context
5. **Your work**: Continue your session as normal
6. **brain-sync end** commits and pushes vault changes

#### Normal Mode

Quick session with project context loaded:
- Pulls vault
- Runs `brain-load` to instantiate current project notes
- Loads decision reasoning into Claude context
- Session proceeds

#### Maintenance Mode

Full maintenance pipeline (typically 5-15 min):
- Pulls vault
- **Phase 1 - Raw Data Compilation**: Processes files in `/raw/` → creates wiki articles in `/inbox/drafts/`
- **Phase 2 - Connection Detection**: Scans vault structure → finds orphaned notes, suggests links in `/inbox/connections/`
- **Phase 3 - Templated Q&A**: Runs saved queries from `/meta/queries/` → files results in `/inbox/qa/`
- **Phase 4 - Digest Generation**: Summarizes all changes → creates `/meta/digest-YYYY-MM-DD-HHmmss.md` → resets 7-day clock in `/meta/last-maintenance.md`
- All inbox items ready for human review
- Commits, resets clock, pushes

---

## Inbox Workflow: Review & Approval

The inbox is your staging ground for all automated changes. Everything goes here first—your job is to review and decide.

### Directory Structure

```
$BRAIN_PATH/
├── inbox/
│   ├── drafts/              # Compiled raw data → structured articles
│   ├── connections/         # Suggested semantic links (markdown list format)
│   └── qa/                  # Query results from templated Q&A
├── meta/
│   ├── last-maintenance.md  # 7-day clock: timestamp of last maintenance
│   ├── digest-*.md          # Timestamped summaries of each maintenance run
│   └── queries/             # Templated Q&A queries (YAML format)
├── raw/                     # Unprocessed captures (research, logs, notes)
├── drafts/                  # Your draft notes (pre-publish)
├── published/               # Approved, merged, finalized knowledge
└── archive/                 # Old/superseded material
```

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

4. **Review Q&A results** (`ls $BRAIN_PATH/inbox/qa/`)
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

## Templated Q&A System

Templated Q&A queries run automatically during maintenance to synthesize knowledge from your vault.

### Creating Query Templates

Store templates as YAML files in `/meta/queries/`:

```yaml
# $BRAIN_PATH/meta/queries/weekly-project-summary.yaml
name: "Weekly Project Summary"
description: "Synthesize this week's progress across all active projects"
query: |
  Based on the vault, summarize:
  1. What work was completed this week?
  2. What blockers remain?
  3. What needs follow-up?
  4. Top 3 priorities for next week?
output_format: "markdown"
target_inbox: "qa"
```

### How They Work

During Phase 3 (Templated Q&A), brain-audit:
1. Reads each query from `/meta/queries/`
2. Passes query + vault context to Claude
3. Writes result to `/inbox/qa/{query-name}-{timestamp}.md`
4. Your review: copy relevant sections into published notes or integrate into projects

### Built-In Queries

The system provides starter queries:

- `weekly-project-summary.yaml` — Synthesize weekly progress
- `orphaned-notes.yaml` — Find notes with no incoming links
- `connection-suggestions.yaml` — Recommend semantic links between notes
- `knowledge-gaps.yaml` — Identify areas with sparse documentation

---

## Manual Triggers & Commands

### Force Maintenance Mode

```bash
# At session start, force maintenance regardless of 7-day clock
brain-route --maintenance

# Or manually run the pipeline
bash ~/ai-dotfiles/skills/brain-audit/scripts/audit.sh
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

Run individual phases without full maintenance:

```bash
# Phase 1: Compile raw data only
bash ~/ai-dotfiles/skills/brain-audit/scripts/phase-1-compile.sh

# Phase 2: Detect connections only
bash ~/ai-dotfiles/skills/brain-audit/scripts/phase-2-connect.sh

# Phase 3: Run Q&A queries only
bash ~/ai-dotfiles/skills/brain-audit/scripts/phase-3-qa.sh

# Phase 4: Generate digest only
bash ~/ai-dotfiles/skills/brain-audit/scripts/phase-4-digest.sh
```

### Reset Maintenance Clock

```bash
# If you've manually processed inbox and want to reset the 7-day clock:
echo "$(date -u +'%Y-%m-%d %H:%M:%S UTC')" > $BRAIN_PATH/meta/last-maintenance.md
cd $BRAIN_PATH && git add meta/last-maintenance.md && git commit -m "chore: reset maintenance clock"
```

---

## Directory Structure Reference

```
$BRAIN_PATH/
│
├── inbox/                           # Staging area for all automated changes
│   ├── drafts/                      # Compiled raw data → articles
│   ├── connections/                 # Suggested semantic links
│   └── qa/                          # Query results
│
├── meta/                            # System metadata
│   ├── last-maintenance.md          # Timestamp of last maintenance (7-day clock)
│   ├── digest-YYYY-MM-DD-*.md       # Summary of each maintenance run
│   └── queries/                     # Templated Q&A queries (YAML)
│       ├── weekly-project-summary.yaml
│       ├── orphaned-notes.yaml
│       ├── connection-suggestions.yaml
│       └── knowledge-gaps.yaml
│
├── raw/                             # Unprocessed captures
│   ├── research-*.md
│   ├── experiment-*.log
│   ├── idea-*.md
│   └── ...
│
├── drafts/                          # Your draft notes (work in progress)
│   ├── project-notes.md
│   ├── research-directions.md
│   └── ...
│
├── published/                       # Approved, finalized knowledge
│   ├── projects/
│   │   ├── project-alpha.md
│   │   ├── project-beta.md
│   │   └── ...
│   ├── research/
│   │   ├── topic-1.md
│   │   ├── topic-2.md
│   │   └── ...
│   ├── reference/
│   ├── people/
│   └── ...
│
└── archive/                         # Old/superseded material
    ├── old-project-*.md
    ├── archived-research/
    └── ...
```

---

## Troubleshooting

### Q: Why didn't maintenance run at session start?

**Possible causes:**

1. **Not yet 7 days since last maintenance**
   - Check: `cat $BRAIN_PATH/meta/last-maintenance.md`
   - Fix: Run `brain-route --maintenance` to force

2. **Fewer than 50 raw files waiting**
   - Brain-audit only triggers automatically if raw data accumulates
   - Check: `ls $BRAIN_PATH/raw/ | wc -l`
   - Fix: Add more raw files or run `brain-route --maintenance` to force

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

### Q: Query templates aren't running. How do I debug?

```bash
# Check if templates exist
ls -la $BRAIN_PATH/meta/queries/

# Run Phase 3 manually with verbose output
bash ~/ai-dotfiles/skills/brain-audit/scripts/phase-3-qa.sh --verbose

# Check query syntax
cat $BRAIN_PATH/meta/queries/<query-name>.yaml
```

**Common issues:**
- Missing YAML file extension (must be `.yaml`)
- Invalid YAML syntax (use `yamllint` to validate)
- Query is too broad and takes too long (add time limit: `timeout 60 claude-query ...`)

---

## Next Steps Checklist

Get started with the Local Brain System:

- [ ] **Understand the vision** — Read the Overview section above
- [ ] **Set up vault path** — Verify `$BRAIN_PATH` is set: `echo $BRAIN_PATH`
- [ ] **Create initial directories** — Run: `mkdir -p $BRAIN_PATH/{inbox/{drafts,connections,qa},meta/queries,raw,published,archive}`
- [ ] **Initialize git** — `cd $BRAIN_PATH && git init && git add . && git commit -m "init: local brain vault"`
- [ ] **Add starter raw files** — Put research notes, ideas, or logs into `/raw/`
- [ ] **Create first query template** — Copy one from the system defaults to `/meta/queries/`
- [ ] **Run first maintenance** — `brain-route --maintenance` (takes 5-15 min)
- [ ] **Review inbox** — Check `/inbox/drafts/`, `/inbox/connections/`, `/inbox/qa/`
- [ ] **Approve changes** — Move approved articles from `/inbox/drafts/` to `/published/`
- [ ] **Commit & push** — `cd $BRAIN_PATH && git add . && git commit -m "inbox: approve first maintenance" && git push`
- [ ] **Future sessions** — System will auto-detect when maintenance is needed
- [ ] **Customize queries** — Create your own templates in `/meta/queries/` based on your workflow
- [ ] **Refine structure** — Organize `/published/` with subdirectories as your vault grows

---

## Reference

**Related documentation:**
- [brain-sync wiki](https://github.com/ldom1/ai-dotfiles/wiki/Brain-Sync)
- [brain-load wiki](https://github.com/ldom1/ai-dotfiles/wiki/Brain-Load)
- [Claude Code session hooks](~/.claude/CLAUDE.md#hooks)

**Key files:**
- System integration: `~/.claude/CLAUDE.md` (Brain System Integration section)
- Skill scripts: `~/ai-dotfiles/skills/brain-route/`, `~/ai-dotfiles/skills/brain-audit/`
- Configuration: `~/ai-dotfiles/config/brain.env`
- Vault root: `$BRAIN_PATH` (usually `/mnt/c/Users/lgiron/Documents/developer-brain/`)
