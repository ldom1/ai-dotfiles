#!/usr/bin/env bats
# config/shell-init.sh : met ~/.local/bin dans le PATH, rien d'autre (plus de tmux : Orca est le
# cockpit). install.sh le fait sourcer par ~/.zshenv (shells de connexion non interactifs d'Orca),
# ~/.zshrc et ~/.bashrc. Lancer : npx --yes bats@1.13.0 tests/

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
  unset TMUX AIF_DECK HERDR_ENV CLAUDECODE TERM_PROGRAM ZDOTDIR
  command -v script >/dev/null || skip "script (util-linux) missing"
}

@test "an interactive terminal outside tmux does not run tma" {
  script -qec "bash -i" /dev/null <<<"exit" >/dev/null
  if command -v zsh >/dev/null; then script -qec "zsh -i" /dev/null <<<"exit" >/dev/null; fi
  [ ! -f "$MARK" ]
}

@test "~/.local/bin is added to PATH once" {
  run -0 bash --norc -c ". '$INIT'; . '$INIT'; printf '%s\n' \"\$PATH\""
  [ "$output" = "$HOME/.local/bin:$PATH" ]
}

@test "a non-interactive login zsh gets ~/.local/bin from ~/.zshenv" {
  command -v zsh >/dev/null || skip "zsh missing"
  printf '. "%s"\n' "$INIT" > "$HOME/.zshenv"
  run -0 env -i HOME="$HOME" PATH=/usr/bin:/bin zsh -lc 'printf "%s\n" "$PATH"'
  [[ "$output" == "$HOME/.local/bin:"* ]]
}
