#!/usr/bin/env bats
# bin/aif-agent-hook : rejoue des événements de hooks Claude Code (tests/fixtures/hooks/, formes
# de https://code.claude.com/docs/en/hooks) et vérifie l'état écrit. tmux et aif-platform sont
# remplacés par des stubs : aucune notification réelle.
# Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."
HOOK="$REPO/bin/aif-agent-hook"
FIX="$BATS_TEST_DIRNAME/fixtures/hooks"

setup() {
  export AIF_STATE_DIR="$BATS_TEST_TMPDIR/agents" TMUX_PANE=%42 NOTIFY_LOG="$BATS_TEST_TMPDIR/notify.log"
  STATE="$AIF_STATE_DIR/42.json"
  mkdir -p "$BATS_TEST_TMPDIR/bin"
  # tmux : pane visible si AIF_TEST_VISIBLE=1, session « proj »
  cat > "$BATS_TEST_TMPDIR/bin/tmux" <<'SH'
#!/bin/sh
case "$*" in
  *session_attached*) echo "${AIF_TEST_VISIBLE:-0}" ;;
  *session_name*) echo proj ;;
esac
SH
  printf '#!/bin/sh\nprintf "%%s|" "$@" >> "$NOTIFY_LOG"; echo >> "$NOTIFY_LOG"\n' > "$BATS_TEST_TMPDIR/bin/aif-platform"
  chmod +x "$BATS_TEST_TMPDIR/bin/"*
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH"
}

# ev <fixture> : rejoue un événement ; le hook doit toujours sortir en 0 sans rien écrire
ev() {
  run --separate-stderr "$HOOK" < <(sed "s|@CWD@|$BATS_TEST_TMPDIR|" "$FIX/$1.json")
  [ "$status" -eq 0 ] && [ -z "$output" ]
}
st() { jq -r "$1" "$STATE"; }
notified() { sleep 0.2; [ -f "$NOTIFY_LOG" ] && wc -l < "$NOTIFY_LOG" || echo 0; }

@test "outside tmux: nothing written, exit 0" {
  unset TMUX_PANE
  ev session-start
  [ ! -e "$AIF_STATE_DIR" ]
}

@test "start, prompt, tool, stop: done → running → done" {
  ev session-start
  [ "$(st .state)" = done ] && [ "$(st .tool)" = claude ] && [ "$(st .pane)" = %42 ]
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

@test "AskUserQuestion: check with question and options, one notification, then running" {
  ev session-start; ev user-prompt; ev pre-tool-ask
  [ "$(st .state)" = check ]
  [ "$(st .question)" = "Which parser for BOAMP notices?" ]
  [ "$(st '.options | join(",")')" = "pdfplumber,PyMuPDF" ]
  [ "$(notified)" -eq 1 ]
  grep -qxF 'notify|◉ proj needs you|Which parser for BOAMP notices?|proj|critical|' "$NOTIFY_LOG"
  # Claude Code envoie aussi permission_prompt pour AskUserQuestion : la question reste
  ev notification-permission
  [ "$(st .question)" = "Which parser for BOAMP notices?" ] && [ "$(st '.options | join(",")')" = "pdfplumber,PyMuPDF" ]
  [ "$(notified)" -eq 1 ]
  ev post-tool
  [ "$(st .state)" = running ] && [ "$(st .question)" = null ]
}

@test "permission prompt: check with Yes / Always / No, notified once on entry" {
  ev session-start; ev user-prompt; ev pre-tool-bash
  ev notification-permission
  [ "$(st .state)" = check ]
  [ "$(st .question)" = "Bash: ls" ]
  [ "$(st '.options | join(",")')" = "Yes,Always,No" ]
  ev notification-permission
  [ "$(notified)" -eq 1 ]
}

@test "a failed tool after approval leaves check" {
  ev session-start; ev notification-permission; ev post-tool-failure
  [ "$(st .state)" = running ]
}

@test "visible pane: no notification" {
  export AIF_TEST_VISIBLE=1
  ev session-start; ev pre-tool-ask
  [ "$(st .state)" = check ] && [ "$(notified)" -eq 0 ]
}

@test "done notifies only with AIF_NOTIFY_DONE=1" {
  ev session-start; ev user-prompt; ev stop
  [ "$(notified)" -eq 0 ]
  export AIF_NOTIFY_DONE=1
  ev user-prompt; ev stop
  [ "$(notified)" -eq 1 ]
  grep -qxF 'notify|✓ proj finished|Parse the BOAMP notice PDFs|proj|' "$NOTIFY_LOG"
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

@test "aif-statusline records model and context, then runs the chained statusLine" {
  ev session-start
  in='{"model":{"id":"claude-opus-5-5","display_name":"Opus"},"context_window":{"used_percentage":61.4,"context_window_size":200000}}'
  run -0 "$REPO/bin/aif-statusline" sh -c 'echo "chained: $(jq -r .model.id)"' <<<"$in"
  [ "$output" = "chained: claude-opus-5-5" ]
  [ "$(st .model)" = Opus ] && [ "$(st .ctx)" = 61 ] && [ "$(st .state)" = done ]
}

@test "aif-statusline without a chained command prints model and context" {
  run -0 "$REPO/bin/aif-statusline" <<<'{"model":{"display_name":"Opus"},"context_window":{"remaining_percentage":20}}'
  [ "$output" = "Opus · ctx 80%" ]
}
