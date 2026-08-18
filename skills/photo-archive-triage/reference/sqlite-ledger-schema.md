# SQLite ledger schema

`triage.py` keeps all state in one SQLite file (`--db`), passed alongside
`--output`. Nothing about progress lives in memory only — every batch is
committed, so the process can be killed at any point without corrupting
state or losing track of what's done.

## Tables

```sql
CREATE TABLE IF NOT EXISTS files (
    source_path   TEXT PRIMARY KEY,
    status        TEXT NOT NULL DEFAULT 'pending',  -- pending | processed | error
    category      TEXT,                              -- clean | review | duplicate | invalid
    size_bytes    INTEGER,
    sha256        TEXT,
    dest_path     TEXT,
    error         TEXT,
    updated_at    REAL
);

CREATE TABLE IF NOT EXISTS hash_index (
    sha256          TEXT PRIMARY KEY,
    canonical_source TEXT NOT NULL,
    dest_path       TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
```

`files` is the per-source-file ledger: one row per candidate file that
passed the extension allowlist. `hash_index` maps a content hash to the
first (canonical) file that had it, so later files with the same hash can
be identified as duplicates in O(1) without rescanning `files`.

## Resumability pattern

On startup, `triage.py`:

1. Walks `SOURCE_DIRS`, applies the extension allowlist, and `INSERT OR
   IGNORE`s every candidate path into `files` with `status='pending'`. This
   makes re-running after adding a new source directory safe — existing
   rows are untouched.
2. Selects `WHERE status = 'pending'` and processes those, committing every
   500 rows (`COMMIT_EVERY` in the script) along with a files/sec-based ETA
   printed to stdout.
3. Any row left `pending` after an interrupted run (Ctrl-C, crash, or a
   deliberate stop — e.g. `ffprobe` wasn't installed yet, so every video
   file failed the "is a required tool available" pre-check and was left
   `pending` rather than marked `error`) is simply picked up again on the
   next invocation. This is why "missing dependency" is handled as "leave
   pending, tell the user what to install" rather than "mark as error" —
   errors are for files, missing tools are an environment problem that
   resolves itself on re-run once fixed.

## Aggregate-column gotcha

SQLite's `ORDER BY` cannot reference an unaliased aggregate expression from
the `SELECT` list by its expression text. This fails:

```sql
SELECT category, COUNT(*)
FROM files
WHERE status = 'processed'
GROUP BY category
ORDER BY COUNT(*) DESC;
-- sqlite3.OperationalError: no such column: COUNT(*)
```

This works — alias the aggregate and order by the alias:

```sql
SELECT category, COUNT(*) AS cnt
FROM files
WHERE status = 'processed'
GROUP BY category
ORDER BY cnt DESC;
```

`triage.py --summary` uses the aliased form. Any ad hoc query written
against the ledger (e.g. while debugging on the command line with
`sqlite3 ledger.sqlite3`) should follow the same pattern.

## Useful ad hoc queries

```sql
-- How much work is left?
SELECT status, COUNT(*) AS cnt FROM files GROUP BY status ORDER BY cnt DESC;

-- What got marked invalid, and why?
SELECT source_path, error FROM files WHERE category = 'invalid';

-- Which source file is the canonical copy for a given duplicate?
SELECT canonical_source, dest_path FROM hash_index WHERE sha256 = ?;

-- Total bytes saved by dedup (duplicates' sizes, since they weren't copied)
SELECT SUM(size_bytes) FROM files WHERE category = 'duplicate';
```
