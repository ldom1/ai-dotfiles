#!/usr/bin/env bats
# bin/aif-platform : détection WSL / Linux natif (install.sh, orca-install.sh, wsl-claude-mount.sh).
# Lancer : npx --yes bats@1.13.0 tests/

bats_require_minimum_version 1.5.0
P="$BATS_TEST_DIRNAME/../bin/aif-platform"

@test "name: AIF_PLATFORM wins, otherwise WSL_DISTRO_NAME means wsl" {
  run -0 env AIF_PLATFORM=linux WSL_DISTRO_NAME=Ubuntu "$P" name
  [ "$output" = linux ]
  run -0 env -u AIF_PLATFORM WSL_DISTRO_NAME=Ubuntu "$P" name
  [ "$output" = wsl ]
}

@test "only name remains: the tmux-era commands are unknown (exit 2)" {
  for c in copy notify open wt-settings; do
    run -2 "$P" "$c" </dev/null
    [[ "$output" == "usage: aif-platform name" ]]
  done
}
