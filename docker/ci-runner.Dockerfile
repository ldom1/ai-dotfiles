# Slim runner for bin/local-ci. Versions come from docker/ci-runner.manifest; build with scripts/build-ci-runner.sh.
FROM ubuntu:24.04
ARG NODE_VERSION
ARG GIT_VERSION
ARG GIT_LFS_VERSION
ARG GH_VERSION
ARG JQ_VERSION
ENV DEBIAN_FRONTEND=noninteractive
# python3 and shellcheck are the noble packages, as on GitHub's image. Apt lists stay: GitHub keeps them, and
# workflows run `sudo apt-get install` without `apt-get update`.
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl sudo build-essential xz-utils jq python3 shellcheck \
      libcurl4-openssl-dev libssl-dev zlib1g-dev libexpat1-dev gettext
# Git: exact version from source; the git-core PPA only ships the latest.
RUN curl -fsSL "https://mirrors.edge.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.xz" | tar -xJ -C /tmp \
 && make -C "/tmp/git-${GIT_VERSION}" -j"$(nproc)" prefix=/usr/local NO_TCLTK=1 NO_RUST=1 all install >/dev/null \
 && rm -rf "/tmp/git-${GIT_VERSION}"
RUN curl -fsSL "https://github.com/git-lfs/git-lfs/releases/download/v${GIT_LFS_VERSION}/git-lfs-linux-amd64-v${GIT_LFS_VERSION}.tar.gz" | tar -xz -C /tmp \
 && install "/tmp/git-lfs-${GIT_LFS_VERSION}/git-lfs" /usr/local/bin/git-lfs && rm -rf "/tmp/git-lfs-${GIT_LFS_VERSION}"
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" | tar -xJ -C /usr/local --strip-components=1
# gh from the tarball: its .deb depends on the apt `git`, and a forced install breaks every later `apt-get install`.
RUN curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.tar.gz" | tar -xz -C /tmp \
 && install "/tmp/gh_${GH_VERSION}_linux_amd64/bin/gh" /usr/local/bin/gh && rm -rf "/tmp/gh_${GH_VERSION}_linux_amd64"
# GitHub runs jobs as `runner` (uid 1001) with passwordless sudo.
RUN userdel -r ubuntu 2>/dev/null || true \
 && useradd -m -u 1001 -s /bin/bash runner \
 && echo 'runner ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runner \
 && mkdir -p /home/runner/.cache/uv /home/runner/.npm && chown -R runner:runner /home/runner
# Tool cache of setup-* actions, writable by runner as on GitHub. act mounts the `act-toolcache` volume here and sets
# RUNNER_TOOL_CACHE; an empty volume takes this directory's owner. AGENT_TOOLSDIRECTORY is set by GitHub's image only.
RUN mkdir -p /opt/hostedtoolcache && chown runner:runner /opt/hostedtoolcache
ENV AGENT_TOOLSDIRECTORY=/opt/hostedtoolcache
USER runner
WORKDIR /home/runner
