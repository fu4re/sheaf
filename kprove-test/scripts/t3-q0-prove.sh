#!/usr/bin/env bash
# T3 Q0 toy proofs against the <inFunc>-extended fork.
set -u
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source "$ROOT/scripts/env.sh"
cd "$ROOT"
mkdir -p logs
DEF="$ROOT/repro/t3-q0/t3-kompiled"
FORK="$ROOT/repro/t3-q0"
KEVMSRC=/nix/store/53c9hz1bs88a067spgbrbbs1j3nkjlvx-source/src/kevm_pyk/kproj/evm-semantics
PLUGIN=/nix/store/p06w45wanmvpw181g53c9lgdqd90azbj-source

kprove "$ROOT/repro/t3-q0/q0-infunc-spec.k" \
  --definition "$DEF" \
  --spec-module Q0-INFUNC-SPEC \
  --depth 1 \
  -I "$FORK" -I "$KEVMSRC" -I "$PLUGIN" \
  2>&1 | tee logs/t3-q0-infunc.log
echo "kprove exit=${PIPESTATUS[0]}"
