#!/usr/bin/env bats
# bin/aif-platform : détection, copie, notifications. notify-send, powershell.exe, wl-copy et tmux
# sont des stubs qui journalisent leurs arguments : aucune vraie notification pendant les tests.
# Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
P="$BATS_TEST_DIRNAME/../bin/aif-platform"

setup() {
  export LOG="$BATS_TEST_TMPDIR/log" STUBS="$BATS_TEST_TMPDIR/bin"
  mkdir -p "$LOG" "$STUBS"
  stub() { printf '#!/bin/sh\n%s\n' "$2" > "$STUBS/$1"; chmod +x "$STUBS/$1"; }
  stub notify-send 'printf "%s\n" "$@" > "$LOG/notify-send"; [ -n "${CLICK:-}" ] && echo open; exit 0'
  stub powershell.exe 'printf "%s\n" "$@" > "$LOG/powershell"'
  stub wl-copy 'cat > "$LOG/clip"'
  stub tmux 'printf "%s " "$@" >> "$LOG/tmux"; echo >> "$LOG/tmux"; case "$*" in *load-buffer*) cat > "$LOG/clip" ;; esac'
  export PATH="$STUBS:$PATH"
  # Aucun vrai bureau : sans DBUS_SESSION_BUS_ADDRESS, un vrai notify-send installé n'est jamais appelé
  unset WAYLAND_DISPLAY DISPLAY TMUX DBUS_SESSION_BUS_ADDRESS
}

# wait_file <fichier> : les notifications partent en arrière-plan
wait_file() { for _ in $(seq 1 25); do [ -s "$1" ] && return 0; sleep 0.1; done; return 1; }

@test "name: AIF_PLATFORM wins, otherwise WSL_DISTRO_NAME means wsl" {
  run -0 env AIF_PLATFORM=linux WSL_DISTRO_NAME=Ubuntu "$P" name
  [ "$output" = linux ]
  run -0 env -u AIF_PLATFORM WSL_DISTRO_NAME=Ubuntu "$P" name
  [ "$output" = wsl ]
}

@test "copy on native Linux under Wayland goes to wl-copy, accents intact" {
  printf 'héllo àccents' | AIF_PLATFORM=linux WAYLAND_DISPLAY=wayland-0 "$P" copy
  [ "$(cat "$LOG/clip")" = "héllo àccents" ]
}

@test "copy on WSL inside tmux goes through tmux load-buffer -w (OSC 52), accents intact" {
  printf 'héllo àccents' | AIF_PLATFORM=wsl TMUX=/tmp/x,1,0 "$P" copy
  [ "$(cat "$LOG/clip")" = "héllo àccents" ]
  grep -q 'load-buffer -w -' "$LOG/tmux"
}

@test "notify on Linux: critical notification with an Open button for the session" {
  run -0 env AIF_PLATFORM=linux DBUS_SESSION_BUS_ADDRESS=unix:x "$P" notify "◉ prosper needs you" "Which parser?" prosper critical
  wait_file "$LOG/notify-send"
  run cat "$LOG/notify-send"
  [[ "$output" == *"--action=open=Open prosper"* ]] && [[ "$output" == *"critical"* ]]
  [[ "$output" == *"◉ prosper needs you"* ]] && [[ "$output" == *"Which parser?"* ]]
}

@test "notify on Linux: clicking Open brings tmux to the session" {
  CLICK=1 AIF_PLATFORM=linux DBUS_SESSION_BUS_ADDRESS=unix:x "$P" notify "◉ prosper needs you" "q" prosper critical
  wait_file "$LOG/tmux"
  grep -q 'switch-client -t =prosper' "$LOG/tmux"
}

@test "notify on WSL: BurntToast toast with quoted title and body" {
  run -0 env AIF_PLATFORM=wsl "$P" notify "✓ prosper finished" "Parse the 'BOAMP' PDFs" prosper
  wait_file "$LOG/powershell"
  run cat "$LOG/powershell"
  [[ "$output" == *"New-BurntToastNotification -Text '✓ prosper finished', 'Parse the ''BOAMP'' PDFs'"* ]]
}

@test "notify without a desktop: message in the tmux status line" {
  rm "$STUBS/notify-send"
  run -0 env AIF_PLATFORM=linux "$P" notify "◉ prosper needs you" "q" prosper
  grep -q 'display-message -d 4000 ◉ prosper needs you — q' "$LOG/tmux"
}

@test "wt-settings: WSL path of the Windows Terminal settings; exit 1 on linux" {
  stub cmd.exe 'printf "C:\\\\Users\\\\Louis\\\\AppData\\\\Local\r\n"'
  stub wslpath 'echo /mnt/c/Users/Louis/AppData/Local'
  run -0 env AIF_PLATFORM=wsl "$P" wt-settings
  [ "$output" = /mnt/c/Users/Louis/AppData/Local/Packages/Microsoft.WindowsTerminal_8wekyb3d8bbwe/LocalState/settings.json ]
  run -1 env AIF_PLATFORM=linux "$P" wt-settings
}
