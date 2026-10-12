"""φ — the full machine-configuration tuple (Pre, Trace, Post, Exit), on disk.

ADR-0003 §2.2 defines the specification as φ = (Pre, Trace, Post, Exit) and
names the SILENT collapse to a terminal-only property (Trace=true, Exit={halt})
a DEFECT. So φ is represented here as all four dimensions EXPLICITLY — even where
the MVP only mechanically discharges a subset. What is checked vs deferred is
recorded in `coverage`, never dropped:

    φ_checked  = coverage.checked_dimensions   (K discharges these mechanically)
    φ_context  = coverage.deferred_dimensions  (declared, NOT checked)

A verified claim is only ever about φ_checked. A non-empty φ_context is the
Obj-2 soundness trip-wire: the run cannot be called green (it routes to
⊥_assumptions_open in Task 0008), because "the artifact satisfies φ" is false
when Trace/Exit are merely recorded.

Freeze (ADR Inv.6 + Inv.9): once H approves, φ is frozen by a content hash over
a FIXED, documented key set (`HASH_KEYS`) plus the pinned checker parameters.
Any downstream command (or a future autonomous loop) recomputes that hash and
REFUSES on mismatch — mechanically forbidding anyone from weakening the spec
they are checked against. The hash domain is recorded in the freeze block
(`hashed_keys`) so a third party can recompute it without reading this file.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml

SCHEMA = "tcg/phi/v1"

# The EXACT keys the freeze hash covers. Chosen so that nothing load-bearing for
# the verdict can change post-freeze: the spec tuple itself AND the coverage split
# (which decides φ_checked vs φ_context). `intent_ref` (a pointer) and `provenance`
# (run metadata) are deliberately OUT — they do not change what is proved.
HASH_KEYS = ["schema", "contract", "method", "spec", "coverage"]


def canonical_bytes(phi: dict) -> bytes:
    """Deterministic serialization of the hashed sub-payload. Independent of YAML
    dump order: keys are sorted, whitespace is fixed."""
    payload = {k: phi[k] for k in HASH_KEYS if k in phi}
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def content_hash(phi: dict) -> str:
    return hashlib.sha256(canonical_bytes(phi)).hexdigest()


def is_frozen(phi: dict) -> bool:
    return bool(phi.get("freeze", {}).get("content_hash"))


def verify_frozen(phi: dict) -> tuple[bool, str, str]:
    """Recompute the hash over the freeze block's declared `hashed_keys` and compare
    to the stored `content_hash`. Returns (ok, expected, got). A mismatch means the
    spec was tampered with after H froze it — the caller MUST refuse (Inv.6)."""
    if not is_frozen(phi):
        return (False, "<frozen>", "<not frozen — no freeze.content_hash>")
    fr = phi["freeze"]
    keys = fr.get("hashed_keys", HASH_KEYS)
    payload = {k: phi[k] for k in keys if k in phi}
    got = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"),
                   ensure_ascii=False).encode("utf-8")
    ).hexdigest()
    expected = fr["content_hash"]
    return (got == expected, expected, got)


def phi_checked(phi: dict) -> list[str]:
    return list(phi.get("coverage", {}).get("checked_dimensions", []))


def phi_context(phi: dict) -> list[str]:
    """Declared-but-unchecked dimensions. Non-empty ⇒ the run is NOT green
    (⊥_assumptions_open) — a verified claim covers only φ_checked."""
    return list(phi.get("coverage", {}).get("deferred_dimensions", []))


def freeze(phi: dict, *, approved_by: str, approved_at: str,
           intent_attestation: str, checker_params: dict) -> dict:
    """Return a NEW φ dict with a freeze block. The hash is computed over the FINAL
    spec/coverage; callers must not mutate `spec`/`coverage` afterward (a later
    verify_frozen would catch it, but the contract is freeze == final)."""
    frozen = dict(phi)
    frozen["freeze"] = {
        "content_hash": content_hash(phi),
        "hashed_keys": HASH_KEYS,
        "hash_algo": "sha256",
        "approved_by": approved_by,
        "approved_at": approved_at,
        "intent_attestation": intent_attestation,
        "checker_params": checker_params,  # Inv.9 — re-pinned at check time
    }
    return frozen


# --- YAML I/O (matches the assurance layer: sort_keys=False, allow_unicode) ----

def load(path: str | Path) -> dict:
    return yaml.safe_load(Path(path).read_text())


def dump(phi: dict, path: str | Path) -> Path:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(yaml.safe_dump(phi, sort_keys=False, allow_unicode=True))
    return p
