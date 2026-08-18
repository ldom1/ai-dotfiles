#!/usr/bin/env python3
"""
photo-archive-triage: recover true capture dates via exiftool and either
apply them as the file's mtime, or emit a CSV for a post-upload API patch.

Run with:

    uv run python3 recover_dates.py --dir /path/to/OUTPUT_DIR/clean --apply-mtime

or

    uv run python3 recover_dates.py --dir /path/to/OUTPUT_DIR/clean \
        --emit-patch-csv recovered_dates.csv

Only stdlib is needed (subprocess/json/csv/os) — this still runs via `uv run`
for consistency with the rest of the skill's tooling, and because it's the
one guaranteed-available Python launcher in the environment this skill was
built for.

Never point --dir at a SOURCE_DIRS path — pass --refuse-prefix for each
source directory and the script will abort rather than risk rewriting a
source file's timestamp.

Performance note: this calls exiftool ONCE for the whole tree (`-r`,
recursive), not once per file. A real run against 11,885 files took under
a minute this way; one-subprocess-per-file at that scale scales far worse
purely from process-spawn overhead, with no accuracy benefit — an earlier
draft of this script did exactly that and was replaced. Keep it batched.
"""
import argparse
import csv
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

# First match wins. See reference/date-trust-order.md for the full rationale.
DATE_FIELDS_IN_TRUST_ORDER = [
    "DateTimeOriginal",
    "CreateDate",
    "IPTC:DateCreated",
    "XMP:DateCreated",
    "XMP:CreateDate",
    "QuickTime:CreateDate",
    "QuickTime:MediaCreateDate",
    "QuickTime:TrackCreateDate",
]

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif", ".bmp", ".tif", ".tiff", ".webp",
              ".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".3g2", ".mts", ".m2ts", ".wmv", ".flv", ".webm"}


def check_exiftool():
    try:
        subprocess.run(["exiftool", "-ver"], capture_output=True, check=True, timeout=10)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("exiftool not found. Install it with:\n"
              "  sudo apt-get update && sudo apt-get install -y libimage-exiftool-perl\n"
              "then re-run. (Not silently working around this — Pillow's EXIF reader is "
              "not reliable enough for recovery-damaged files; see reference/date-trust-order.md.)",
              file=sys.stderr)
        sys.exit(1)


def scan_tree(target: Path) -> list[dict]:
    """One exiftool call for the entire tree. Returns exiftool's raw -j records."""
    cmd = ["exiftool", "-r", "-j"] + [f"-{f}" for f in DATE_FIELDS_IN_TRUST_ORDER] + [str(target)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=1800)
    if not result.stdout.strip():
        print(f"exiftool produced no output (stderr: {result.stderr.strip()[:500]})", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"Could not parse exiftool JSON output: {e}", file=sys.stderr)
        return []


def pick_date(record: dict) -> tuple[str | None, str | None]:
    """Returns (iso_date_or_None, field_name_used_or_None) for one exiftool record."""
    for field in DATE_FIELDS_IN_TRUST_ORDER:
        raw = record.get(field)
        if not raw:
            continue
        # exiftool's default format is "YYYY:MM:DD HH:MM:SS", optionally
        # followed by fractional seconds and/or a timezone offset — the
        # first 19 characters are always the fixed-width date+time part.
        raw_trimmed = raw.strip()[:19]
        try:
            dt = datetime.strptime(raw_trimmed, "%Y:%m:%d %H:%M:%S")
            return dt.isoformat(), field
        except ValueError:
            continue
    return None, None


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--dir", type=Path, required=True, help="OUTPUT_DIR/clean or /review — never a source dir")
    p.add_argument("--apply-mtime", action="store_true", help="rewrite each file's mtime to the recovered date")
    p.add_argument("--emit-patch-csv", type=Path, help="write source-file/checksum/date rows for a post-upload API patch instead")
    p.add_argument("--refuse-prefix", action="append", dest="refuse_prefixes", type=Path, default=[],
                    help="abort if --dir resolves under any of these (pass your SOURCE_DIRS here as a safety net)")
    args = p.parse_args()

    if not args.apply_mtime and not args.emit_patch_csv:
        p.error("pass --apply-mtime, --emit-patch-csv, or both")

    target = args.dir.resolve()
    for prefix in args.refuse_prefixes:
        if target == prefix.resolve() or prefix.resolve() in target.parents:
            print(f"Refusing to run: --dir {target} is inside a source directory ({prefix}). "
                  f"This script must only touch copies in OUTPUT_DIR.", file=sys.stderr)
            sys.exit(1)

    check_exiftool()

    print(f"Scanning {target} with a single recursive exiftool pass...")
    records = scan_tree(target)
    records = [r for r in records if Path(r["SourceFile"]).suffix.lower() in (IMAGE_EXTS | VIDEO_EXTS)]
    print(f"  {len(records)} media file(s) read")

    rows = []
    counts = {"exif": 0, "iptc_xmp": 0, "quicktime": 0, "no_reliable_date": 0}

    for record in records:
        path = Path(record["SourceFile"])
        iso_date, field = pick_date(record)
        if field in ("DateTimeOriginal", "CreateDate"):
            counts["exif"] += 1
        elif field and field.startswith("QuickTime"):
            counts["quicktime"] += 1
        elif field:
            counts["iptc_xmp"] += 1
        else:
            counts["no_reliable_date"] += 1

        if iso_date and args.apply_mtime:
            ts = datetime.fromisoformat(iso_date).timestamp()
            import os
            os.utime(path, (ts, ts))

        # dest filenames are written by triage.py as "<sha256[:16]>_<original name>"
        checksum_prefix, _, original_name = path.name.partition("_")
        rows.append({
            "file_path": str(path),
            "checksum_prefix": checksum_prefix if len(checksum_prefix) == 16 else "",
            "original_name": original_name or path.name,
            "recovered_date": iso_date or "",
            "source_field": field or "none (mtime unchanged)",
        })

    if args.emit_patch_csv:
        with open(args.emit_patch_csv, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=["file_path", "checksum_prefix", "original_name", "recovered_date", "source_field"])
            writer.writeheader()
            writer.writerows(rows)
        print(f"Wrote {len(rows)} row(s) to {args.emit_patch_csv}")

    total = len(rows) or 1
    print("Summary:")
    print(f"  EXIF DateTimeOriginal/CreateDate: {counts['exif']} ({100*counts['exif']/total:.1f}%)")
    print(f"  IPTC/XMP date fields:             {counts['iptc_xmp']} ({100*counts['iptc_xmp']/total:.1f}%)")
    print(f"  QuickTime (video) date fields:    {counts['quicktime']} ({100*counts['quicktime']/total:.1f}%)")
    print(f"  No reliable date found:           {counts['no_reliable_date']} ({100*counts['no_reliable_date']/total:.1f}%) "
          f"— left as-is; see scripts/apply_destination_patch.py to quarantine these instead of "
          f"leaving them under a wrong recovery-run date.")


if __name__ == "__main__":
    main()
