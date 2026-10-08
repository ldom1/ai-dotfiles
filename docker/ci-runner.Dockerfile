# Slim runner for bin/local-ci. Versions come from docker/ci-runner.manifest; build with scripts/build-ci-runner.sh.
FROM ubuntu:24.04
ARG NODE_VERSION
ARG GIT_VERSION
ARG GIT_LFS_VERSION
ARG GH_VERSION
ARG JQ_VERSION
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update && apt-get install -y --no-install-recommends \
      ca-certificates curl sudo build-essential xz-utils jq \
      libcurl4-openssl-dev libssl-dev zlib1g-dev libexpat1-dev gettext \
 && rm -rf /var/lib/apt/lists/*
# Git: exact version from source; the git-core PPA only ships the latest.
RUN curl -fsSL "https://mirrors.edge.kernel.org/pub/software/scm/git/git-${GIT_VERSION}.tar.xz" | tar -xJ -C /tmp \
 && make -C "/tmp/git-${GIT_VERSION}" -j"$(nproc)" prefix=/usr/local NO_TCLTK=1 NO_RUST=1 all install >/dev/null \
 && rm -rf "/tmp/git-${GIT_VERSION}"
RUN curl -fsSL "https://github.com/git-lfs/git-lfs/releases/download/v${GIT_LFS_VERSION}/git-lfs-linux-amd64-v${GIT_LFS_VERSION}.tar.gz" | tar -xz -C /tmp \
 && install "/tmp/git-lfs-${GIT_LFS_VERSION}/git-lfs" /usr/local/bin/git-lfs && rm -rf "/tmp/git-lfs-${GIT_LFS_VERSION}"
RUN curl -fsSL "https://nodejs.org/dist/v${NODE_VERSION}/node-v${NODE_VERSION}-linux-x64.tar.xz" | tar -xJ -C /usr/local --strip-components=1
RUN curl -fsSL -o /tmp/gh.deb "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_amd64.deb" \
 && dpkg -i --ignore-depends=git /tmp/gh.deb && rm /tmp/gh.deb
# GitHub runs jobs as `runner` (uid 1001) with passwordless sudo.
RUN userdel -r ubuntu 2>/dev/null || true \
 && useradd -m -u 1001 -s /bin/bash runner \
 && echo 'runner ALL=(ALL) NOPASSWD:ALL' > /etc/sudoers.d/runner \
 && mkdir -p /home/runner/.cache/uv /home/runner/.npm && chown -R runner:runner /home/runner
USER runner
WORKDIR /home/runner
