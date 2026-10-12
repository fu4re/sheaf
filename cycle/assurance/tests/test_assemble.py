"""Phase 2 witness — emit -> assemble -> verify end-to-end.

A component emits records via emit.py; a hand-authored spine declares the epistemic
composition; assemble() fuses them; the linter must return WELL-FORMED. Proves the
hybrid path works with no translation layer and no real-artifact dependency.

Run: `python -m assurance.tests.test_assemble` from `cycle/` (exit 0 = pass).
"""
from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # cycle/ on path

from assurance import emit  # noqa: E402
from assurance.assemble import assemble  # noqa: E402
from assurance.verify_package import lint  # noqa: E402


def main() -> int:
    work = Path(tempfile.mkdtemp(prefix="assur_p2_"))
    src = work / "src"
    recs = work / "records"
    src.mkdir()
    (src / "harness.sol").write_text("pragma solidity ^0.8.0; contract H {}")
    (src / "Proof.lean").write_text("theorem t : True := trivial")

    # --- a component emits records in the format's vocabulary (no translation) --
    emit.emit_smt(
        "R_caller",
        human="vault holds at least what it accounts for",
        formal="(>= vaultBal totalAssets)",
        verdict="proven", engine="solc 0.8.35 chc z3 4.16.0",
        shape="stateless", harness="harness.sol",
        reproduce="solc --model-checker-engine chc ...",
        produced_by={"component": "smtchecker"}, out_dir=recs,
    )
    emit.emit_smt(
        "R_bug",
        human="buggy mint creates a share from nothing",
        formal="(= totalShares totalAssets)",
        verdict="refuted", engine="solc 0.8.35 chc z3",
        witness={"totalAssets": "0", "totalShares": "1"}, out_dir=recs,
    )
    emit.emit_lean(
        "R_lean",
        human="transfer preserves the balance-sum",
        formal="(a - amt) + (b + amt) = a + b",
        theorem_name="Erc20.transfer_pair_sum_preserved",
        lean_file="Proof.lean", build_status="ok",
        lean_project="/canonical/lake/project", out_dir=recs,
    )

    # --- the human authors the spine (epistemic composition) ----------------
    spine = {
        "meta": {"contract": "Demo", "date": "2026-06-26"},
        "claims": [
            {"id": "C_solvency", "shape": "stateless", "evidence_record": "R_caller",
             "depends_on": [
                 {"kind": "lean_theorem", "ref": "L_cons", "status": "proven",
                  "human": "callee conservation, Lean kernel"},
                 {"kind": "assumption", "ref": "A_guarantee", "status": "assumed",
                  "human": "callee credits recipient by >= amount"},
                 {"kind": "harness_faithfulness", "ref": "H_model", "status": "assumed",
                  "human": "harness <-> bytecode unverified"},
             ]},
            {"id": "C_bug", "shape": "stateless", "evidence_record": "R_bug"},
        ],
        "ledger": {
            "lean_theorems": [
                {"id": "L_cons", "evidence_record": "R_lean", "status": "proven"},
            ],
            "assumptions": [
                {"id": "A_guarantee",
                 "statement_human": "every transfer credits the recipient by >= amount",
                 "statement_formal": "vaultBal_post >= vaultBal + assets",
                 "why_assumed": "callee guarantee discharged separately (A/G)",
                 "risk_if_false": "caller solvency proof does not hold",
                 "status": "assumed"},
            ],
            "harness_faithfulness": [
                {"id": "H_model", "target": "VaultAsset.deposit",
                 "claim": "the cross harness models deployed bytecode",
                 "evidence": "not measured", "evidence_ref": "n/a", "status": "unverified"},
            ],
        },
    }
    spine_path = work / "spine.yaml"
    spine_path.write_text(yaml.safe_dump(spine, sort_keys=False))

    pkg = assemble(spine_path, recs, work / "pkg", src)
    rep = lint(pkg)

    print(f"assembled package at {pkg}")
    for f in rep.findings:
        if f.status != "PASS":
            print(f"  [{f.status}] {f.check}: {f.message}")
    print(f"VERDICT: {rep.verdict} (exit {rep.exit_code})")

    ok = rep.verdict == "WELL-FORMED"
    # sanity: the assembled graph really pulled formal/verdict from records
    graph = yaml.safe_load((pkg / "assurance_graph.yaml").read_text())
    c0 = graph["claims"][0]
    ok &= c0["formal"] == "(>= vaultBal totalAssets)" and c0["verdict"] == "proven"
    ok &= graph["claims"][1]["verdict"] == "refuted"
    led = yaml.safe_load((pkg / "trusted" / "ledger.yaml").read_text())
    ok &= led["lean_theorems"][0]["theorem_name"] == "Erc20.transfer_pair_sum_preserved"
    ok &= led["lean_theorems"][0]["build_status"] == "ok"

    print("\n" + ("ALL PASS" if ok else "FAILED"))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
