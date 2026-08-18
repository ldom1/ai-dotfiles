#!/usr/bin/env python3
"""
photo-archive-triage: apply recovered dates to an already-uploaded destination
library, and quarantine anything with no recoverable date at all.

This is the implementation of the "B. Patch the destination system after
upload" path described in reference/date-trust-order.md, built against
Immich's real API (verified live — see reference/destination-patch-immich.md
for the exact endpoints and a critical SSO/reverse-proxy gotcha you should
read before running this against a self-hosted instance).

Two things it does, from a --emit-patch-csv produced by recover_dates.py:

1. For rows with a recovered_date: match the source file to its uploaded
   asset by original filename, then bulk-PATCH the destination's date field.
2. For rows with NO recovered date (source_field == "none (mtime unchanged)"):
   match + file them into a clearly-named quarantine album with a date you
   provide explicitly. This script never invents a placeholder date — pass
   --placeholder-date, sourced from asking the user, not guessed.

Only Immich is implemented as a concrete --backend. Adapt build_immich_api()
for another system; the matching/batching logic above it is backend-agnostic.

Usage:

    uv run python3 apply_destination_patch.py \
        --csv recovered_dates.csv \
        --backend immich --immich-auth-file ~/.config/immich/auth.yml \
        --quarantine-album "Undated / Recovered" \
        --placeholder-date 1994-11-16

Requires only stdlib (urllib) so it runs anywhere `uv run python3` does,
without needing the destination's own SDK installed.
"""
import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BATCH_SIZE = 500


def load_immich_auth(auth_file: Path) -> tuple[str, str]:
    url = key = None
    with open(auth_file) as f:
        for line in f:
            k, _, v = line.strip().partition(":")
            v = v.strip()
            if k == "url":
                url = v
            elif k == "key":
                key = v
    if not url or not key:
        print(f"Could not parse url/key out of {auth_file} — expected the plain "
              f"'url: ...\\nkey: ...' format immich-cli's `login-key` writes.", file=sys.stderr)
        sys.exit(1)
    return url.rstrip("/"), key


def build_immich_api(auth_file: Path):
    """Returns (find_asset_id_by_name, bulk_set_date, ensure_album, bulk_add_to_album)."""
    base_url, key = load_immich_auth(auth_file)

    def call(method, path, body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(f"{base_url}{path}", data=data, method=method)
        req.add_header("x-api-key", key)
        req.add_header("Content-Type", "application/json")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    raw = resp.read()
                    return json.loads(raw) if raw else None
            except (urllib.error.HTTPError, urllib.error.URLError):
                if attempt == 2:
                    raise
                time.sleep(2)

    def find_asset_id_by_name(original_name: str) -> str | None:
        result = call("POST", "/search/metadata", {"originalFileName": original_name})
        items = result.get("assets", {}).get("items", [])
        return items[0]["id"] if items else None

    def bulk_set_date(asset_ids: list[str], iso_date: str):
        for i in range(0, len(asset_ids), BATCH_SIZE):
            batch = asset_ids[i:i + BATCH_SIZE]
            call("PUT", "/assets", {"ids": batch, "dateTimeOriginal": iso_date})

    def ensure_album(name: str) -> str:
        created = call("POST", "/albums", {"albumName": name})
        return created["id"]

    def bulk_add_to_album(album_id: str, asset_ids: list[str]):
        for i in range(0, len(asset_ids), BATCH_SIZE):
            batch = asset_ids[i:i + BATCH_SIZE]
            call("PUT", f"/albums/{album_id}/assets", {"ids": batch})

    return find_asset_id_by_name, bulk_set_date, ensure_album, bulk_add_to_album


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--csv", type=Path, required=True, help="output of recover_dates.py --emit-patch-csv")
    p.add_argument("--backend", choices=["immich"], required=True)
    p.add_argument("--immich-auth-file", type=Path, default=Path.home() / ".config/immich/auth.yml")
    p.add_argument("--quarantine-album", default="Undated / Recovered",
                    help="album name for rows with no recoverable date")
    p.add_argument("--placeholder-date", required=True,
                    help="ISO date (YYYY-MM-DD) to apply to undated assets — must come from the "
                         "user, never invented by this script or by whoever is running it")
    args = p.parse_args()

    if args.backend == "immich":
        find_asset_id_by_name, bulk_set_date, ensure_album, bulk_add_to_album = build_immich_api(args.immich_auth_file)

    with open(args.csv, newline="") as f:
        rows = list(csv.DictReader(f))

    dated_rows = [r for r in rows if r["recovered_date"]]
    undated_rows = [r for r in rows if not r["recovered_date"]]
    print(f"{len(dated_rows)} row(s) have a recovered date, {len(undated_rows)} have none")

    def match_all(rows):
        matched, not_found = [], []
        for i, row in enumerate(rows, 1):
            asset_id = find_asset_id_by_name(row["original_name"])
            (matched if asset_id else not_found).append((row, asset_id))
            if i % 200 == 0:
                print(f"  matched {i}/{len(rows)}...", flush=True)
        return matched, not_found

    if dated_rows:
        print("Matching dated rows to uploaded assets...")
        matched, not_found = match_all(dated_rows)
        by_date: dict[str, list[str]] = {}
        for row, asset_id in matched:
            by_date.setdefault(row["recovered_date"], []).append(asset_id)
        for iso_date, asset_ids in by_date.items():
            bulk_set_date(asset_ids, iso_date)
        print(f"  patched {len(matched)} asset(s) across {len(by_date)} distinct date(s); "
              f"{len(not_found)} not found on the destination (not uploaded yet?)")

    if undated_rows:
        print(f"Matching undated rows, quarantining into '{args.quarantine_album}' "
              f"@ {args.placeholder_date}...")
        matched, not_found = match_all(undated_rows)
        asset_ids = [asset_id for _, asset_id in matched]
        if asset_ids:
            placeholder_iso = f"{args.placeholder_date}T00:00:00.000Z"
            album_id = ensure_album(args.quarantine_album)
            bulk_set_date(asset_ids, placeholder_iso)
            bulk_add_to_album(album_id, asset_ids)
            print(f"  quarantined {len(asset_ids)} asset(s) into album {album_id}; "
                  f"{len(not_found)} not found on the destination")
        else:
            print("  nothing matched — nothing to quarantine")

    print("Done. Files never touched — this script only calls the destination's API.")


if __name__ == "__main__":
    main()
