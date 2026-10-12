#!/usr/bin/env bash
# Sourceable: puts the nix-installed K/Kontrol/KEVM toolchain on PATH.
# Usage: source scripts/env.sh
if [ -e /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh ]; then
  . /nix/var/nix/profiles/default/etc/profile.d/nix-daemon.sh 2>/dev/null
fi
export PATH="$HOME/.nix-profile/bin:/nix/var/nix/profiles/default/bin:$HOME/.foundry/bin:$PATH"
