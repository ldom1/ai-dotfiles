#!/usr/bin/env bash
# Lance scripts/install.sh deux fois dans un conteneur propre et vérifie l'idempotence :
# les deux passes sortent en 0 et la 2ᵉ ne change aucun fichier de $HOME.
# Usage : tests/install-twice.sh [image]   (défaut ubuntu:24.04). Teste le HEAD commité.
set -euo pipefail
image=${1:-ubuntu:24.04}
repo=$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)

docker run --rm -i -v "$repo:/src:ro" "$image" bash -s <<'IN'
set -euo pipefail
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null && apt-get install -y -qq git python3 tmux curl ca-certificates jq fzf >/dev/null
git config --global --add safe.directory '*'
git clone -q /src "$HOME/ai-dotfiles"
# Contenu de $HOME : liens (cible) et fichiers (md5), hors dépôts .git internes
snap() { find "$HOME" -path '*/.git' -prune -o -type l -printf '%p -> %l\n' -o -type f -exec md5sum {} + | sort; }
run() { bash "$HOME/ai-dotfiles/scripts/install.sh" > "/tmp/install-$1.log" 2>&1 || { echo "FAIL: pass $1 exit $?"; tail -20 "/tmp/install-$1.log"; exit 1; }; }
run 1; snap > /tmp/s1
run 2; snap > /tmp/s2
echo "--- opensessions, pass 1:"; grep -a opensessions /tmp/install-1.log
echo "tag: $(git -C "$HOME/.tmux/plugins/opensessions" describe --tags)"
echo "--- warnings, pass 2:"; sed -n '/Warnings:/,$p' /tmp/install-2.log
if diff /tmp/s1 /tmp/s2; then echo "OK: $(. /etc/os-release; echo "$PRETTY_NAME"): 2 passes exit 0, pass 2 changed nothing"; else echo "FAIL: pass 2 changed files"; exit 1; fi
IN
