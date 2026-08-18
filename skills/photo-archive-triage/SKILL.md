---
name: photo-archive-triage
description: >
  Non-destructively triage large, messy photo/video collections — PhotoRec
  data-recovery dumps (recup_dir.N folders), old phone backups, duplicated
  exports — into a clean, deduplicated, correctly-dated set ready to import
  into Immich or another photo manager. Covers exact-duplicate detection,
  corrupt/truncated file screening, thumbnail/junk triage, and recovering
  true capture dates when EXIF is missing or the file's timestamp is wrong
  (near-universal with recovered files). Use whenever the user mentions
  PhotoRec, recup_dir, recovering photos from a dying/failed drive,
  deduplicating a photo library, "why are all my photos dated the same
  day", or cleaning up before an Immich/Google Photos import — even for a
  plain "dedup this folder" ask, since that hides the corrupt-file and
  wrong-date problems this skill catches. Skip it for a single file or an
  already-organized library with no dedup/corruption/date concerns.
---

# Photo & Video Archive Triage

Turns a messy source pile into a clean output tree without ever modifying or
deleting anything in the source. Built from a real run that triaged 67,962
PhotoRec-recovered files (45,358 exact dupes, 12,499 clean, 10,103 flagged
for review, 2 corrupt) ahead of an Immich import.

## Design principles — read before running anything

**Never touch the source.** Every step reads from `SOURCE_DIRS` and writes
only into a separate `OUTPUT_DIR`. Nothing is ever deleted or modified
in-place in the source. If a step can't decide whether a file is good, it
copies it to a `review/` subfolder for a human to skim later — it does not
delete it and does not guess.

**Two-tier dedup, not one.** This skill does exact-duplicate detection only
(byte-identical, via streamed SHA-256). It deliberately does **not**
implement near-duplicate / perceptual-hash matching (e.g. catching the same
photo saved twice at different resolutions or JPEG quality). That's a
different, fuzzier problem, and the destination system usually already
solves it well: Immich's built-in duplicate detection is CLIP-embedding
based (`smartSearch` + `machineLearning.duplicateDetection`, enabled by
default with `maxDistance: 0.01`) and ships a genuinely good "which copy do
I keep" heuristic — largest file size, then most-populated EXIF fields as
tiebreaker (`suggestDuplicateKeepAssetIds` in Immich's
`duplicate.service.ts`). Reimplementing perceptual hashing locally would be
slower, riskier (false positives merge two different photos), and
duplicative of work the target system already does on ingest. So: do the
cheap, zero-false-positive exact-hash pass locally, and let near-duplicates
ride through to the destination system's own dedup UI. If the destination
system has no such feature, that's the one case worth adding a local
perceptual-hash pass — treat it as an explicit extension, not the default.

**Resumability is not optional.** At tens of thousands of files, validity
checks and hashing take hours, and something *will* interrupt the run — a
missing dependency, a Ctrl-C, a crash. Every script in this skill uses a
SQLite ledger keyed by source path so a re-run picks up exactly where it
left off instead of reprocessing or, worse, re-copying already-copied files.

**Capture date is a separate concern from validity.** A file can be a
perfectly valid, non-duplicate photo and still carry a completely wrong
date. Don't treat "triage passed" as "dates are correct" — see the
dedicated date-recovery step below.

## Prerequisites

Check before running anything: `bash scripts/check_prereqs.sh`

It checks for `uv`, `exiftool`, and `ffprobe`, and if any are missing it
prints the exact install command and stops — it never tries to silently
install things itself (installing `exiftool`/`ffmpeg` needs `apt-get` and a
real sudo prompt; there's no way to self-heal that safely). Report the
missing-tool message to the user verbatim rather than working around it.

All Python steps run via `uv run --with <deps> python3 script.py`. Do not
assume a bare `pip` or `python3 -m pip` is available — in the environment
this skill was built in, neither was, while `uv` fetched Pillow on first use
with no setup. Treat `uv run --with Pillow --with piexif` (or whatever the
script needs) as the standard invocation, not a fallback.

## Workflow

### 1. Define the scope

Confirm with the user (or infer from what they've said):
- One or more `SOURCE_DIRS` — read-only, never written to.
- One `OUTPUT_DIR` for the clean set — the script creates `clean/` and
  `review/` subfolders inside it.
- Whether this is PhotoRec output specifically. PhotoRec recovers *every*
  file type it can carve — documents, executables, archives, fragments —
  indiscriminately, mixed in with the real photos/videos. `triage.py`
  applies an extension allowlist (`reference/extension-allowlist.md`) as the
  very first filter, before any I/O-heavy work, and files that don't match
  are skipped silently — they're not photos or videos, so there's nothing
  to log. Don't skip this filter even for non-PhotoRec sources; it's cheap
  and harmless there too.

### 2. Run the triage pipeline

```bash
uv run --with Pillow python3 scripts/triage.py \
  --source /path/to/recup_dir.1 --source /path/to/recup_dir.2 \
  --output /path/to/OUTPUT_DIR \
  --db /path/to/OUTPUT_DIR/ledger.sqlite3
```

For each candidate file (post-allowlist), in order:

1. **Validity.** Images: `Image.open(path)` then `im.load()` — the `load()`
   call matters, since a truncated/corrupt PhotoRec carve can pass
   `Image.open`'s header parse and still fail on full decode. Videos:
   `ffprobe -v error -show_entries stream=codec_type -of csv=p=0 <path>`
   with a timeout (default 30s — a hung ffprobe on a garbage file shouldn't
   stall the whole run), exit code 0 and `video` in the output required.
   Failures are logged to `invalid.jsonl` (path + size) and never copied.
2. **Exact dedup.** Streamed SHA-256 (1MB chunks — don't load multi-GB video
   files fully into memory to hash them). First file with a given hash is
   canonical and gets copied; every later file with the same hash is logged
   to `duplicates.jsonl` (path, hash, and which canonical source it
   duplicates) and never copied.
3. **Junk/thumbnail heuristic.** Files under 30KB, or images under 200x200px,
   are routed to `OUTPUT_DIR/review/` instead of `OUTPUT_DIR/clean/` —
   flagged for a human skim, never auto-deleted. In the reference run, 10,103
   of 67,962 files landed here; the user skimmed and bulk-deleted the whole
   folder in the end, which is a legitimate outcome of this step — the point
   is that it was a human decision on a segregated folder, not something the
   pipeline decided unilaterally.
4. **Copy.** Survivors are copied (`shutil.copy2`, so whatever timestamp the
   source file has travels with it — see the date-recovery step for why
   that timestamp is not to be trusted yet) into `clean/` or `review/`.
   Progress commits to the SQLite ledger every 500 files with an ETA
   printed from files/sec so far. Interrupting (Ctrl-C, crash, or an
   intentional stop to install a missing dependency) is safe — pending rows
   stay `pending` and the next run resumes from there. This is exactly how
   a real run handled `ffprobe` not being installed yet: the script left
   every video `pending`, kept processing images, and picked the videos up
   automatically once `ffmpeg` was installed and the script re-run.

Ledger schema, resumability details, and the SQLite gotcha below are in
`reference/sqlite-ledger-schema.md` — read it before modifying `triage.py`
or writing ad hoc summary queries against `ledger.sqlite3`.

**Gotcha worth knowing up front:** a naive summary query like
`SELECT category, COUNT(*) FROM files GROUP BY category ORDER BY COUNT(*) DESC`
fails in SQLite with `no such column: COUNT(*)` — `ORDER BY` can't see an
unaliased aggregate from the SELECT list. Always alias it:
`SELECT category, COUNT(*) AS cnt FROM files GROUP BY category ORDER BY cnt DESC`.
`triage.py --summary` already does this correctly; it's only a trap if you
write your own query against the ledger.

### 3. Recover true capture dates

This is a distinct step, not folded into step 2, because it needs to run
against the *copies* in `clean/`/`review/` and because getting it wrong is
subtle enough to deserve its own pass and its own review.

**Why this matters:** `shutil.copy2` preserves the *source* file's mtime.
For PhotoRec output, that mtime is very often an artifact of when PhotoRec
wrote the file during recovery — not when the photo was taken. The
tell-tale sign is a large cluster of unrelated files all sharing the exact
same mtime, matching the day the recovery ran. Files from an
already-organized backup source (not raw carved output) tend to have
varied, plausible mtimes and are less suspect, but should still go through
this step rather than being assumed correct. CLI uploaders that fall back
to filesystem mtime when no EXIF date is present (this is the observed
behavior of `immich-cli upload`, and is common in this class of tool) will
otherwise silently import thousands of photos dated to the day of a disk
recovery, not the day they were actually taken.

**Why exiftool, not Pillow, for this specifically.** `Image.getexif()` is
fine for "does this file have basic EXIF," but it can silently return
incomplete data on recovery-damaged files — missing `DateTimeOriginal` even
when a deeper parse would find a date in MakerNotes, a truncated-but-still-
parseable IFD, or (for video) QuickTime/MP4 atoms like `CreateDate`, which
Pillow doesn't read at all. `exiftool` (`libimage-exiftool-perl` on
Debian/Ubuntu) reads all of EXIF, IPTC, XMP, MakerNotes, and video container
metadata, and is materially more tolerant of partially-corrupt files. Use
Pillow for the fast validity check in step 2 (already loaded, already fully
decoding the image) and exiftool for date recovery — they're doing
different jobs and one doesn't substitute for the other here.

```bash
uv run python3 scripts/recover_dates.py \
  --dir /path/to/OUTPUT_DIR/clean \
  --apply-mtime
```

`recover_dates.py` runs exiftool **once** for the whole tree
(`exiftool -r -j <tags...> <dir>`), not once per file — a real 11,885-file
run finished in under a minute this way. One-subprocess-per-file was an
early mistake in this skill's first draft; don't reintroduce it when editing
this script.

Trust order (first match wins — full field list in
`reference/date-trust-order.md`):
`EXIF DateTimeOriginal` > `EXIF CreateDate` > `IPTC/XMP date fields` >
`QuickTime CreateDate` (video) > filesystem mtime (last resort — i.e. leave
it alone and flag it, don't invent a date).

Two ways to land the recovered date, both legitimate — pick based on the
destination system:

- **`--apply-mtime`**: rewrite the copy's mtime (`os.utime`) to the
  recovered date before upload. Simplest; works with any uploader that
  falls back to mtime, no destination-side changes needed. Only ever
  touches files under `OUTPUT_DIR` — never the source.
- **`--emit-patch-csv OUT.csv`**: instead of touching the file, write a
  `source_path, checksum, recovered_date` table for `apply_destination_patch.py`
  to apply after upload. More precise, avoids a re-upload — but read the
  next paragraph before assuming you need it.

**Check the summary percentages before reaching for the patch step.**
Immich's own metadata-extraction job re-reads EXIF from the uploaded
bytes and uses it for the asset's real date, independent of whatever the
uploader sent at upload time — verified live: `immich-cli upload` sends the
local mtime unconditionally, yet an asset with real EXIF still showed the
correct EXIF-derived date server-side once processed. So files in the
"exif" / "iptc_xmp" / "quicktime" summary buckets **self-correct on the
destination and don't need patching.** Only the "no_reliable_date" bucket
needs `apply_destination_patch.py`, and only for quarantining (there's no
recovered date to patch in for those). On a real run this bucket was 15.1%
of the set — check your own percentages, don't assume the whole batch needs
the patch step.

```bash
uv run python3 scripts/apply_destination_patch.py \
  --csv recovered_dates.csv --backend immich \
  --quarantine-album "Undated / Recovered" --placeholder-date 1994-11-16
```

`--placeholder-date` is required and must come from asking the user —
the script refuses to default or invent one. Full endpoint contract, and a
costly SSO/reverse-proxy gotcha to check *before* running this against a
self-hosted destination, are in `reference/destination-patch-immich.md`.

Document which mode was used and why when handing results back to the user
— it affects how to fix mistakes later.

### 4. Hand off

Upload/import `OUTPUT_DIR/clean/` with whatever tool the destination system
provides. Let its own near-duplicate detection (CLIP-embedding or
equivalent) handle near-dupes — that was deliberately not done locally (see
Design principles). `OUTPUT_DIR/review/` and the two JSONL logs
(`invalid.jsonl`, `duplicates.jsonl`) are for human skimming, not for
automatic action; ask the user what they want done with `review/` rather
than assuming it should also be uploaded or deleted.

## Scripts

- `scripts/check_prereqs.sh` — checks for `uv`, `exiftool`, `ffprobe`;
  reports exact install commands and exits non-zero rather than installing
  anything itself.
- `scripts/triage.py` — the resumable validity + exact-dedup + junk-triage
  pipeline described in step 2. `--summary` prints ledger counts by
  category (dedup-safe query, see the gotcha above).
- `scripts/recover_dates.py` — the exiftool-based date-recovery pass from
  step 3, supporting both `--apply-mtime` and `--emit-patch-csv`. Single
  batched `exiftool -r` call for the whole tree, not per-file.
- `scripts/apply_destination_patch.py` — applies an `--emit-patch-csv`
  output to an already-uploaded destination library: bulk-patches dated
  rows (belt-and-suspenders; usually unnecessary, see step 3) and
  quarantines undated rows into a named album at a user-provided placeholder
  date. Immich implemented concretely; other backends need an equivalent
  `find_asset_id_by_name`/`bulk_set_date`/`ensure_album`/`bulk_add_to_album`.

## Reference files

- `reference/sqlite-ledger-schema.md` — `files`/`hash_index` table
  definitions, resumable-query patterns, and the aggregate-alias gotcha in
  full.
- `reference/date-trust-order.md` — the full exiftool tag list checked per
  media type, the trust-order rationale, and the destination-patch decision
  (including why most files don't need it).
- `reference/destination-patch-immich.md` — the exact Immich API contract
  `apply_destination_patch.py` uses, and a real, costly SSO/reverse-proxy
  gotcha (a misleading client-side crash that had nothing to do with API-key
  permissions) worth reading before patching any self-hosted, SSO-fronted
  destination.
- `reference/extension-allowlist.md` — the image/video extension list used
  to filter PhotoRec's indiscriminate output, and why it's applied before
  any hashing or decoding work.

## Common pitfalls

- Treating "copied to `clean/`" as "dates are correct" — it isn't until
  step 3 has run. Don't hand a freshly-triaged-but-not-date-recovered folder
  to an uploader and assume the dates will be fine.
- Writing an unaliased `COUNT(*)` into an `ORDER BY` against the ledger —
  see the gotcha above.
- Assuming `pip`/`python3 -m pip` works — provision every Python dependency
  through `uv run --with <pkg>`.
- Trying to `apt-get install` `exiftool`/`ffmpeg` automatically — always
  prompt the human; sudo prompts need a real user.
- Reimplementing perceptual/near-duplicate hashing locally when the
  destination system already does it — check first before adding that
  complexity.
- Running `triage.py` or `recover_dates.py` against `SOURCE_DIRS` instead of
  `OUTPUT_DIR` for the date-recovery step — only copies get their mtime
  rewritten, never sources.
- Calling exiftool once per file instead of once per tree — kills
  performance at scale for no accuracy benefit.
- Running `apply_destination_patch.py` on the whole CSV when only the
  "no_reliable_date" rows actually need it — check `recover_dates.py`'s
  summary percentages first; EXIF/IPTC/XMP/QuickTime-dated files usually
  self-correct on the destination without any patch call.
- Inventing a placeholder date for undated assets instead of asking the
  user — `apply_destination_patch.py` requires `--placeholder-date`
  explicitly for this reason.
- Assuming a self-hosted, SSO-fronted destination's API is reachable just
  because the web UI loads — check `reference/destination-patch-immich.md`'s
  one-line `curl` sanity check before debugging a login/upload failure as a
  permissions problem.
