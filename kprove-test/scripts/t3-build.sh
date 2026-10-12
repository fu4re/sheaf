#!/usr/bin/env bash
# T3 Q0: kompile the <inFunc>-extended fork (T1 fork + stack-like reentrancy monitor).
# Include order matters: -I <fork dir> FIRST so `requires "evm.md"` binds the FORKED evm.md,
# not the stock KEVM one; then the KEVM source tree; then the plugin root (for plugin/krypto.md).
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
cd "$ROOT"
mkdir -p logs

FORK="$ROOT/repro/t3-q0"
KEVMSRC=/nix/store/53c9hz1bs88a067spgbrbbs1j3nkjlvx-source/src/kevm_pyk/kproj/evm-semantics
PLUGIN=/nix/store/p06w45wanmvpw181g53c9lgdqd90azbj-source

kompile "$FORK/kevm-fork-t3.k" \
  --backend haskell \
  --main-module KEVM-FORK-T3 \
  --syntax-module KEVM-FORK-T3 \
  --output-definition "$FORK/t3-kompiled" \
  -I "$FORK" \
  -I "$KEVMSRC" \
  -I "$PLUGIN" \
  2>&1 | tee logs/t3-q0-kompile.log
ec=${PIPESTATUS[0]}
echo "kompile exit=$ec"
exit $ec
