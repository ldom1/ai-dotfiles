#!/usr/bin/env python3
"""
photo-archive-triage: resumable, non-destructive validity + exact-dedup +
junk-triage pass over a pile of photo/video files.

Run via uv so Pillow doesn't need to be pre-installed:

    uv run --with Pillow python3 triage.py \
        --source /path/to/recup_dir.1 --source /path/to/recup_dir.2 \
        --output /path/to/OUTPUT_DIR \
        --db /path/to/OUTPUT_DIR/ledger.sqlite3

Re-running with the same --db is always safe: files already marked
'processed' are skipped, and interrupting mid-run (Ctrl-C, crash, or a
deliberate stop to install a missing dependency) leaves unfinished files
'pending' for the next run to pick up.

Never touches SOURCE_DIRS beyond reading — nothing is deleted or modified
in place there. Survivors are *copied* into OUTPUT_DIR/clean or
OUTPUT_DIR/review.
"""
import argparse
import hashlib
import shutil
import sqlite3
import subprocess
import sys
import time
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None  # only required if an image file is actually encountered

IMAGE_EXTS = {
    ".jpg", ".jpeg", ".png", ".heic", ".heif", ".gif", ".bmp", ".tif", ".tiff",
    ".webp", ".cr2", ".cr3", ".nef", ".arw", ".dng", ".orf", ".rw2", ".raf",
}
VIDEO_EXTS = {
    ".mp4", ".mov", ".avi", ".mkv", ".m4v", ".3gp", ".3g2", ".mts", ".m2ts",
    ".wmv", ".flv", ".webm",
}
EXTENSION_ALLOWLIST = IMAGE_EXTS | VIDEO_EXTS

JUNK_MIN_BYTES = 30 * 1024   # below this size, route to review/ regardless of type
JUNK_MIN_DIM = 200           # images with both dimensions below this go to review/
COMMIT_EVERY = 500
FFPROBE_TIMEOUT_S = 30

SCHEMA = """
CREATE TABLE IF NOT EXISTS files (
    source_path   TEXT PRIMARY KEY,
    status        TEXT NOT NULL DEFAULT 'pending',
    category      TEXT,
    size_bytes    INTEGER,
    sha256        TEXT,
    dest_path     TEXT,
    error         TEXT,
    updated_at    REAL
);
CREATE TABLE IF NOT EXISTS hash_index (
    sha256           TEXT PRIMARY KEY,
    canonical_source TEXT NOT NULL,
    dest_path        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_files_status ON files(status);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(str(db_path))
    conn.executescript(SCHEMA)
    return conn


def discover(conn: sqlite3.Connection, source_dirs: list[Path]) -> int:
    """Walk source_dirs, apply the extension allowlist, and register any
    not-yet-seen file as a pending row. Safe to call repeatedly (e.g. after
    adding a new source dir) — existing rows are left untouched."""
    added = 0
    cur = conn.cursor()
    for src in source_dirs:
        for path in src.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix.lower() not in EXTENSION_ALLOWLIST:
                continue  # not a photo/video candidate — skip silently, no log
            cur.execute(
                "INSERT OR IGNORE INTO files (source_path, status) VALUES (?, 'pending')",
                (str(path),),
            )
            added += cur.rowcount
    conn.commit()
    return added


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def is_valid_image(path: Path) -> bool:
    if Image is None:
        raise RuntimeError("Pillow not available — run via: uv run --with Pillow python3 triage.py ...")
    try:
        im = Image.open(path)
        im.load()  # forces full decode; a header-only check would miss truncated files
        return True
    except Exception:
        return False


def is_valid_video(path: Path) -> bool:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(path)],
            capture_output=True, text=True, timeout=FFPROBE_TIMEOUT_S,
        )
        return result.returncode == 0 and "video" in result.stdout
    except FileNotFoundError:
        # ffprobe not installed — leave this file pending rather than failing it.
        # It will be picked up automatically once ffmpeg is installed and the
        # script is re-run (see reference/sqlite-ledger-schema.md).
        raise
    except subprocess.TimeoutExpired:
        return False


def image_dims_below_threshold(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            w, h = im.size
            return w < JUNK_MIN_DIM and h < JUNK_MIN_DIM
    except Exception:
        return False  # already caught by is_valid_image; don't double-report


def process_one(conn: sqlite3.Connection, source_path: Path, output_dir: Path) -> tuple[str, str | None]:
    """Returns (status, error). Mutates the ledger for this one row."""
    ext = source_path.suffix.lower()
    size = source_path.stat().st_size

    if ext in IMAGE_EXTS:
        valid = is_valid_image(source_path)
        invalid_reason = "failed full decode"
    else:
        valid = is_valid_video(source_path)
        invalid_reason = "ffprobe validation failed"

    if not valid:
        conn.execute(
            "UPDATE files SET status='processed', category='invalid', size_bytes=?, error=? WHERE source_path=?",
            (size, invalid_reason, str(source_path)),
        )
        return "invalid", invalid_reason

    digest = sha256_of(source_path)

    cur = conn.cursor()
    cur.execute("SELECT canonical_source FROM hash_index WHERE sha256 = ?", (digest,))
    row = cur.fetchone()
    if row is not None:
        # Exact duplicate — never copied. Near-duplicates (resized/recompressed
        # copies) are NOT caught here on purpose; see SKILL.md Design principles.
        conn.execute(
            "UPDATE files SET status='processed', category='duplicate', size_bytes=?, sha256=? WHERE source_path=?",
            (size, digest, str(source_path)),
        )
        return "duplicate", None

    is_junk = size < JUNK_MIN_BYTES or (ext in IMAGE_EXTS and image_dims_below_threshold(source_path))
    subdir = "review" if is_junk else "clean"
    dest_dir = output_dir / subdir
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path = dest_dir / f"{digest[:16]}_{source_path.name}"

    # copy2 preserves the source mtime — for PhotoRec output that is often
    # the recovery time, not the capture time. This is deliberate: it keeps
    # whatever timestamp exists for now, and recover_dates.py (step 3 in
    # SKILL.md) is responsible for correcting it before upload.
    shutil.copy2(source_path, dest_path)

    conn.execute(
        "INSERT INTO hash_index (sha256, canonical_source, dest_path) VALUES (?, ?, ?)",
        (digest, str(source_path), str(dest_path)),
    )
    conn.execute(
        "UPDATE files SET status='processed', category=?, size_bytes=?, sha256=?, dest_path=? WHERE source_path=?",
        (subdir, size, digest, str(dest_path), str(source_path)),
    )
    return subdir, None


def run(source_dirs: list[Path], output_dir: Path, db_path: Path):
    conn = connect(db_path)
    added = discover(conn, source_dirs)
    if added:
        print(f"Registered {added} new candidate file(s).")

    pending = conn.execute("SELECT source_path FROM files WHERE status='pending'").fetchall()
    total = len(pending)
    print(f"{total} file(s) pending.")
    if total == 0:
        return

    start = time.time()
    done = 0
    ffprobe_missing_warned = False
    for (source_path_str,) in pending:
        source_path = Path(source_path_str)
        try:
            if not source_path.exists():
                conn.execute(
                    "UPDATE files SET status='error', error='source file vanished' WHERE source_path=?",
                    (source_path_str,),
                )
            else:
                process_one(conn, source_path, output_dir)
        except FileNotFoundError:
            # ffprobe missing — leave this (and every other video) pending.
            if not ffprobe_missing_warned:
                print("ffprobe not found — leaving video files pending. "
                      "Install ffmpeg (see scripts/check_prereqs.sh) and re-run.")
                ffprobe_missing_warned = True
            continue
        except Exception as e:
            conn.execute(
                "UPDATE files SET status='error', error=? WHERE source_path=?",
                (str(e), source_path_str),
            )

        done += 1
        if done % COMMIT_EVERY == 0:
            conn.commit()
            elapsed = time.time() - start
            rate = done / elapsed if elapsed > 0 else 0
            remaining = total - done
            eta_s = remaining / rate if rate > 0 else float("inf")
            print(f"{done}/{total} ({rate:.1f} files/s, ETA {eta_s / 60:.1f} min)")

    conn.commit()
    print(f"Done: {done}/{total} processed this run.")


def summary(db_path: Path):
    conn = connect(db_path)
    print("By status:")
    for status, cnt in conn.execute(
        "SELECT status, COUNT(*) AS cnt FROM files GROUP BY status ORDER BY cnt DESC"
    ):
        print(f"  {status:12s} {cnt}")
    print("By category (processed only):")
    for category, cnt in conn.execute(
        "SELECT category, COUNT(*) AS cnt FROM files WHERE status='processed' GROUP BY category ORDER BY cnt DESC"
    ):
        print(f"  {category:12s} {cnt}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--source", action="append", dest="sources", type=Path, default=[])
    p.add_argument("--output", type=Path)
    p.add_argument("--db", type=Path, required=True)
    p.add_argument("--summary", action="store_true", help="print ledger counts and exit")
    args = p.parse_args()

    if args.summary:
        summary(args.db)
        return

    if not args.sources or not args.output:
        p.error("--source (one or more) and --output are required unless --summary is given")

    run(args.sources, args.output, args.db)
    summary(args.db)


if __name__ == "__main__":
    sys.exit(main())
