# Capture-date recovery: fields, trust order, and application

## Why filesystem mtime is untrustworthy for recovered files

`shutil.copy2` (used by `triage.py` when copying survivors into
`clean/`/`review/`) preserves the *source* file's mtime/atime onto the
copy. For PhotoRec-recovered files, that source mtime is frequently just
the moment PhotoRec carved the file out during recovery, not the moment the
photo was taken — the tell is a large cluster of otherwise-unrelated files
all sharing the exact same mtime, matching the recovery run's date. CLI
upload tools that fall back to filesystem mtime when no usable EXIF date is
present (observed with `immich-cli upload`) will then import a huge batch
of photos all dated to the day of the disk recovery. This is exactly the
bug this reference file exists to prevent.

## Fields checked, by media type

Run via `exiftool -j <tags...> <path>` (JSON output, easy to parse; `-j`
also degrades gracefully — missing tags are simply absent keys rather than
errors).

**Images:**
- `DateTimeOriginal` (EXIF) — when the shutter fired. Highest trust.
- `CreateDate` (EXIF) — often identical to DateTimeOriginal, sometimes the
  only one present.
- `IPTC:DateCreated` / `XMP:DateCreated` / `XMP:CreateDate` — set by editing
  software (Lightroom, Photos apps) or by IPTC captioning workflows; can be
  the *editing* date rather than capture date, hence ranked below EXIF.

**Video:**
- `QuickTime:CreateDate` — the standard MP4/MOV container date field.
  Pillow does not read this at all; this is the concrete reason exiftool is
  required for video date recovery, not optional.
- `QuickTime:MediaCreateDate` / `TrackCreateDate` — sometimes more reliable
  than the top-level `CreateDate` on files with editing history.

**Always available, last resort:**
- `FileModifyDate` (i.e. the filesystem mtime exiftool would report anyway)
  — only used if nothing above is present, and it should be flagged as
  low-confidence rather than silently treated as equal to a real EXIF date.

## Trust order

```
EXIF DateTimeOriginal
  > EXIF CreateDate
  > IPTC/XMP date fields (DateCreated, XMP:CreateDate)
  > QuickTime CreateDate (video)
  > filesystem mtime (last resort — flag, don't silently trust)
```

`recover_dates.py` walks this list per file and stops at the first field
with a parseable value. Files that fall through to "filesystem mtime only"
are reported separately in the summary so a human can decide whether
they're worth investigating further (e.g. checking the original file's
directory of origin, or nearby files with real dates) rather than being
silently treated as if they had a confirmed date.

## Applying the recovered date

Two valid approaches — the script supports both, pick based on what the
destination system offers:

### A. Rewrite mtime before upload (`--apply-mtime`)

```python
os.utime(dest_path, (recovered_ts, recovered_ts))
```

Simplest option. Works with any uploader that falls back to mtime absent
EXIF (this is exactly the mechanism that caused the original bug, so
fixing the mtime before upload closes the loop). Only ever touches files
under `OUTPUT_DIR` — `recover_dates.py` should refuse to run against a
path that looks like one of the configured `SOURCE_DIRS`.

### B. Patch the destination system after upload (`--emit-patch-csv` + `apply_destination_patch.py`)

More precise — corrects the asset's actual capture-date field rather than
relying on a fallback — but needs (a) the destination to expose an
asset date-patch endpoint and (b) a way to match an already-uploaded
asset back to its source file (checksum or original filename both work if
the uploader preserves either).

**Check first whether you even need this.** Immich's own metadata-extraction
job re-reads EXIF from the uploaded file's actual bytes and uses it to set
`fileCreatedAt`/`localDateTime`, independent of whatever `fileCreatedAt` the
uploader sent at upload time. Verified live: `immich-cli upload` sends the
local file's mtime unconditionally as `fileCreatedAt` (`index.js:19887-19888`
in the CLI bundle — not "only if EXIF is missing", *every* file), but a
sample asset with real EXIF `DateTimeOriginal: 2025-09-20` still showed
`fileCreatedAt: 2025-09-20...` server-side, with the bogus upload-time mtime
surviving only in the separate `fileModifiedAt` field. So: **files with a
recovered EXIF/IPTC/XMP/QuickTime date (`recover_dates.py`'s "exif" /
"iptc_xmp" / "quicktime" buckets) self-correct in Immich without needing
this patch step at all.** Only the "no_reliable_date" bucket — files with
*zero* embedded date anywhere — actually needs `apply_destination_patch.py`,
and even then only for the quarantine step (B2 below), since there's no
recovered date to patch in. On a real 11,885-file run, 84.9% fell in the
self-correcting buckets and only 15.1% had no embedded date at all — run
`recover_dates.py --emit-patch-csv` and read its percentages before assuming
you need a big patch pass.

`scripts/apply_destination_patch.py` implements two things against
`--emit-patch-csv`'s output:

**B1. Patch dated rows.** For any row with a `recovered_date` (belt-and-
suspenders — covers destinations that *don't* self-correct from EXIF, or a
row where you want to force a specific value): match by `original_name` via
`POST /api/search/metadata {"originalFileName": ...}`, then bulk-apply via
`PUT /api/assets {"ids": [...], "dateTimeOriginal": "<iso>"}` — Immich's
*bulk* update endpoint (`AssetBulkUpdateDto`, `ids` + `dateTimeOriginal`),
grouped by date so N assets sharing a recovered date cost one API call, not
N. (Not `PATCH /api/assets/{id}` per-asset — that works too but is far
slower at scale; the bulk endpoint is the one to reach for.)

**B2. Quarantine undated rows.** For rows with no recovered date at all,
don't leave them silently sitting under whatever wrong date they picked up
(upload-time mtime, or "today") mixed into the real timeline. Match them the
same way, then: create (or reuse) an album via `POST /api/albums
{"albumName": "..."}`, bulk-set their date to an explicit placeholder via the
same `PUT /api/assets` call, and bulk-add them to the album via
`PUT /api/albums/{id}/assets {"ids": [...]}`. **The placeholder date must
come from the user — never invent one.** `apply_destination_patch.py`
requires `--placeholder-date` for exactly this reason; it will not default
one. A real run used `1994-11-16` because the user picked it when asked —
any fixed, memorable, obviously-not-real date the user chooses works, the
point is that it's *their* choice and it's easy to filter/find later via the
quarantine album.

```bash
uv run python3 scripts/apply_destination_patch.py \
  --csv recovered_dates.csv --backend immich \
  --quarantine-album "Undated / Recovered" --placeholder-date 1994-11-16
```

Only Immich is implemented (`build_immich_api()` in the script). Adapting to
another destination means writing an equivalent `find_asset_id_by_name` /
`bulk_set_date` / `ensure_album` / `bulk_add_to_album` — the matching and
batching logic around them is backend-agnostic.

**Before running this against a self-hosted destination sitting behind SSO
(Authelia, oauth2-proxy, etc.): read `reference/destination-patch-immich.md`
first.** A real deployment lost significant time to a reverse-proxy
misconfiguration that broke *all* API-key auth with a misleading, unrelated-
looking client-side crash — not a permissions problem, and not anything this
script or `recover_dates.py` can detect or work around on their own.

**Auth note:** if you're debugging this by hand with `curl` and an API key
header, be aware some terminal/agent environments run an output-redaction
proxy that can mangle command output containing sensitive-looking strings.
If upload/auth debugging output looks corrupted or redacted unexpectedly,
check whether a raw/passthrough mode is available before concluding the
API call itself failed.
