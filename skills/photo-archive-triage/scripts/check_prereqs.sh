#!/usr/bin/env bash
# Checks for the external tools photo-archive-triage needs, and reports
# exactly what to install if something is missing. Never installs anything
# itself — apt-get needs a real sudo prompt, and silently trying (or
# silently working around a missing tool) is worse than telling the human.
set -euo pipefail

missing=0

check() {
    local bin="$1" apt_pkg="$2" purpose="$3"
    if command -v "$bin" >/dev/null 2>&1; then
        echo "OK   $bin ($(command -v "$bin"))"
    else
        echo "MISS $bin — needed for: $purpose"
        echo "     install with: sudo apt-get update && sudo apt-get install -y $apt_pkg"
        missing=1
    fi
}

echo "Checking prerequisites for photo-archive-triage..."
echo

check uv       "curl -LsSf https://astral.sh/uv/install.sh | sh   (not an apt package)" \
               "running the Python scripts without relying on a system pip"
check exiftool libimage-exiftool-perl "true capture-date recovery (recover_dates.py)"
check ffprobe  ffmpeg                 "video validity checking (triage.py)"

echo
if [ "$missing" -eq 0 ]; then
    echo "All prerequisites present."
    exit 0
else
    echo "One or more prerequisites are missing. Install them (see above), then re-run."
    echo "Note: triage.py can still run image-only validation without ffprobe — it will"
    echo "leave video files 'pending' in the ledger and pick them up automatically on"
    echo "the next run once ffmpeg is installed."
    exit 1
fi
