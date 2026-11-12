#!/usr/bin/env bash
# Dans un conteneur propre : scripts/install.sh deux fois (les deux passes sortent en 0, la 2ᵉ
# ne change aucun fichier de $HOME), puis les tests bats. Sur la branche Ubuntu native, la 1ʳᵉ passe
# télécharge le .deb d'Orca (réseau) et prépare ses réglages ; elle n'installe rien (pas de sudo).
# Usage : tests/container.sh [image] [wsl|linux]   (défaut ubuntu:24.04, plateforme détectée).
# Sous WSL, Docker partage le noyau « microsoft » : passer linux pour tester la branche Ubuntu native.
# Teste le HEAD commité.
set -euo pipefail
image=${1:-ubuntu:24.04}
platform=${2:-}
repo=$(git -C "$(dirname "$0")/.." rev-parse --show-toplevel)

docker run --rm -i -e AIF_PLATFORM="$platform" -v "$repo:/src:ro" "$image" bash -s <<'IN'
set -euo pipefail
[ -n "$AIF_PLATFORM" ] || unset AIF_PLATFORM
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq >/dev/null
apt-get install -y -qq git python3 curl ca-certificates jq bats procps util-linux zsh >/dev/null
git config --global --add safe.directory '*'
git clone -q /src "$HOME/ai-dotfiles"
# Contenu de $HOME : liens (cible) et fichiers (md5), hors dépôts .git internes
snap() { find "$HOME" -path '*/.git' -prune -o -type l -printf '%p -> %l\n' -o -type f -exec md5sum {} + | sort; }
run() { bash "$HOME/ai-dotfiles/scripts/install.sh" > "/tmp/install-$1.log" 2>&1 || { echo "FAIL: pass $1 exit $?"; tail -20 "/tmp/install-$1.log"; exit 1; }; }
run 1; snap > /tmp/s1
run 2; snap > /tmp/s2
os="$(. /etc/os-release; echo "$PRETTY_NAME")"
echo "--- $os, pass 1:"; grep -aE 'platform:|Orca' /tmp/install-1.log
echo "--- warnings, pass 2:"; sed -n '/Warnings:/,$p' /tmp/install-2.log
diff /tmp/s1 /tmp/s2 || { echo "FAIL: pass 2 changed files"; exit 1; }
for rc in .bashrc .zshenv; do
  [ "$(grep -c 'config/shell-init.sh' "$HOME/$rc")" -eq 1 ] || { echo "FAIL: ~/$rc must source shell-init.sh once"; exit 1; }
done
echo "OK: $os: 2 passes exit 0, pass 2 changed nothing"
bats "$HOME/ai-dotfiles/tests/"
IN
