# brain-audit Skill

**autonomous maintenance pipeline for the Local Brain vault**

## Purpose

Brain-audit is a four-phase maintenance pipeline that keeps your Local Brain vault organized, connected, and up-to-date. It processes raw notes into publishable articles, discovers orphaned files, runs templated Q&A queries, and generates a weekly digest report.

## What It Does

| Phase | Name | Input | Output | Time | Notes |
|-------|------|-------|--------|------|-------|
| 1 | Raw Data Processing | Markdown fragments, inbox clippings | Draft articles, indexed metadata | 5-10m | Applies semantic structure |
| 2 | Orphan Detection | All vault files, connection graph | Isolated notes, suggested links | 10-15m | Finds knowledge gaps |
| 3 | Templated Q&A | Vault state snapshot | Structured answers, insights | 15-30m | Runs custom queries |
| 4 | Digest Generation | Phases 1-3 outputs | Weekly summary report | 5-10m | Resets maintenance clock |

## Quick Start

```bash
# View this skill documentation
cat ~/ai-dotfiles/skills/brain-audit/SKILL.md

# Check configuration
grep BRAIN_PATH ~/ai-dotfiles/config/brain.env

# Run full audit (all 4 phases)
brain-audit --full

# Run single phase
brain-audit --phase 1
brain-audit --phase 2
brain-audit --phase 3
brain-audit --phase 4

# View detailed phase documentation
cat ~/ai-dotfiles/skills/brain-audit/reference/PHASES.md

# Review query templates
ls -la ~/ai-dotfiles/skills/brain-audit/reference/queries/
```

## Configuration

The skill requires `BRAIN_PATH` to be set in your environment:

```bash
# Check current setting
echo $BRAIN_PATH

# Set it (add to ~/.zshrc or ~/ai-dotfiles/config/brain.env)
export BRAIN_PATH="/path/to/your/Local Brain"
```

The Local Brain vault must be a git repository with the following structure:
```
Local Brain/
├── daily/                 # Daily notes, implementation logs
├── resources/             # Stable knowledge base
│   ├── articles/         # Published articles
│   ├── knowledge/        # Reference materials
│   └── queries/          # Q&A results archive
├── projects/             # Active project CAPs
└── .git/                 # Git repository root
```

## Human Review Workflow

Brain-audit produces outputs that require human review and approval:

1. **After Phase 1:** Review generated draft articles
   - Check semantic structure correctness
   - Approve or request revisions
   - Mark articles ready for publication

2. **After Phase 2:** Review orphaned notes
   - Examine connection suggestions
   - Decide: merge, archive, or keep isolated
   - Update vault structure as needed

3. **After Phase 3:** Review Q&A insights
   - Validate query results
   - Extract actionable items
   - Update related articles/projects

4. **After Phase 4:** Review and archive digest
   - Confirm weekly summary is accurate
   - Store in `resources/queries/` archive
   - Reset audit clock for next week

## Scripts

The skill includes six executable scripts in `scripts/`:

| Script | Purpose | Called By | Output |
|--------|---------|-----------|--------|
| `phase1.sh` | Raw data → articles | Main pipeline | `phase1-results.json` |
| `phase2.sh` | Orphan detection | Main pipeline | `phase2-results.json` |
| `phase3.sh` | Q&A queries | Main pipeline | `phase3-results.json` |
| `phase4.sh` | Digest generation | Main pipeline | `phase4-results.json` |
| `validate.sh` | Check outputs before commit | Main pipeline | `validation-report.json` |
| `cleanup.sh` | Archive results, reset state | End of cycle | None |

## Files

```
~/ai-dotfiles/skills/brain-audit/
├── SKILL.md                          # This file
├── .claude-plugin/
│   └── plugin.json                   # Marketplace metadata
├── scripts/
│   ├── phase1.sh                     # Raw data processing
│   ├── phase2.sh                     # Orphan detection
│   ├── phase3.sh                     # Templated Q&A
│   ├── phase4.sh                     # Digest generation
│   ├── validate.sh                   # Output validation
│   └── cleanup.sh                    # Archive & reset
└── reference/
    ├── brain.env.example             # Configuration template
    ├── PHASES.md                     # Detailed phase documentation
    └── queries/
        ├── project-summary.md        # Q&A: Project status
        └── knowledge-gaps.md         # Q&A: Knowledge coverage
```

## Related Documentation

- **Phase Details:** `reference/PHASES.md` — comprehensive breakdown of each phase with examples
- **Configuration:** `reference/brain.env.example` — environment variable setup
- **Q&A Templates:** `reference/queries/` — standard query formats for Phase 3
- **Brain Vault Structure:** Check your Local Brain `README.md` for vault organization

## Integration with Other Skills

- **brain-load:** Load project context before running brain-audit
- **brain-sync:** Sync vault before and after audit runs
- **finops-audit:** Track time spent on audit phases

---

**Last Updated:** 2026-04-11  
**Version:** 1.0.0
