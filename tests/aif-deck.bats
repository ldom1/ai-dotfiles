#!/usr/bin/env bats
# bin/aif-deck : retire et remet les touches tma de Windows Terminal. Travaille sur une copie de
# tests/fixtures/wt-settings.json (forme du vrai fichier du 09/11/2026) ; jamais sur le vrai.
# Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
DECK="$BATS_TEST_DIRNAME/../bin/aif-deck"
FIX="$BATS_TEST_DIRNAME/fixtures/wt-settings.json"

setup() {
  export AIF_WT_SETTINGS="$BATS_TEST_TMPDIR/settings.json" XDG_CONFIG_HOME="$BATS_TEST_TMPDIR/config"
  BACKUP="$XDG_CONFIG_HOME/aif/wt-keys.json"
  cp "$FIX" "$AIF_WT_SETTINGS"
}

kb() { jq -S '.keybindings' "$AIF_WT_SETTINGS"; }
ids() { jq -r '[.keybindings[].id] | sort | join(" ")' "$AIF_WT_SETTINGS"; }
tma_keys() { jq '[.keybindings[] | select(.id | startswith("User.tmux"))] | length' "$AIF_WT_SETTINGS"; }

@test "off removes the 6 tma keybindings and keeps ctrl+c and ctrl+v" {
  run -0 "$DECK" off
  [ "$(ids)" = "User.copy.644BA8F2 User.paste" ]
}

@test "off keeps the actions unchanged" {
  "$DECK" off
  [ "$(jq -S .actions "$AIF_WT_SETTINGS")" = "$(jq -S .actions "$FIX")" ]
}

@test "off, off, on restores the keybindings exactly and deletes the backup" {
  "$DECK" off
  run -0 "$DECK" off
  [[ $output == *"already off"* ]]
  run -0 "$DECK" on
  [ "$(kb)" = "$(jq -S .keybindings "$FIX")" ]
  [ ! -e "$BACKUP" ]
}

@test "second off leaves the backup byte-identical" {
  "$DECK" off
  cp "$BACKUP" "$BATS_TEST_TMPDIR/b1"
  "$DECK" off
  cmp "$BACKUP" "$BATS_TEST_TMPDIR/b1"
}

@test "interrupted off (backup present, keys still present): off rewrites the backup, on restores exactly" {
  mkdir -p "$(dirname "$BACKUP")"
  echo '[{"id": "User.stale", "keys": "ctrl+shift+q"}]' > "$BACKUP"
  "$DECK" off
  [ "$(tma_keys)" = 0 ]
  "$DECK" on
  [ "$(kb)" = "$(jq -S .keybindings "$FIX")" ]
}

@test "on with a conflict: exit 3, file and backup unchanged" {
  "$DECK" off
  jq '.keybindings += [{"id": "User.find", "keys": "ctrl+shift+o"}]' "$AIF_WT_SETTINGS" > "$BATS_TEST_TMPDIR/s" && mv "$BATS_TEST_TMPDIR/s" "$AIF_WT_SETTINGS"
  cp "$AIF_WT_SETTINGS" "$BATS_TEST_TMPDIR/before"; cp "$BACKUP" "$BATS_TEST_TMPDIR/b1"
  run -3 "$DECK" on
  [[ $output == *"ctrl+shift+o"* ]]
  cmp "$AIF_WT_SETTINGS" "$BATS_TEST_TMPDIR/before"
  cmp "$BACKUP" "$BATS_TEST_TMPDIR/b1"
}

@test "on after an unrelated change restores the 6 keys and keeps the new one" {
  "$DECK" off
  jq '.keybindings += [{"id": "User.find", "keys": "ctrl+shift+q"}]' "$AIF_WT_SETTINGS" > "$BATS_TEST_TMPDIR/s" && mv "$BATS_TEST_TMPDIR/s" "$AIF_WT_SETTINGS"
  run -0 "$DECK" on
  [ "$(tma_keys)" = 6 ]
  [ "$(jq '[.keybindings[] | select(.keys == "ctrl+shift+q")] | length' "$AIF_WT_SETTINGS")" = 1 ]
}

@test "on without backup: exit 1 nothing to restore, or exit 0 already on" {
  "$DECK" off
  rm "$BACKUP"
  run -1 "$DECK" on
  [[ $output == *"nothing to restore"* ]]
  cp "$FIX" "$AIF_WT_SETTINGS"
  run -0 "$DECK" on
  [[ $output == *"already on"* ]]
}

@test "status prints on, then off with backup present" {
  run -0 "$DECK" status
  [ "$output" = on ]
  "$DECK" off
  run -0 "$DECK" status
  [ "$output" = "off (backup present)" ]
}

@test "invalid JSON: exit 2, file byte-identical, no backup" {
  printf '//x\n' >> "$AIF_WT_SETTINGS"
  cp "$AIF_WT_SETTINGS" "$BATS_TEST_TMPDIR/before"
  run -2 "$DECK" off
  cmp "$AIF_WT_SETTINGS" "$BATS_TEST_TMPDIR/before"
  [ ! -e "$BACKUP" ]
}

@test "no settings file: exit 1" {
  rm "$AIF_WT_SETTINGS"
  run -1 "$DECK" status
}
