# Brain-Audit Phases — Detailed Documentation

The brain-audit skill implements a four-phase maintenance pipeline. Each phase is atomic, idempotent, and requires human review before proceeding to the next phase.

---

## Phase 1: Raw Data Processing

**Purpose:** Transform unstructured markdown fragments and inbox clippings into draft articles with semantic structure.

### Input

- **Inbox notes** (from `daily/inbox/`)
- **Raw fragments** (from `daily/raw/`)
- **Clipped content** (web clips, meeting notes)
- **Existing articles** (for context and linking)

### Process

1. Parse markdown fragments for topic, key concepts, and references
2. Apply semantic structure (headings, lists, code blocks)
3. Generate metadata (tags, category, source, date)
4. Create inter-article links based on concept matching
5. Check for duplicates and suggest merges
6. Validate markdown syntax and formatting

### Output

- **Drafts directory:** `resources/articles/draft/`
  - One file per article: `YYYY-MM-DD-slug.md`
  - Full frontmatter with metadata
  - Markdown body with semantic structure
  - Comments flagging uncertain connections

- **Metadata index:** `phase1-results.json`
  ```json
  {
    "timestamp": "2026-04-11T10:30:00Z",
    "phase": 1,
    "articles_processed": 12,
    "articles_created": 8,
    "duplicates_found": 2,
    "articles": [
      {
        "slug": "kubernetes-deployment-best-practices",
        "title": "Kubernetes Deployment Best Practices",
        "status": "draft",
        "confidence": 0.95,
        "topics": ["kubernetes", "devops", "best-practices"],
        "links_suggested": 3
      }
    ],
    "warnings": [],
    "next_action": "Review draft articles in resources/articles/draft/"
  }
  ```

### Human Action Required

1. Navigate to `resources/articles/draft/`
2. For each article:
   - Read the content and metadata
   - Verify the semantic structure is correct
   - Review suggested links and approve/remove
   - Check for missing context or unclear sections
   - Move to `resources/articles/published/` when approved
3. Resolve duplicate suggestions by merging or keeping separate
4. Archive processed inbox items
5. Proceed to Phase 2 once all drafts are reviewed

### Example Flow

```
Raw input (inbox):
  "Learned about Kubernetes health checks. Probe types: liveness, 
   readiness, startup. Each has different retry behavior. Need to 
   document this for the team."

Phase 1 output (draft article):
  # Kubernetes Probe Types and Configuration
  
  ## Overview
  Kubernetes uses three types of probes to manage Pod lifecycle...
  
  ## Probe Types
  - **Liveness:** Determines if Pod should be restarted
  - **Readiness:** Determines if Pod is ready for traffic
  - **Startup:** Validates initial startup has completed
  
  [Suggested links to: Kubernetes Health Management, Pod Lifecycle]
```

---

## Phase 2: Orphan Detection

**Purpose:** Identify isolated notes with weak connections, find knowledge gaps, and suggest semantic links to strengthen the vault.

### Input

- **All vault files** (entire directory tree)
- **Connection graph** (computed from cross-references)
- **Published articles** (from `resources/articles/published/`)
- **Project CAPs** (from `projects/*/`)
- **Knowledge base** (from `resources/knowledge/`)

### Process

1. Build graph of inter-file connections (links, tags, backlinks)
2. Identify nodes with in-degree < 2 (weakly connected)
3. For each isolated file:
   - Compute semantic similarity to other vault files
   - Suggest up to 3 connection targets
   - Check for potential merges
4. Identify orphaned topic clusters (related files with no links)
5. Generate connection recommendations with confidence scores

### Output

- **Orphan report:** `orphans-phase2.md`
  ```markdown
  # Orphaned Notes — Phase 2 Report
  Date: 2026-04-11
  
  ## Isolated Files (0-1 connections)
  
  ### daily/2026-02-15-kafka-notes.md
  **Connections:** 0 (fully isolated)
  **Suggested Links:**
  - → resources/articles/published/message-queues-architecture.md (0.92)
  - → daily/2026-01-30-event-driven-systems.md (0.87)
  - → projects/CAP-streaming-platform/README.md (0.79)
  
  **Action:** Review and add links, or archive if outdated.
  ```

- **Metadata:** `phase2-results.json`
  ```json
  {
    "timestamp": "2026-04-11T11:00:00Z",
    "phase": 2,
    "total_files": 256,
    "orphaned_files": 18,
    "orphan_clusters": 3,
    "suggestions_generated": 54,
    "next_action": "Review orphans-phase2.md and add connections"
  }
  ```

### Human Action Required

1. Open `orphans-phase2.md` and `phase2-results.json`
2. For each orphaned file:
   - Read the file and review suggested connections
   - Add links if suggestions are relevant
   - Decide: keep, merge with another file, or archive
   - Update tags or frontmatter as needed
3. Review orphan clusters:
   - Verify suggested connections between cluster members
   - Create summary articles if needed
4. Proceed to Phase 3 when orphans are reviewed

### Example Output

```markdown
## daily/2025-12-08-sidecar-pattern.md
**Current connections:** 1 (backlink from one project README)
**Suggested connections:**
- resources/articles/kubernetes-patterns.md (confidence: 0.94)
- projects/CAP-service-mesh/README.md (confidence: 0.88)
- daily/2025-11-20-microservices-architecture.md (confidence: 0.82)

**Recommendation:** Strong match for Kubernetes patterns article.
Add bidirectional link and review for merge opportunity.
```

---

## Phase 3: Templated Q&A

**Purpose:** Run standardized queries against the vault to extract insights, validate knowledge coverage, and identify improvement areas.

### Input

- **Vault state snapshot** (all current files and metadata)
- **Query templates** (from `reference/queries/`)
- **Previous Q&A results** (for trend analysis)

### Process

1. Load each query template (e.g., `project-summary.md`, `knowledge-gaps.md`)
2. Prepare vault context (file list, tags, structure)
3. Submit query to Claude with vault context
4. Parse Claude's response and structure results
5. Compare with previous results to identify changes
6. Generate trend report (what's improving, what's declining)
7. Archive results with metadata

### Output

- **Query results:** `qa-results-YYYY-MM-DD.md`
  ```markdown
  # Q&A Results — 2026-04-11
  
  ## Query 1: Project Progress Summary
  
  ### Query
  Which projects have made the most progress this month?
  What are the top blockers and risks?
  
  ### Results
  
  **Top 3 Projects by Progress:**
  1. CAP-streaming-platform: 60% complete, on schedule
  2. CAP-api-gateway-v2: 45% complete, blocked on auth design
  3. CAP-infrastructure-automation: 30% complete, proceeding well
  
  ### Recommendations
  - Schedule design review for auth blocker
  - Consider resource reallocation if needed
  
  ## Query 2: Knowledge Gaps
  
  ...
  ```

- **Metadata:** `phase3-results.json`
  ```json
  {
    "timestamp": "2026-04-11T11:30:00Z",
    "phase": 3,
    "queries_executed": 2,
    "insights_found": 7,
    "trends": {
      "new_topics": ["ai-safety", "verification-protocols"],
      "declining_areas": ["legacy-systems"],
      "stable_areas": ["kubernetes", "python-patterns"]
    },
    "next_action": "Review qa-results-YYYY-MM-DD.md for insights"
  }
  ```

### Human Action Required

1. Open `qa-results-YYYY-MM-DD.md`
2. For each query result:
   - Review the insights and recommendations
   - Verify findings match your current understanding
   - Identify action items
   - Update relevant articles or projects based on insights
3. Review trend analysis
4. Archive useful results to `resources/queries/archive/`
5. Proceed to Phase 4

### Available Query Templates

- **`project-summary.md`:** Which projects are on track? What are blockers?
- **`knowledge-gaps.md`:** What knowledge areas are underrepresented? What should we document?

---

## Phase 4: Digest Generation

**Purpose:** Synthesize Phases 1-3 into a weekly summary report, archive all outputs, and reset the audit clock.

### Input

- **Phase 1 results:** `phase1-results.json` + draft articles
- **Phase 2 results:** `phase2-results.json` + orphan report
- **Phase 3 results:** `phase3-results.json` + Q&A results

### Process

1. Aggregate all phase outputs
2. Generate executive summary (key metrics, top actions)
3. Create action items list (with priorities and owners)
4. Compile detailed appendix (all phase outputs)
5. Generate archive filename: `weekly-digest-YYYY-WXX.md`
6. Write digest to `resources/queries/archive/`
7. Reset audit clock (update `.audit-timestamp` file)
8. Clean up temporary working files

### Output

- **Weekly digest:** `resources/queries/archive/weekly-digest-2026-W15.md`
  ```markdown
  # Weekly Digest — Week 15 (2026-04-07 to 2026-04-11)
  
  ## Executive Summary
  - 8 new articles drafted and published
  - 18 orphaned notes reviewed; 5 connected, 3 archived
  - 2 Q&A queries executed; 7 insights found
  - 3 project blockers identified
  - Recommended actions: 5 high priority, 8 medium priority
  
  ## Key Metrics
  | Metric | Value | Trend |
  |--------|-------|-------|
  | Total articles | 142 | +8 |
  | Orphaned files | 12 | -6 |
  | Average connections | 3.2 | +0.4 |
  | Coverage score | 76% | +2% |
  
  ## Top Action Items
  1. **[HIGH]** Review and approve Kubernetes health checks article
  2. **[HIGH]** Resolve auth design blocker in API Gateway project
  3. **[MEDIUM]** Merge sidecar-pattern notes with main K8s article
  
  ## Detailed Results
  [Appendix A: Phase 1 Results]
  [Appendix B: Phase 2 Orphan Report]
  [Appendix C: Phase 3 Q&A Results]
  ```

- **Metadata:** `phase4-results.json`
  ```json
  {
    "timestamp": "2026-04-11T12:00:00Z",
    "phase": 4,
    "digest_file": "weekly-digest-2026-W15.md",
    "cycle_complete": true,
    "next_audit_date": "2026-04-18T10:00:00Z",
    "summary": {
      "articles_drafted": 8,
      "articles_published": 8,
      "orphans_processed": 18,
      "action_items": 13,
      "status": "ready for commit"
    }
  }
  ```

### Human Action Required

1. Open `resources/queries/archive/weekly-digest-YYYY-WXX.md`
2. Review executive summary and metrics
3. Review action items and assign owners/deadlines
4. Verify all appendices are present and accurate
5. Commit digest and phase outputs to vault git repo
6. Update project CAPs based on identified blockers
7. Update knowledge base articles based on Q&A findings
8. Celebrate progress and plan for next week

### Example Digest Structure

```markdown
# Weekly Digest — Week 15 (2026-04-07 to 2026-04-11)

## At a Glance
✅ 8 articles published | ✅ 18 orphans reviewed | ✅ 2 queries executed
📊 Coverage improved 2% | 🚀 3 blockers identified | 📋 13 action items

[Full digest content...]
```

---

## Failure Handling

| Failure Mode | Detection | Recovery |
|--------------|-----------|----------|
| Phase 1 markdown parsing fails | JSON validation error | Re-check source markdown syntax, retry phase |
| Phase 2 graph construction incomplete | Fewer orphans than expected | Rebuild connection graph, check for parsing errors |
| Phase 3 Q&A timeout | Partial results in JSON | Retry query with reduced vault context, check token usage |
| Phase 4 archive write fails | Digest file not created | Check disk space, verify write permissions, retry |
| Concurrent phase execution | Lock file detected | Wait for other process, or remove stale lock and retry |

---

## Idempotency & Safety

### Idempotent Operations

- **Phase 1:** Draft articles in separate directory; no overwrites
- **Phase 2:** Orphan report is read-only analysis
- **Phase 3:** Results timestamped and archived separately each run
- **Phase 4:** Digest uses week number; running twice produces same week file

### Safety Checks

- ✅ All phases validate input files before processing
- ✅ No vault files are modified until human approval
- ✅ All outputs are timestamped and archived
- ✅ Git commit required before next audit cycle
- ✅ Cleanup phase only removes temporary working files

### Re-running Phases

Safe to re-run phases 1-3:
```bash
brain-audit --phase 1  # Overwrites previous phase1-results.json
brain-audit --phase 2  # Overwrites previous orphans-phase2.md
brain-audit --phase 3  # Overwrites previous qa-results-*.md
```

Phase 4 is special (must be run after phases 1-3):
```bash
brain-audit --phase 4  # Generates new weekly digest with unique filename
```

---

## Debugging & Logs

Each phase writes logs to `audit-logs/`:
- `audit-logs/phase1-YYYY-MM-DDTHH:MM:SSZ.log`
- `audit-logs/phase2-YYYY-MM-DDTHH:MM:SSZ.log`
- `audit-logs/phase3-YYYY-MM-DDTHH:MM:SSZ.log`
- `audit-logs/phase4-YYYY-MM-DDTHH:MM:SSZ.log`

View logs:
```bash
tail -f audit-logs/phase1-*.log              # Follow live logs
cat audit-logs/phase1-2026-04-11T10:30:00Z.log  # View specific run
```

---

**Last Updated:** 2026-04-11  
**Version:** 1.0.0
