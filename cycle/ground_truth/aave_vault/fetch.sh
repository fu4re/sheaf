#!/usr/bin/env bash
# fetch.sh — restore the Aave Vault ground truth at the pinned commit.
#
# The Aave-Vault sources are "All Rights Reserved © Aave Labs" and are therefore
# NOT committed to this public repository. This script fetches exactly the files
# PROVENANCE.md lists, at the commit it records, into src/ and certora_specs/.
# Research reference only (ground truth for Finding 0001); not a compile target.
set -euo pipefail

REPO="https://github.com/aave/Aave-Vault"
COMMIT="5ab52d20b07f35a8f34e6702f2fea6797a5787eb"
HERE="$(cd "$(dirname "$0")" && pwd)"
SPECS="erc20 methods_base positiveSupply_imply_positiveAssets fees_LEQ_ATokenBal \
changeInContractBalanceShouldCauseAccrual lastVaultBal_LEQ_ATokenBalThis \
totalSupply_EQ_sumAllBal accrueYieldCheck erc4626 rayMul_rayDiv_mulDiv_properties"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
git -C "$TMP" init -q
git -C "$TMP" remote add origin "$REPO"
git -C "$TMP" fetch -q --depth 1 origin "$COMMIT"
git -C "$TMP" checkout -q FETCH_HEAD

mkdir -p "$HERE/src" "$HERE/certora_specs"
cp "$TMP/src/ATokenVault.sol" "$TMP/src/ATokenVaultStorage.sol" "$HERE/src/"
for s in $SPECS; do
  f="$(find "$TMP" -name "$s.spec" -not -path '*/node_modules/*' | head -1)"
  [ -n "$f" ] || { echo "missing spec: $s" >&2; exit 1; }
  cp "$f" "$HERE/certora_specs/"
done
echo "fetched Aave-Vault @ $COMMIT: 2 sources, $(ls "$HERE/certora_specs" | wc -l | tr -d ' ') specs"
