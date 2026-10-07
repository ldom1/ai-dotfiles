#!/usr/bin/env bash
# Statusline line 4: skills invoked/available and MCP servers loaded/failed this session.
# Reads the transcript; skill_listing and deferred_tools_delta are undocumented Claude Code records (2.1.293).
t=$(jq -r '.transcript_path // empty')
[[ -r $t ]] || exit 0
G=$'\033[90m' C=$'\033[36m' R=$'\033[31m' N=$'\033[0m'

skills=$(grep -o '"name":"Skill","input":{"skill":"[^"]*"' "$t" | sed 's/.*"skill":"//; s/"$//')
n=0; [[ -n $skills ]] && n=$(wc -l <<<"$skills")
avail=$(grep '"type":"skill_listing"' "$t" | jq -rs '[.[].attachment.names[]?] | unique | length')
out="${G}skills used ${C}${n}${G}/${avail:-0}${N}"
(( n > 0 )) && out+="${G} last ${C}$(tail -1 <<<"$skills")${N}"

read -r loaded failed < <(grep '"type":"deferred_tools_delta"' "$t" | jq -rs '
  [.[].attachment] as $d
  | ([$d[] | (.addedNames, .readdedNames, .surfacedNames)[]?] - [$d[].removedNames[]?])
    | map(select(startswith("mcp__")) | split("__")[1]) | unique as $ok
  | [$d[].failedMcpServers[]?.name | gsub("[^A-Za-z0-9_-]"; "_")] | unique - $ok
  | "\($ok | length) \(join(","))"')
out+=" ${G}| mcp ${C}${loaded:-0}${N}"
[[ -n $failed ]] && out+=" ${R}✗ ${failed//,/, } failed${N}"
printf '%s\n' "$out"
