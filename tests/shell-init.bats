#!/usr/bin/env bats
# config/shell-init.sh : PATH, puis tma seulement dans un terminal interactif hors tmux.
# ~/.bashrc et ~/.zshrc de test sourcent l'init comme la ligne d'install.sh ; `script` donne un
# vrai tty ; tma et tmux sont des stubs. Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
INIT="$BATS_TEST_DIRNAME/../config/shell-init.sh"

setup() {
  export HOME="$BATS_TEST_TMPDIR/home" MARK="$BATS_TEST_TMPDIR/tma-ran"
  mkdir -p "$HOME/.local/bin" "$BATS_TEST_TMPDIR/bin"
  printf '#!/bin/sh\ntouch "$MARK"\n' > "$HOME/.local/bin/tma"
  printf '#!/bin/sh\nexit 0\n' > "$BATS_TEST_TMPDIR/bin/tmux"
  chmod +x "$HOME/.local/bin/tma" "$BATS_TEST_TMPDIR/bin/tmux"
  printf '. "%s"\n' "$INIT" | tee "$HOME/.bashrc" > "$HOME/.zshrc"
  export PATH="$BATS_TEST_TMPDIR/bin:/usr/bin:/bin"
  # Les tests eux-mêmes tournent parfois sous tmux, VS Code ou Claude Code
  unset TMUX AIF_NO_TMUX CLAUDECODE TERM_PROGRAM ZDOTDIR
  command -v script >/dev/null || skip "script (util-linux) missing"
}

# term <shell> : nouveau terminal (shell interactif avec un tty, qui lit son rc puis sort)
term() {
  case $1 in
    bash) script -qec "bash -i" /dev/null ;;
    zsh) script -qec "zsh -i" /dev/null ;;
  esac <<<"exit" >/dev/null
}

@test "a new bash terminal outside tmux runs tma" {
  term bash
  [ -f "$MARK" ]
}

@test "a new zsh terminal outside tmux runs tma" {
  command -v zsh >/dev/null || skip "zsh missing"
  term zsh
  [ -f "$MARK" ]
}

@test "no tma inside tmux, VS Code / Cursor, Claude Code, or with AIF_NO_TMUX=1" {
  TMUX=/tmp/x,1,0 term bash
  TERM_PROGRAM=vscode term bash
  CLAUDECODE=1 term bash
  AIF_NO_TMUX=1 term bash
  [ ! -f "$MARK" ]
}

@test "no tma when the shell runs a command (zsh -lic tma already runs it)" {
  script -qec "bash -i -c true" /dev/null >/dev/null
  if command -v zsh >/dev/null; then script -qec "zsh -i -c true" /dev/null >/dev/null; fi
  [ ! -f "$MARK" ]
}

@test "no tma in a non-interactive shell or without a tty" {
  bash -c ". '$INIT'"
  bash -i </dev/null >/dev/null 2>&1
  [ ! -f "$MARK" ]
}

@test "~/.local/bin is added to PATH once" {
  run -0 bash --norc -c ". '$INIT'; . '$INIT'; printf '%s\n' \"\$PATH\""
  [ "$output" = "$HOME/.local/bin:$PATH" ]
}
