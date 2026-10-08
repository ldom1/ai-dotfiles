#!/usr/bin/env bash
# Build local-ci-runner:24.04 from docker/ci-runner.manifest, then check every tool version in the image.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck source=/dev/null
source "$ROOT/docker/ci-runner.manifest"
IMAGE=local-ci-runner:24.04
docker build -t "$IMAGE" -f "$ROOT/docker/ci-runner.Dockerfile" \
  --build-arg NODE_VERSION="$NODE_VERSION" --build-arg GIT_VERSION="$GIT_VERSION" \
  --build-arg GIT_LFS_VERSION="$GIT_LFS_VERSION" --build-arg GH_VERSION="$GH_VERSION" \
  --build-arg JQ_VERSION="$JQ_VERSION" "$ROOT/docker"
check() { # check <label> <expected substring> <command...>
  local label=$1 want=$2; shift 2
  local got; got=$(docker run --rm "$IMAGE" "$@" 2>&1 | head -1)
  [[ "$got" == *"$want"* ]] || { echo "build-ci-runner: $label is '$got', manifest says '$want'" >&2; exit 1; }
  echo "ok $label $got"
}
check node "v$NODE_VERSION" node --version
check git "git version $GIT_VERSION" git --version
check git-lfs "git-lfs/$GIT_LFS_VERSION" git lfs version
check gh "gh version $GH_VERSION" gh --version
check jq "jq-$JQ_VERSION" jq --version
check uid 1001 id -u
check user runner id -un
check sudo ok sh -c 'sudo -n true && echo ok'
echo "image $(docker image inspect -f '{{.Id}}' "$IMAGE")"
