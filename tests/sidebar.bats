#!/usr/bin/env bats
# aif-sidebar de bout en bout sur un serveur tmux dédié (-L aif-test) : rendu de l'onglet AGENTS,
# réponse envoyée au pane de l'agent (send-keys), aperçu. Le faux agent est un script nommé
# « claude » qui enregistre les touches reçues (terminal en mode raw).
# Binaire : AIF_SIDEBAR_BIN, sinon le plus récent de sidebar/target/{release,debug} ; test sauté sans binaire.
# Lancer : (cd sidebar && cargo build) && npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
REPO="$BATS_TEST_DIRNAME/.."

setup() {
  # Le binaire le plus récent (release par install.sh, debug par cargo build)
  BIN=${AIF_SIDEBAR_BIN:-$(ls -t "$REPO"/sidebar/target/{release,debug}/aif-sidebar 2>/dev/null | head -1)}
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

teardown() { tmux -L aif-test kill-server 2>/dev/null || true; }   # -L explicite : setup a pu sauter (skip) avant le wrapper

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

# permission : réécrit l'état de l'agent en demande de permission (options Yes / Always / No)
as_permission() {
  jq '.question = "Bash: touch /tmp/x" | .options = ["Yes", "Always", "No"]' "$AIF_STATE_DIR/${AGENT#%}.json" > "$AIF_STATE_DIR/t"
  mv "$AIF_STATE_DIR/t" "$AIF_STATE_DIR/${AGENT#%}.json"
}

@test "permission: 3 (No) sends Escape, never the digit (option 3 may switch to auto mode)" {
  as_permission
  SB=$(tmux split-window -d -P -F '#{pane_id}' -h -l 60 -t prosper aif-sidebar)
  screen "$SB" "[3 No]"
  tmux send-keys -t "$SB" 3
  keys_received "$(printf '\033')"
  screen "$SB" "you answered: No"
}

@test "permission: a free reply refuses with Escape, then sends the text as a prompt" {
  as_permission
  SB=$(tmux split-window -d -P -F '#{pane_id}' -h -l 60 -t prosper aif-sidebar)
  screen "$SB" "Bash: touch /tmp/x"
  tmux send-keys -t "$SB" i
  screen "$SB" "›"
  tmux send-keys -t "$SB" -l "not now"
  tmux send-keys -t "$SB" Enter
  keys_received "$(printf '\033not now\r')"
}

@test "help view: four sections and the glyph legend; Esc closes it" {
  HP=$(tmux split-window -d -P -F '#{pane_id}' -h -l 100 -t prosper "aif-sidebar help")
  screen "$HP" "NAVIGATE"
  screen "$HP" "PANES & VIEW"
  screen "$HP" "◉ to check"
  tmux send-keys -t "$HP" Escape
  for _ in $(seq 1 25); do tmux list-panes -a -F '#{pane_id}' | grep -qx "$HP" || break; sleep 0.2; done
  ! tmux list-panes -a -F '#{pane_id}' | grep -qx "$HP"
}
