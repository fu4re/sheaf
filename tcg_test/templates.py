"""Spine synthesizer — turn a run into an assurance-graph spine.

The spine is the EPISTEMIC composition (assemble.py fuses it with the mechanical
evidence records). For a source-level tcg run it is small and fixed in shape:

    C1  the Post invariant (the economic law), verdict from the K gate
        ├─ proven →  L_<axiom>            ghost axioms discharged by the Lean kernel
        ├─ assumed → A_solver             IRREDUCIBLE (ADR Assumption 3)
        ├─ assumed → A_machine_semantics  IRREDUCIBLE (ADR Assumption 1)
        ├─ assumed → A_human_intent       IRREDUCIBLE (ADR Assumption 7)
        ├─ assumed → phi_context          DISCHARGEABLE (deferred φ dimensions)
        └─ assumed → H_bytecode           DISCHARGEABLE (Inv.7, unverified at source)

Every assumed leaf is tagged `leaf_class: irreducible|dischargeable` so the render
rule can cap the top status: a proven C1 over an OPEN dischargeable leaf is NOT
green (Finding 0007). A refuted run produces an honest-negative C1 with a witness.
"""
from __future__ import annotations

# φ.post shape → assurance schema shape (schema.SHAPES)
_SHAPE = {
    "stateless": "stateless",
    "quantified-over-mapping": "quantified-over-mapping",
    "temporal-2state": "temporal-2state",
}


def _irreducible_assumptions(engine: str) -> list[dict]:
    return [
        {"id": "A_solver", "leaf_class": "irreducible", "status": "assumed",
         "statement_human": "The SMT solver's verdicts (z3 via SMTChecker) are sound.",
         "statement_formal": f"trust({engine}) — no independent kernel re-check of the SMT proof",
         "why_assumed": "ADR Assumption 3. The CHC/BMC proof is taken on the solver's word; "
                        "lean-smt kernel reconstruction would replace this leaf (separate track). "
                        "Visible, not hidden.",
         "risk_if_false": "A solver soundness bug would make a 'proven' claim false. Mitigated by "
                          "determinism and witness-bearing refutations, not eliminated."},
        {"id": "A_machine_semantics", "leaf_class": "irreducible", "status": "assumed",
         "statement_human": "SMTChecker's model of the EVM is faithful to the real EVM.",
         "statement_formal": "model(SMTChecker EVM) ≈ real EVM / KEVM bytecode semantics",
         "why_assumed": "ADR Assumption 1. The source-level proof reasons over SMTChecker's EVM "
                        "abstraction; a full bytecode-semantics discharge (KEVM/Halmos) is a "
                        "separate verify-level.",
         "risk_if_false": "A semantic gap between the modelled and the executed EVM could let a "
                          "'proven' source property fail on-chain."},
        {"id": "A_human_intent", "leaf_class": "irreducible", "status": "assumed",
         "statement_human": "H attests that φ captures the intended economic property.",
         "statement_formal": "φ ≈ intent (frozen by H; the single non-formal trust leaf)",
         "why_assumed": "ADR Assumption 7. The translation from human economic intent to the "
                        "formal φ is validated by a human, not a machine.",
         "risk_if_false": "If φ misstates the intent, a correct proof discharges the wrong property."},
    ]


def _dischargeable_assumptions(phi_context: list[str]) -> list[dict]:
    return [
        {"id": "phi_context", "leaf_class": "dischargeable", "status": "assumed",
         "statement_human": "The deferred φ dimensions are NOT mechanically discharged.",
         "statement_formal": f"φ_context = {phi_context} (declared in φ, not checked by K)",
         "why_assumed": "ADR §2.2. Trace-deep, exit-safety and exit-outofgas are represented in "
                        "φ but not discharged at source level (havoc wall / runner limits).",
         "risk_if_false": "A property in φ_context could fail though the checked subset holds — "
                          "the verified claim covers only φ_checked.",
         "discharge_path": "full-tuple φ coverage: deep-Trace via KEVM/Halmos, exit-safety via a "
                           "safety-verdict parser (backlog)."},
    ]


def _bytecode_faithfulness() -> dict:
    return {
        "id": "H_bytecode", "leaf_class": "dischargeable",
        "target": "source ↔ deployed runtime bytecode",
        "claim": "the verified source compiles to the deployed runtime bytecode, bit-identical",
        "evidence": "not measured at source level (runtime-hash + pinned settings + immutables/"
                    "constructor/metadata accounting is the intended evidence — Sourcify-style)",
        "evidence_ref": "n/a",
        "status": "unverified",
        "discharge_path": "runtime bytecode hash + pinned compiler settings (Inv.7).",
    }


def build_spine(*, phi: dict, k_result: str, engine: str, assurance_level: str,
                claim_scope: str, phi_context: list[str], lean_leaves: list[dict],
                date: str) -> dict:
    """Synthesize the spine dict. `lean_leaves` is a list of
    {id, record_id, human, status} for ghost-axiom Lean theorems (may be empty)."""
    post = phi["spec"]["post"][0]
    shape = _SHAPE.get(post.get("shape", "stateless"), "stateless")
    verdict_word = {"accept": "proven", "refute": "refuted"}.get(k_result, "inconclusive")

    meta = {
        "contract": phi["contract"], "method": phi["method"], "date": date,
        "task": "tcg assurance package (T2)",
        "phi_hash": phi.get("freeze", {}).get("content_hash"),
        "assurance_level": assurance_level,   # render-rule anchor (e.g. ⊥_assumptions_open)
        "claim_scope": claim_scope,
        "note": "Source-level run. A proven Post over an OPEN dischargeable leaf "
                "(H_bytecode / phi_context) is NOT green — see render-rule.",
    }

    if verdict_word == "refuted":
        # honest negative: a refuted Post needs only its witness; no proof edges.
        claims = [{
            "id": "C1", "shape": shape, "evidence_record": "R_post",
            "human": f"Honest negative: the Post invariant `{post['solidity_expr']}` is REFUTED "
                     f"with a concrete counterexample (no value is claimed proved).",
        }]
        ledger = {
            "lean_theorems": [], "harness_faithfulness": [],
            "assumptions": [{
                "id": "A_solver", "leaf_class": "irreducible", "status": "assumed",
                "statement_human": "The solver's refuting witness is a real reachable counterexample.",
                "statement_formal": f"trust({engine}) for the counterexample",
                "why_assumed": "ADR Assumption 3 — the refutation is the solver's; the witness is "
                               "retained and re-checkable.",
                "risk_if_false": "A solver bug could surface a spurious counterexample; mitigated by "
                                 "the concrete witness which --replay re-derives."}],
        }
        return {"meta": meta, "claims": claims, "ledger": ledger}

    # proven / inconclusive: full leaf set
    depends_on = [
        {"kind": "lean_theorem", "ref": lf["id"], "status": lf.get("status", "proven"),
         "human": lf["human"]}
        for lf in lean_leaves
    ] + [
        {"kind": "assumption", "ref": "A_solver", "status": "assumed",
         "human": "the SMT proof is trusted (z3/SMTChecker), not re-checked by a Lean kernel"},
        {"kind": "assumption", "ref": "A_machine_semantics", "status": "assumed",
         "human": "SMTChecker's EVM model is faithful to the real EVM (source-level)"},
        {"kind": "assumption", "ref": "A_human_intent", "status": "assumed",
         "human": "H attests φ captures the intended economic property"},
        {"kind": "assumption", "ref": "phi_context", "status": "assumed",
         "human": "deferred φ dimensions are not discharged — claim covers only φ_checked"},
        {"kind": "harness_faithfulness", "ref": "H_bytecode", "status": "assumed",
         "human": "the verified source equals the deployed bytecode (UNVERIFIED — Inv.7)"},
    ]
    claims = [{
        "id": "C1", "shape": shape, "evidence_record": "R_post",
        "human": post.get("informal") or f"The Post economic invariant `{post['solidity_expr']}` "
                 f"holds over all reachable states.",
        "depends_on": depends_on,
    }]
    ledger = {
        "lean_theorems": [
            {"id": lf["id"], "evidence_record": lf["record_id"], "status": lf.get("status", "proven")}
            for lf in lean_leaves
        ],
        "assumptions": _irreducible_assumptions(engine) + _dischargeable_assumptions(phi_context),
        "harness_faithfulness": [_bytecode_faithfulness()],
    }
    return {"meta": meta, "claims": claims, "ledger": ledger}
