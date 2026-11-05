#!/usr/bin/env bats
# aif-sidebar de bout en bout sur un serveur tmux dédié (-L aif-test) : rendu de l'onglet AGENTS,
# réponse envoyée au pane de l'agent (send-keys), aperçu. Le faux agent est un script nommé
# « claude » qui enregistre les touches reçues (terminal en mode raw).
# Binaire : AIF_SIDEBAR_BIN, sinon sidebar/target/{release,debug}/aif-sidebar ; test sauté sans binaire.
# Lancer : (cd sidebar && cargo build) && npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."

setup() {
  BIN=${AIF_SIDEBAR_BIN:-}
  for b in "$REPO/sidebar/target/release/aif-sidebar" "$REPO/sidebar/target/debug/aif-sidebar"; do
    [ -n "$BIN" ] || { [ -x "$b" ] && BIN=$b; }
  done
  [ -n "$BIN" ] || skip "aif-sidebar not built"
  export AIF_STATE_DIR="$BATS_TEST_TMPDIR/agents" KEYLOG="$BATS_TEST_TMPDIR/keys"
  mkdir -p "$AIF_STATE_DIR" "$BATS_TEST_TMPDIR/bin"
  printf '#!/bin/sh\nexec %s -L aif-test "$@"\n' "$(command -v tmux)" > "$BATS_TEST_TMPDIR/bin/tmux"
  printf '#!/bin/sh\nstty raw -echo\necho waiting for keys\ncat > "$KEYLOG"\n' > "$BATS_TEST_TMPDIR/bin/claude"
  ln -s "$BIN" "$BATS_TEST_TMPDIR/bin/aif-sidebar"
  ln -s "$REPO/bin/aif-agents" "$BATS_TEST_TMPDIR/bin/aif-agents"
  chmod +x "$BATS_TEST_TMPDIR/bin/tmux" "$BATS_TEST_TMPDIR/bin/claude"
  export PATH="$BATS_TEST_TMPDIR/bin:$PATH" AIF_DOTFILES="$REPO"
  tmux -f /dev/null new-session -d -s prosper -x 200 -y 50 -c "$BATS_TEST_TMPDIR"
  AGENT=$(tmux split-window -d -P -F '#{pane_id}' -t prosper claude)
  jq -n --arg p "$AGENT" --arg cwd "$BATS_TEST_TMPDIR" --argjson t "$(date +%s)" '{pane: $p, state: "check", cwd: $cwd,
    task: "Parse the BOAMP notice PDFs", question: "Which parser for BOAMP notices?",
    options: ["pdfplumber", "PyMuPDF"], updated_at: $t, model: "Opus", ctx: 61}' > "$AIF_STATE_DIR/${AGENT#%}.json"
}

teardown() { tmux kill-server 2>/dev/null || true; }

# screen <pane> <texte> : attend (5 s max) que le pane affiche le texte
screen() {
  for _ in $(seq 1 25); do tmux capture-pane -p -t "$1" | grep -qF -- "$2" && return 0; sleep 0.2; done
  tmux capture-pane -p -t "$1" >&3; return 1
}
keys_received() { for _ in $(seq 1 25); do [ "$(cat "$KEYLOG" 2>/dev/null)" = "$1" ] && return 0; sleep 0.2; done; od -c "$KEYLOG" >&3; return 1; }

@test "agents tab shows the waiting agent with its answer buttons and the version" {
  SB=$(tmux split-window -d -P -F '#{pane_id}' -h -l 60 -t prosper aif-sidebar)
  screen "$SB" "TO CHECK 1"
  screen "$SB" "Which parser for BOAMP notices?"
  screen "$SB" "[1 pdfplumber] [2 PyMuPDF] [i Reply…]"
  screen "$SB" "$(git -C "$REPO" describe --tags --abbrev=0)"
}

@test "2 sends the second option to the agent pane" {
  SB=$(tmux split-window -d -P -F '#{pane_id}' -h -l 60 -t prosper aif-sidebar)
  screen "$SB" "[2 PyMuPDF]"
  tmux send-keys -t "$SB" 2
  keys_received 2
  screen "$SB" "sent: PyMuPDF"
  screen "$SB" "you answered: PyMuPDF"
}

@test "i opens a reply field; Enter sends the free-text option, the text and Enter" {
  SB=$(tmux split-window -d -P -F '#{pane_id}' -h -l 60 -t prosper aif-sidebar)
  screen "$SB" "[i Reply…]"
  tmux send-keys -t "$SB" i
  screen "$SB" "›"
  tmux send-keys -t "$SB" -l "use pypdf"
  tmux send-keys -t "$SB" Enter
  keys_received "$(printf '3use pypdf\r')"
}

@test "peek shows the agent output, model and context" {
  PK=$(tmux split-window -d -P -F '#{pane_id}' -h -l 70 -t prosper "aif-sidebar peek $AGENT")
  screen "$PK" "PEEK ◉ prosper"
  screen "$PK" "waiting for keys"
  screen "$PK" "Opus · ctx 61%"
  tmux send-keys -t "$PK" Tab
  screen "$PK" "no changes against HEAD"
}
