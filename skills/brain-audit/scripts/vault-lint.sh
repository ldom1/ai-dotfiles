#!/bin/bash
# brain-audit:lint — vault link health through the Obsidian CLI (read-only: `unresolved`, `orphans`, `file`).
# Reads BRAIN_PATH, OBSIDIAN_CLI (explicit CLI path; no fallback when set), SKILLS_ROOT (default: repo skills/).
# Prints: unresolved N, orphans N, top 10 unresolved targets, missing skill paths.
# Exit 0: report printed, or "skipped:" (no CLI binary on this machine).
# Exit 1: "error:" (the CLI exists but failed, or answered with garbage).
# The skill-path check needs no CLI and always runs. Needs Obsidian open: the CLI launches it otherwise.

set -uo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ -z "${BRAIN_PATH:-}" ]]; then
    # shellcheck source=_brain_env.sh
    source "$script_dir/_brain_env.sh"
fi
vault="$(basename "$BRAIN_PATH")"
skills_root="$(cd "${SKILLS_ROOT:-$script_dir/../..}" && pwd)"
errf="$(mktemp)"
trap 'rm -f "$errf"' EXIT

find_cli() {
    if [[ -n "${OBSIDIAN_CLI:-}" ]]; then
        tried="$OBSIDIAN_CLI"
        [[ -x "$OBSIDIAN_CLI" ]] && cli="$OBSIDIAN_CLI"
        return
    fi
    tried="obsidian on PATH, /mnt/c/Users/*/AppData/Local/Programs/Obsidian/Obsidian.com"
    cli="$(command -v obsidian || true)"
    if [[ -z "$cli" ]]; then
        cli="$(ls /mnt/c/Users/*/AppData/Local/Programs/Obsidian/Obsidian.com 2>/dev/null | head -n 1 || true)"
    fi
}

# call <cli args...>: stdout in $out; on failure sets $rc and prints the error.
call() {
    out="$("$cli" "vault=$vault" "$@" 2>"$errf")"
    rc=$?
    if ((rc != 0)); then
        fail "Obsidian CLI failed (exit $rc): $(head -n 1 "$errf")"
    fi
    return "$rc"
}

fail() {
    echo "error: $1" >&2
    return 1
}

stale_warning() {
    local newest rel disk_ms modified
    newest="$(find "$BRAIN_PATH" \( -name .obsidian -o -name .git \) -prune -o -name '*.md' -printf '%T@ %P\n' | sort -rn | head -n 1)"
    [[ -n "$newest" ]] || return 0
    rel="${newest#* }"
    disk_ms="$(awk -v t="${newest%% *}" 'BEGIN { printf "%d", t * 1000 }')"
    modified=""
    if "$cli" "vault=$vault" file "path=$rel" >"$errf.out" 2>/dev/null; then
        modified="$(awk '$1 == "modified" { print $2 }' "$errf.out")"
    fi
    rm -f "$errf.out"
    if [[ ! "$modified" =~ ^[0-9]+$ ]] || ((disk_ms > modified + 2000)); then
        echo "warning: Obsidian link cache is stale ($rel changed since Obsidian indexed it); restart Obsidian for exact counts"
    fi
}

lint_cli() {
    local total unresolved_json top n_orphans
    cli="" tried=""
    find_cli
    if [[ -z "$cli" ]]; then
        echo "skipped: Obsidian CLI not found ($tried)"
        return 0
    fi
    call unresolved total || return 1
    total="$(tr -d '[:space:]' <<<"$out")"
    [[ "$total" =~ ^[0-9]+$ ]] || { fail "Obsidian CLI returned a non-number for 'unresolved total': ${out:0:80}"; return 1; }
    call unresolved format=json || return 1
    unresolved_json="$out"
    top="$(jq -r 'sort_by(-(.count | tonumber)) | .[:10][]
        | "  \(.link) (\(.count)): \(.sources | if type == "array" then join(", ") else tostring end)"' <<<"$unresolved_json" 2>&1)" \
        || { fail "Obsidian CLI returned invalid JSON for 'unresolved format=json'"; return 1; }
    call orphans || return 1
    n_orphans="$(grep -v -E '^(inbox/daily/|projects/[^/]+/)' <<<"$out" | grep -c . || true)"

    stale_warning
    echo "unresolved: $total"
    echo "orphans (outside inbox/daily, projects/*/): $n_orphans"
    [[ -z "$top" ]] || printf '%s\n' "$top"
}

missing_skill_paths() {
    local base missing="" f line match p
    base="$(cd "$skills_root/.." && pwd)"
    while IFS=: read -r f line match; do
        p="${match//\`/}"
        [[ "$p" == *[\<\*\{\}]* ]] && continue
        [[ -e "$BRAIN_PATH/${p#\$BRAIN_PATH/}" ]] && continue
        missing+="${f#"$base"/}:$line $p"$'\n'
    done < <(grep -H -n -o '`\$BRAIN_PATH/[^`]*`' "$skills_root"/*/SKILL.md 2>/dev/null)
    echo "missing skill paths: $(grep -c . <<<"$missing" || true)"
    [[ -z "$missing" ]] || printf '%s' "$missing"
}

lint_cli
status=$?
missing_skill_paths
exit "$status"
