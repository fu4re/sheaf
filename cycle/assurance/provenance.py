"""provenance.py — emit an in-toto provenance statement for the package.

Provenance is in the trusted base of the *supply* (was this package tampered with?),
NOT of the *claim* (is the claim true?). The claim's trust lives in the graph +
ledger + evidence; this wrapper only attests how the package was produced and pins
each file's digest so a recipient detects substitution.

Output: `provenance.intoto.json` — an in-toto Statement v1 whose subjects are the
package's core+evidence files with sha256 digests. DSSE signing is a separate step
that needs key material; we emit the (unsigned) statement and, with --dsse, wrap it
in a DSSE PAE envelope with an empty signatures list so a signer can fill it in.
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # cycle/ on path

from assurance.schema import AssuranceGraph, Ledger  # noqa: E402

PREDICATE_TYPE = "https://sheaf.dev/assurance/provenance/v0.1"
STATEMENT_TYPE = "https://in-toto.io/Statement/v1"

# files that are part of the attested package (the provenance file itself excluded).
_INCLUDE_SUFFIXES = {".yaml", ".sol", ".lean", ".json", ".md"}
_EXCLUDE_NAMES = {"provenance.intoto.json"}


def _sha256(p: Path) -> str:
    h = hashlib.sha256()
    h.update(p.read_bytes())
    return h.hexdigest()


def _subjects(pkg: Path) -> list[dict]:
    subs = []
    for p in sorted(pkg.rglob("*")):
        if not p.is_file() or p.name in _EXCLUDE_NAMES:
            continue
        if p.suffix not in _INCLUDE_SUFFIXES:
            continue
        subs.append({"name": str(p.relative_to(pkg)), "digest": {"sha256": _sha256(p)}})
    return subs


def build_statement(pkg: Path, build_invocation: str | None = None) -> dict:
    graph = AssuranceGraph.load(pkg / "assurance_graph.yaml")
    ledger = Ledger.load(pkg / "trusted" / "ledger.yaml")
    meta = graph.meta

    depended = {e.ref for c in graph.claims for e in c.depends_on if e.kind == "claim"}
    tops = [c for c in graph.claims if c.id not in depended]

    predicate = {
        "buildType": "https://sheaf.dev/assurance/assemble",
        "builder": {"id": "sheaf/cycle/assurance/assemble.py"},
        "invocation": {"command": build_invocation or "python -m assurance.assemble ..."},
        "toolchain": {
            "engines": sorted({c.engine for c in graph.claims}),
            "lean": sorted({t.theorem_name + " @ " + t.file for t in ledger.lean_theorems}),
        },
        "claimSummary": {
            "contract": meta.get("contract"),
            "topClaims": [
                {"id": c.id, "formal": c.formal, "verdict": c.verdict} for c in tops
            ],
            "trustedBase": {
                "leanTheorems": [t.id for t in ledger.lean_theorems],
                "assumptions": [a.id for a in ledger.assumptions],
                "harnessFaithfulness": [
                    {"id": h.id, "status": h.status} for h in ledger.harness_faithfulness
                ],
            },
        },
        "note": "Provenance attests the SUPPLY (no tampering), not the CLAIM (truth). "
                "Claim trust = graph + ledger + evidence, re-checked by verify_package.py.",
    }
    return {
        "_type": STATEMENT_TYPE,
        "subject": _subjects(pkg),
        "predicateType": PREDICATE_TYPE,
        "predicate": predicate,
    }


def dsse_envelope(statement: dict) -> dict:
    """Unsigned DSSE envelope. signatures is empty: a signer with key material fills
    it using PAE(payloadType, payload). We never fabricate a signature."""
    payload = base64.b64encode(json.dumps(statement).encode()).decode()
    return {
        "payloadType": "application/vnd.in-toto+json",
        "payload": payload,
        "signatures": [],  # unsigned — sign out of band; empty is honest, a fake sig is not
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Emit in-toto provenance for a package.")
    ap.add_argument("package")
    ap.add_argument("--dsse", action="store_true", help="wrap in an unsigned DSSE envelope")
    ap.add_argument("--invocation", default=None, help="record the assemble command used")
    args = ap.parse_args(argv)
    pkg = Path(args.package).resolve()
    stmt = build_statement(pkg, args.invocation)
    out = pkg / "provenance.intoto.json"
    payload = dsse_envelope(stmt) if args.dsse else stmt
    out.write_text(json.dumps(payload, indent=2))
    print(f"wrote {out} ({len(stmt['subject'])} subjects, "
          f"{'DSSE unsigned' if args.dsse else 'statement'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
