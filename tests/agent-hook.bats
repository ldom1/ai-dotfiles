#!/usr/bin/env bats
# bin/aif-agent-hook : rejoue des événements de hooks Claude Code (tests/fixtures/hooks/, formes
# de https://code.claude.com/docs/en/hooks) dans un terminal Orca (ORCA_PANE_KEY) et vérifie l'état
# écrit et le journal aif-check.log. tmux et aif-platform sont des stubs qui journalisent : le hook
# ne doit jamais les appeler.
# Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."
HOOK="$REPO/bin/aif-agent-hook"
FIX="$BATS_TEST_DIRNAME/fixtures/hooks"

setup() {
  unset TMUX_PANE HERDR_ENV HERDR_PANE_ID
  export AIF_STATE_DIR="$BATS_TEST_TMPDIR/agents" ORCA_PANE_KEY=8984e803-6068:01d9dade-e26c
  export AIF_CHECK_LOG="$BATS_TEST_TMPDIR/check.log" CALLS="$BATS_TEST_TMPDIR/calls.log"
  STATE="$AIF_STATE_DIR/orca-8984e803-6068-01d9dade-e26c.json"
  mkdir -p "$BATS_TEST_TMPDIR/bin"
  for c in tmux aif-platform herdr; do
    printf '#!/bin/sh\necho "%s $*" >> "$CALLS"\n' "$c" > "$BATS_TEST_TMPDIR/bin/$c"
  done
  chmod +x "$BATS_TEST_TMPDIR/bin/"*
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
}

# ev <fixture> : rejoue un événement ; le hook doit toujours sortir en 0 sans rien écrire
ev() {
  run --separate-stderr "$HOOK" < <(sed "s|@CWD@|$BATS_TEST_TMPDIR|" "$FIX/$1.json")
  [ "$status" -eq 0 ] && [ -z "$output" ]
}
st() { jq -r "$1" "$STATE"; }

@test "no Orca pane key: nothing written, exit 0" {
  unset ORCA_PANE_KEY
  ev session-start
  [ ! -e "$AIF_STATE_DIR" ]
}

@test "TMUX_PANE alone: nothing written" {
  unset ORCA_PANE_KEY
  export TMUX_PANE=%42
  ev session-start
  [ ! -e "$AIF_STATE_DIR" ]
}

@test "HERDR_ENV alone: nothing written" {
  unset ORCA_PANE_KEY
  export HERDR_ENV=1 HERDR_PANE_ID=w1:p3
  ev session-start
  [ ! -e "$AIF_STATE_DIR" ]
}

@test "Orca pane: no tmux, notification or Herdr call on any state change" {
  export TMUX_PANE=%42
  ev session-start; ev user-prompt; ev pre-tool-ask; ev post-tool; ev stop-question; ev session-end
  sleep 0.3
  [ ! -e "$CALLS" ]
}

@test "start, prompt, tool, stop: done → running → done" {
  ev session-start
  [ "$(st .state)" = done ] && [ "$(st .tool)" = claude ] && [ "$(st .pane)" = 8984e803-6068:01d9dade-e26c ]
  [ "$(st .cwd)" = "$BATS_TEST_TMPDIR" ] && [ "$(st .session_id)" = s1 ]
  ev user-prompt
  [ "$(st .state)" = running ] && [ "$(st .task)" = "Parse the BOAMP notice PDFs" ]
  [ "$(st .prompt_at)" -ge "$(st .started_at)" ]
  ev pre-tool-bash
  [ "$(st .state)" = running ] && [ "$(st .last_tool)" = Bash ]
  ev stop
  [ "$(st .state)" = done ] && [ "$(st .last_message)" = "Done: 3 parsers compared." ]
  [ "$(st .updated_at)" -ge "$(st .started_at)" ]
}

@test "AskUserQuestion: check with question and options, then running" {
  ev session-start; ev user-prompt; ev pre-tool-ask
  [ "$(st .state)" = check ]
  [ "$(st .question)" = "Which parser for BOAMP notices?" ]
  [ "$(st '.options | join(",")')" = "pdfplumber,PyMuPDF" ]
  # Claude Code envoie aussi permission_prompt pour AskUserQuestion : la question reste
  ev notification-permission
  [ "$(st .question)" = "Which parser for BOAMP notices?" ] && [ "$(st '.options | join(",")')" = "pdfplumber,PyMuPDF" ]
  ev post-tool
  [ "$(st .state)" = running ] && [ "$(st .question)" = null ]
}

@test "permission prompt: check with Yes / Always / No" {
  ev session-start; ev user-prompt; ev pre-tool-bash
  ev notification-permission
  [ "$(st .state)" = check ]
  [ "$(st .question)" = "Bash: ls" ]
  [ "$(st '.options | join(",")')" = "Yes,Always,No" ]
  ev notification-permission
}

@test "a failed tool after approval leaves check" {
  ev session-start; ev notification-permission; ev post-tool-failure
  [ "$(st .state)" = running ]
}

@test "subagents are tracked; a compaction keeps state and subagents" {
  ev session-start; ev user-prompt; ev subagent-start
  [ "$(st '.subagents.ag1.type')" = Explore ] && [ "$(st '.subagents.ag1.state')" = running ]
  ev session-start-compact
  [ "$(st .state)" = running ] && [ "$(st '.subagents.ag1.state')" = running ]
  ev subagent-stop
  [ "$(st '.subagents.ag1.state')" = done ]
}

@test "API failure: error with its type" {
  ev session-start; ev user-prompt; ev stop-failure
  [ "$(st .state)" = error ] && [ "$(st .error)" = rate_limit ]
}

@test "session end removes the state file" {
  ev session-start; ev session-end
  [ ! -e "$STATE" ]
}

@test "bad input and unknown events: exit 0, state unchanged" {
  ev session-start
  run "$HOOK" <<<'not json'
  [ "$status" -eq 0 ]
  run "$HOOK" <<<'{"hook_event_name":"FileChanged","cwd":"/x"}'
  [ "$status" -eq 0 ] && [ "$(st .state)" = done ] && [ "$(st .event)" = SessionStart ]
}

@test "tool input over 128 KB (argument size limit) still updates the state" {
  ev session-start
  head -c 300000 /dev/zero | tr '\0' a | jq -Rsc --arg cwd "$BATS_TEST_TMPDIR" \
    '{hook_event_name:"PreToolUse",cwd:$cwd,tool_name:"Write",tool_input:{content:.}}' > "$BATS_TEST_TMPDIR/big.json"
  run "$HOOK" < "$BATS_TEST_TMPDIR/big.json"
  [ "$status" -eq 0 ] && [ "$(st .last_tool)" = Write ]
}

@test "speed: a tool event takes under 100 ms" {
  ev session-start
  in=$(sed "s|@CWD@|$BATS_TEST_TMPDIR|" "$FIX/pre-tool-bash.json")
  # Meilleure de 3 séries de 10 : mesure le coût du hook, pas la charge de la machine
  best=999
  for _ in 1 2 3; do
    t0=$(date +%s%N)
    for _ in 1 2 3 4 5 6 7 8 9 10; do "$HOOK" <<<"$in"; done
    ms=$(( ($(date +%s%N) - t0) / 10000000 ))
    (( ms < best )) && best=$ms
  done
  echo "aif-agent-hook PreToolUse: ${best} ms per event (best of 3 x 10)" >&3
  [ "$best" -lt 100 ]
}

@test "Stop with a trailing question: check, prose" {
  ev session-start; ev user-prompt; ev stop-question
  [ "$(st .state)" = check ]
  [ "$(st .question)" = "Should I squash the branch?" ]
  [ "$(st .ask)" = prose ]
  [ "$(st '.options | length')" -eq 0 ]
  [ "$(st .last_message)" = $'Two options.\nShould I squash the branch?' ]
}

@test "Stop ending inside an unclosed fenced block, or on a URL ending in ?: done" {
  ev session-start; ev user-prompt; ev stop-fence-question
  [ "$(st .state)" = done ]
  [ "$(st .question)" = null ]
  ev user-prompt; ev stop-url-question
  [ "$(st .state)" = done ]
  [ "$(st .question)" = null ]
}

@test "Stop with a closed fenced block then a real question: check" {
  ev session-start; ev user-prompt; ev stop-fence-closed-question
  [ "$(st .state)" = check ]
  [ "$(st .question)" = "Should I run it?" ]
  [ "$(st .ask)" = prose ]
}

@test "prompt after a prose question: running" {
  ev session-start; ev user-prompt; ev stop-question
  ev user-prompt
  [ "$(st .state)" = running ]
  [ "$(st .question)" = null ]
}

@test "ask kind: tool for AskUserQuestion, permission for a permission prompt" {
  ev session-start; ev user-prompt; ev pre-tool-ask
  [ "$(st .ask)" = tool ]
  ev post-tool; ev pre-tool-bash; ev notification-permission
  [ "$(st .ask)" = permission ]
}

@test "check transitions are logged: enter then leave" {
  ev session-start; ev pre-tool-ask
  ev post-tool
  [ "$(wc -l < "$AIF_CHECK_LOG")" -eq 2 ]
  [ "$(sed -n 1p "$AIF_CHECK_LOG" | cut -f2-4)" = "$(printf 's1\tenter\ttool')" ]
  [ "$(sed -n 2p "$AIF_CHECK_LOG" | cut -f2-4)" = "$(printf 's1\tleave\ttool')" ]
  [[ "$(cut -f1 "$AIF_CHECK_LOG" | head -1)" =~ ^[0-9]+$ ]]
  ev stop
  [ "$(wc -l < "$AIF_CHECK_LOG")" -eq 2 ]
}

@test "check log: a prose question enters with ask prose, the next prompt leaves with it" {
  ev session-start; ev stop-question; ev user-prompt
  [ "$(cut -f3,4 "$AIF_CHECK_LOG" | paste -sd,)" = "$(printf 'enter\tprose,leave\tprose')" ]
}

@test "check log has the Orca key as 5th column" {
  ev session-start; ev user-prompt; ev stop-question
  [ "$(st .state)" = check ]
  [ "$(cut -f3-5 "$AIF_CHECK_LOG" | tail -1)" = "$(printf 'enter\tprose\torca-8984e803-6068-01d9dade-e26c')" ]
}
