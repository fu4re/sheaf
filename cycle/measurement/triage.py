"""Module [6] — Symbolic triage (Task 0002, Goal B). The SOLVER is the judge.

Replaces the pilot's LLM judge: every candidate invariant gets a SOLVER verdict
— proven / refuted(+counterexample) / unknown(harness-bound) — and "recovered vs
ground truth" + corollary-dedup are decided by solver-checked logical implication
over the contract's reachable states, never by a model.

Trust note: ghost-arithmetic axioms inside a ghost harness are taken as
ASSUMED-VERIFIED here. They are separately discharged in Lean
(cycle/trusted/proofs/) — referenced as evidence, NOT code-linked (decoupled by
decision; the link is its own task).
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gateway.translator import (  # noqa: E402
    build_cross_harness,
    build_from_harness,
    build_harness,
    validate_compiles,
)
from trusted.solver import run_solver  # noqa: E402

BUILD = ROOT / "measurement" / "artifacts" / "build"
_BUCKET = {
    "proved": "proven",
    "counterexample": "refuted",
    "inconclusive": "unknown",
    "compile_error": "malformed",
}


def _harness(sut, contract, expr, tag, template=None):
    if template is not None:
        return build_from_harness(template, contract, expr, BUILD, tag=tag)
    return build_harness(sut, contract, expr, BUILD, tag=tag)


def triage_one(sut, contract, name, expr, template=None) -> dict:
    """One candidate -> {proven | refuted(+witness) | unknown | malformed}."""
    h = _harness(sut, contract, expr, name, template)
    ok, errors, _ = validate_compiles(h)
    if not ok:
        return {"name": name, "expr": expr, "bucket": "malformed", "detail": errors[:2]}
    v = run_solver(h)
    return {
        "name": name,
        "expr": expr,
        "bucket": _BUCKET.get(v.verdict, "unknown"),
        "witness": v.witness,
        "reason": v.reason,
    }


def implies(sut, contract, a, b, tag, template=None):
    """a ⇒ b over all reachable states. True/False, or None if harness-bound."""
    h = _harness(sut, contract, f"!({a}) || ({b})", tag, template)
    ok, _, _ = validate_compiles(h)
    if not ok:
        return None
    verdict = run_solver(h).verdict
    if verdict == "proved":
        return True
    if verdict == "counterexample":
        return False
    return None  # inconclusive → undecidable in budget (do not confuse with refuted)


def equivalent(sut, contract, a, b, tag, template=None):
    """Reachable-state equivalence (None if either direction is harness-bound)."""
    f = implies(sut, contract, a, b, tag + "_f", template)
    g = implies(sut, contract, b, a, tag + "_b", template)
    if f is None or g is None:
        return None
    return f and g


def triage_set(sut, contract, candidates, template=None) -> dict:
    """Triage a candidate set + solver-dedup the proven ones into equivalence classes."""
    triaged = [triage_one(sut, contract, c["name"], c["solidity_expr"], template) for c in candidates]
    proven = [t for t in triaged if t["bucket"] == "proven"]
    classes: list[list[dict]] = []
    for t in proven:
        for cls in classes:
            if equivalent(sut, contract, t["expr"], cls[0]["expr"], f"dd_{t['name']}_{cls[0]['name']}", template):
                cls.append(t)
                break
        else:
            classes.append([t])
    counts = {b: sum(1 for t in triaged if t["bucket"] == b)
              for b in ("proven", "refuted", "unknown", "malformed")}
    return {
        "counts": counts,
        "solver_judged": f"{len(triaged)}/{len(triaged)}",
        "proven_equiv_classes": [[t["name"] for t in cls] for cls in classes],
        "triaged": triaged,
    }


def recall_vs_ground_truth(sut, contract, candidates, ground_truth, template=None) -> list:
    """For each ground-truth invariant, is it recovered by a candidate (solver-checked)?"""
    out = []
    for g in ground_truth:
        status, matched = "missed", None
        for c in candidates:
            if equivalent(sut, contract, c["solidity_expr"], g["solidity_expr"], f"rc_{c['name']}_{g['id']}", template):
                status, matched = "recovered", c["name"]
                break
            if implies(sut, contract, c["solidity_expr"], g["solidity_expr"], f"ri_{c['name']}_{g['id']}", template):
                status, matched = "implied_by_stronger", c["name"]
        out.append({"ground_truth": g["id"], "status": status, "matched": matched})
    return out


# =====================================================================================
# Cross-contract assume-guarantee triage (Task 0003). The solver judges THREE A/G
# obligations with the SAME proven/refuted/unknown vocabulary it uses for self-contained
# contracts, and MINES the weakest sufficient guarantee by ablation — no LLM judge.
# =====================================================================================

def _caller_verdict(caller_template, caller_contract, invariant_expr, summary_exprs, tag) -> str:
    """Obligation 1: prove the caller law I_A under a given guarantee summary."""
    h = build_cross_harness(caller_template, caller_contract, invariant_expr, summary_exprs, BUILD, tag=tag)
    ok, _errors, _ = validate_compiles(h)
    if not ok:
        return "malformed"
    return _BUCKET.get(run_solver(h).verdict, "unknown")


def _clause_implies(a: str, b: str, tag: str) -> bool:
    """Pure-formula implication a ⇒ b over the free call vars (vaultBal, vaultBal_post,
    assets), uint128-capped so the sum cannot overflow. Used to rank sufficient clauses
    by logical strength so the WEAKEST (most reusable) one can be reported."""
    src = (
        "// SPDX-License-Identifier: MIT\n"
        "pragma solidity ^0.8.0;\n"
        "contract __Impl {\n"
        "    function check(uint256 vaultBal, uint256 vaultBal_post, uint256 assets) public pure {\n"
        "        require(vaultBal <= type(uint128).max);\n"
        "        require(vaultBal_post <= type(uint128).max);\n"
        "        require(assets <= type(uint128).max);\n"
        f"        assert(!({a}) || ({b}));\n"
        "    }\n"
        "}\n"
    )
    p = BUILD / f"impl_{_safe_tag(tag)}.sol"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(src)
    ok, _, _ = validate_compiles(p)
    if not ok:
        return False
    return run_solver(p).verdict == "proved"


def _safe_tag(tag: str) -> str:
    import re as _re
    return _re.sub(r"[^A-Za-z0-9_]+", "_", tag).strip("_")


def mine_interface(caller_template, caller_contract, invariant_expr, deposit_clauses, withdraw_clause) -> dict:
    """Weakest-sufficient interface mining (the 'solver discards the unneeded' move).
    Each candidate is an over-generated caller-side guarantee clause for the deposit
    call. The solver decides, with no LLM judge: (a) SUFFICIENCY — does the clause alone
    prove I_A; (b) among sufficient clauses, which is logically WEAKEST (implied by all
    other sufficient ones) — that is the tightest demand on the callee, the most
    reusable summary. Insufficient clauses are discarded."""
    results = []
    for c in deposit_clauses:
        v = _caller_verdict(caller_template, caller_contract, invariant_expr,
                            [c["expr"], withdraw_clause], tag=f"suff_{c['name']}")
        results.append({"name": c["name"], "expr": c["expr"], "sufficient": v == "proven", "verdict": v})
    sufficient = [c for c in results if c["sufficient"]]
    weakest = None
    for c in sufficient:
        others = [o for o in sufficient if o["name"] != c["name"]]
        if all(_clause_implies(o["expr"], c["expr"], f"{o['name']}__to__{c['name']}") for o in others):
            weakest = c["name"]
            break
    return {
        "clauses": results,
        "sufficient": [c["name"] for c in sufficient],
        "discarded_insufficient": [c["name"] for c in results if not c["sufficient"]],
        "weakest_sufficient": weakest,
    }


def triage_callees(callee_templates: dict, clause_name: str, clause_expr: str) -> dict:
    """Obligation 2 across honest + adversarial callees: discharge the guarantee on each
    callee's tracked-sum harness. Honest → proven; a callee that violates it → refuted."""
    out = {}
    for label, (sut, contract, template) in callee_templates.items():
        t = triage_one(sut, contract, f"{label}_{clause_name}", clause_expr, template=template)
        out[label] = t["bucket"]
    return out


def discharge(harness_path, engines=("chc", "bmc")) -> dict:
    """Discharge a pre-baked guarantee harness (the assert is already the property — e.g. a
    2-state delta) under MULTIPLE engines. CHC and BMC are complementary: BMC catches the
    short multi-tx counterexamples CHC reports as 'could not be proved' (Finding 0002). So:
    refuted if ANY engine finds a counterexample; proven if some engine proves and none
    refutes; else unknown. This is the per-clause callee discharge that closes the gap of
    conservation-only obligation 2 (the mined caller clause must be discharged, not a proxy)."""
    by = {}
    for e in engines:
        by[e] = _BUCKET.get(run_solver(Path(harness_path), engine=e).verdict, "unknown")
    if "refuted" in by.values():
        return {"bucket": "refuted", "by": by}
    if "proven" in by.values():
        return {"bucket": "proven", "by": by}
    return {"bucket": "unknown", "by": by}


if __name__ == "__main__":
    C = ROOT / "contracts"
    print("### MiniVault (subclass) — buckets + solver dedup ###")
    cands = [
        {"name": "conservation", "solidity_expr": "totalShares == totalAssets"},
        {"name": "solvency", "solidity_expr": "totalShares <= totalAssets"},
        {"name": "false_strict", "solidity_expr": "totalShares < totalAssets"},
        {"name": "bogus", "solidity_expr": "totalShares >= totalAssets + 1"},
    ]
    r = triage_set(C / "MiniVault.sol", "MiniVault", cands)
    print("  counts:", json.dumps(r["counts"]))
    for t in r["triaged"]:
        w = f"  witness={t['witness']['assignments']}" if t.get("witness") else ""
        print(f"    {t['bucket']:9} {t['name']}{w}")
    print("  proven equivalence classes (solver-deduped):", r["proven_equiv_classes"])

    print("### recall vs ground truth {totalShares == totalAssets} ###")
    gt = [{"id": "conservation_law", "solidity_expr": "totalShares == totalAssets"}]
    print("  ", recall_vs_ground_truth(C / "MiniVault.sol", "MiniVault", cands, gt))

    print("### ProportionalVault — same invariant, subclass(wall) vs ghost ###")
    pv = C / "ProportionalVault.sol"
    ghost = ROOT / "trusted" / "harness" / "ProportionalVaultGhost.sol"
    sub = triage_one(pv, "ProportionalVault", "solvency", "totalShares <= totalAssets")
    gho = triage_one(pv, "ProportionalVault", "solvency", "totalShares <= totalAssets", template=ghost)
    print(f"    subclass -> {sub['bucket']} ({sub.get('reason','')[:40]})")
    print(f"    ghost    -> {gho['bucket']}")
