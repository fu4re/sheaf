#!/usr/bin/env bash
# Reproducible build of the VaultAssetAG assurance package (Task 0003 pilot).
# Run from the cycle/ directory:  bash artifact_format/pilot-vaultasset-2026-06-26.src/build.sh
#
# Pipeline: bridge (legacy json -> records) -> assemble (spine + records -> package)
#           -> render AUDIT.md -> provenance -> verify (--replay).
# assemble() wipes the output dir, so AUDIT.md/provenance are regenerated after it.
set -euo pipefail

SRC=artifact_format/pilot-vaultasset-2026-06-26.src
PKG=artifact_format/pilot-vaultasset-2026-06-26

echo "[1/5] bridge existing artifacts -> evidence records"
python3 -m assurance.adapters.bridge_existing --out "$SRC/records"

echo "[2/5] assemble package (spine + records)"
python3 -m assurance.assemble --spine "$SRC/spine.yaml" --records "$SRC/records" \
        --out "$PKG" --src-root .

echo "[3/5] render view/AUDIT.md from core"
python3 -m assurance.render_audit "$PKG"

echo "[4/5] emit in-toto provenance (unsigned DSSE)"
python3 -m assurance.provenance "$PKG" --dsse --invocation "$SRC/build.sh"

echo "[5/5] verify package (static + replay)"
python3 -m assurance.verify_package "$PKG" --replay
