"""Phase 0 witness — structural validation of the normative format.

Run: `python -m assurance.tests.test_schema` from `cycle/` (exit 0 = all pass).
No pytest dependency: a soundness tool's own checks stay re-runnable by anyone.
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # cycle/ on path

from assurance.schema import AssuranceGraph, Ledger, SchemaError  # noqa: E402

VALID_GRAPH = """
meta: {contract: Demo}
claims:
  - id: C1
    human: "shares are backed by assets"
    formal: "(= totalShares totalAssets)"
    shape: stateless
    verdict: proven
    engine: "solc 0.8.35 chc z3 4.16.0"
    evidence: {smt_query: "evidence/smt/C1.sol", reproduce: "solc ..."}
    depends_on:
      - {kind: assumption, ref: A_noreentry, status: assumed, human: "no reentrancy frame"}
  - id: C2
    human: "buggy mint refuted"
    formal: "(= totalShares totalAssets)"
    shape: stateless
    verdict: refuted
    engine: "solc 0.8.35 chc z3"
    evidence: {witness: {totalAssets: "0", totalShares: "1"}}
"""

VALID_LEDGER = """
assumptions:
  - id: A_noreentry
    statement_human: "external calls do not reenter"
    statement_formal: "reentrancy_frame == none"
    why_assumed: "out of solver scope"
    risk_if_false: "invariant may break under reentrancy"
    status: assumed
lean_theorems: []
harness_faithfulness: []
"""

REJECT = {
    "refuted-without-witness": """
claims:
 - {id: X, human: h, formal: f, shape: stateless, verdict: refuted, engine: e, evidence: {}}
""",
    "proven-without-evidence": """
claims:
 - {id: X, human: h, formal: f, shape: stateless, verdict: proven, engine: e, evidence: {}}
""",
    "bad-shape": """
claims:
 - {id: X, human: h, formal: f, shape: WRONG, verdict: proven, engine: e, evidence: {smt_query: q}}
""",
    "bad-edge-status": """
claims:
 - {id: X, human: h, formal: f, shape: stateless, verdict: proven, engine: e, evidence: {smt_query: q},
    depends_on: [{kind: assumption, ref: A, status: MAYBE, human: h}]}
""",
    "bad-edge-kind": """
claims:
 - {id: X, human: h, formal: f, shape: stateless, verdict: proven, engine: e, evidence: {smt_query: q},
    depends_on: [{kind: spell, ref: A, status: assumed, human: h}]}
""",
    "dup-claim-id": """
claims:
 - {id: X, human: h, formal: f, shape: stateless, verdict: inconclusive, engine: e}
 - {id: X, human: h, formal: f, shape: stateless, verdict: inconclusive, engine: e}
""",
    "no-claims": """
claims: []
""",
}

REJECT_LEDGER = {
    "dup-leaf-id": """
assumptions:
  - {id: D, statement_human: h, statement_formal: f, why_assumed: w, risk_if_false: r, status: assumed}
harness_faithfulness:
  - {id: D, target: t, claim: c, evidence: e, evidence_ref: r, status: unverified}
""",
    "bad-faithfulness-status": """
harness_faithfulness:
  - {target: t, claim: c, evidence: e, evidence_ref: r, status: maybe_ok}
""",
    "bad-build-status": """
lean_theorems:
  - {id: L, statement_human: h, statement_formal: f, file: x, theorem_name: t, build_status: green, status: proven}
""",
}


def main() -> int:
    fails: list[str] = []

    g = AssuranceGraph.parse(yaml.safe_load(VALID_GRAPH))
    lg = Ledger.parse(yaml.safe_load(VALID_LEDGER))
    assert [c.id for c in g.claims] == ["C1", "C2"], "valid graph mis-parsed"
    assert lg.ids == {"A_noreentry"}, "valid ledger mis-parsed"
    print(f"OK  valid graph+ledger parse: claims={[c.id for c in g.claims]} leaves={sorted(lg.ids)}")

    for name, doc in REJECT.items():
        try:
            AssuranceGraph.parse(yaml.safe_load(doc))
            fails.append(f"graph '{name}' should have been rejected")
            print(f"XX  graph {name}: NOT rejected")
        except SchemaError as e:
            print(f"OK  graph {name} rejected -> {e}")

    for name, doc in REJECT_LEDGER.items():
        try:
            Ledger.parse(yaml.safe_load(doc))
            fails.append(f"ledger '{name}' should have been rejected")
            print(f"XX  ledger {name}: NOT rejected")
        except SchemaError as e:
            print(f"OK  ledger {name} rejected -> {e}")

    if fails:
        print(f"\nFAILED ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print("\nALL PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
