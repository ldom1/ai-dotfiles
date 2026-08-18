# Extension allowlist

PhotoRec (and data-recovery carving tools generally) recover *every* file
type they can identify from raw disk blocks — documents, executables,
archives, database files, font files, whatever was on the drive — mixed in
indiscriminately with the actual photos and videos. Applying an extension
allowlist as the very first filter, before any hashing or image-decoding
work, keeps the expensive per-file work (SHA-256 over a multi-GB video,
`Image.open().load()`) from ever running on files that were never going to
be photos or videos in the first place. Non-matching files are skipped
silently — they're not a triage outcome (not invalid, not duplicate, not
junk), so logging them would just be noise.

This same filter is applied even for non-PhotoRec sources (phone backups,
old export folders) — it's cheap, and stray `.DS_Store`/`.thumbdata`/sidecar
files show up in those too.

## Default allowlist used by `triage.py`

Images:
```
.jpg .jpeg .png .heic .heif .gif .bmp .tif .tiff .webp
.cr2 .cr3 .nef .arw .dng .orf .rw2 .raf   # common RAW formats
```

Videos:
```
.mp4 .mov .avi .mkv .m4v .3gp .3g2 .mts .m2ts .wmv .flv .webm
```

Adjust the list in `triage.py`'s `EXTENSION_ALLOWLIST` set to match what the
user actually cares about — e.g. drop RAW formats if the user says they
only shot JPEG, or add `.insv`/`.360` for action-camera formats. Ask rather
than guessing if the source is an unfamiliar device/camera and the default
list might be dropping real photos.

## Case sensitivity

PhotoRec and most cameras produce lowercase extensions, but recovered or
Windows-originated files can be mixed-case (`.JPG`, `.Mp4`). Always
lowercase the extension before checking membership in the allowlist.
