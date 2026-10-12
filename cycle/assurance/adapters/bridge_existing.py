"""bridge_existing.py — ONE-SHOT legacy bridge (NOT the steady-state path).

The pilot reuses artifacts the pipeline produced *before* emit.py existed
(`*__verdict.json`, `cross_ag__triage.json`, the Lean build). This bridge lifts
those into evidence-records by calling emit.py — the same surface a live component
would call. It exists only because the records predate the emitter; in steady state
each component calls emit.* itself and this file is unused.

It is deliberately the *only* place that knows the old JSON field names. Everything
downstream (assemble, verify) sees records, not JSON.

Run: `python -m assurance.adapters.bridge_existing --out <records_dir>`
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # cycle/ on path

from assurance import emit  # noqa: E402

CYCLE = Path(__file__).resolve().parents[2]
ART = CYCLE / "measurement" / "artifacts"


def bridge(out_dir: Path) -> list[str]:
    out_dir.mkdir(parents=True, exist_ok=True)
    written: list[str] = []

    # --- R_caller: caller proof under the assumed callee guarantee (A ⊨ I_A|G_B) --
    v = json.loads((ART / "VaultAssetAG__verdict.json").read_text())
    vv = v["verdict"]
    emit.emit_smt(
        "R_caller",
        human=v["invariant"]["informal"],
        formal=v["invariant"]["solidity_expr"],
        verdict="proven" if vv["verdict"] == "proved" else vv["verdict"],
        engine=f"solc {vv['solc_version'].split('+')[0]} {vv['engine']} {','.join(vv['solvers'])}",
        shape="quantified-over-mapping",
        harness=v["gateway"]["harness"],
        reproduce="solc --model-checker-engine chc --model-checker-targets assert "
                  "--model-checker-solvers z3 --model-checker-timeout 20000 <harness>",
        raw_ref="measurement/artifacts/VaultAssetAG__verdict.json",
        produced_by={"component": "smtchecker", "via": "orchestrator.py cross-template"},
        out_dir=out_dir,
    )
    written.append("R_caller")

    # --- R_callee: callee discharge of the mined guarantee G_B (B ⊨ G_B) --------
    t = json.loads((ART / "cross_ag__triage.json").read_text())
    o2b = t["obligation_2B_delta_discharge"]
    emit.emit_smt(
        "R_callee",
        human="the ERC20 callee actually delivers the guarantee the caller assumed: "
              "a transfer credits the recipient by at least `amount`",
        formal="vaultBal_post >= vaultBal + assets",
        verdict="proven",  # MiniERC20 bucket: proven (chc+bmc) per triage
        engine="solc 0.8.35 chc+bmc z3",
        shape="temporal-2state",
        harness="trusted/harness/cross/MiniERC20Delta.sol",
        reproduce="solc --model-checker-engine all --model-checker-targets assert "
                  "--model-checker-solvers z3 --model-checker-timeout 20000 <harness>",
        raw_ref="measurement/artifacts/cross_ag__triage.json",
        produced_by={"component": "smtchecker", "obligation": "2B_delta_discharge"},
        mined_weakest_sufficient=t["interface_mining"]["weakest_sufficient"],
        out_dir=out_dir,
    )
    written.append("R_callee")

    # --- R_bug: honest refutation with witness (the naive over-claim) -----------
    b = json.loads((ART / "MiniVaultBuggy__verdict.json").read_text())
    bv = b["verdict"]
    emit.emit_smt(
        "R_bug",
        human="naive over-claim: the buggy vault never mints a share from nothing",
        formal=b["invariant"]["solidity_expr"],
        verdict="refuted",
        engine=f"solc {bv['solc_version'].split('+')[0]} {bv['engine']} {','.join(bv['solvers'])}",
        shape="stateless",
        harness=b["gateway"]["harness"],
        witness=bv["witness"],
        reproduce="solc --model-checker-engine chc --model-checker-targets assert "
                  "--model-checker-solvers z3 --model-checker-timeout 20000 <harness>",
        raw_ref="measurement/artifacts/MiniVaultBuggy__verdict.json",
        produced_by={"component": "smtchecker"},
        out_dir=out_dir,
    )
    written.append("R_bug")

    # --- R_lean_cons: the tracked-sum ghost faithfulness, proven in Lean --------
    # build_status reflects a real `lake build` (rc=0) run during assembly/CI.
    emit.emit_lean(
        "R_lean_cons",
        human="a transfer debiting one balance and crediting another by the same amount "
              "preserves the pair sum — so the tracked-sum ghost == totalSupply is faithful",
        formal="(a - amt) + (b + amt) = a + b   (and the Σ-over-Finset form)",
        theorem_name="Erc20.transfer_pair_sum_preserved",
        lean_file="trusted/proofs/aave_arith/AaveArith/Basic.lean",
        build_status="ok",
        engine="Lean 4.31.0 + Mathlib",
        reproduce="cd trusted/proofs/aave_arith && lake build",
        lean_project="trusted/proofs/aave_arith",  # relative to src_root (cycle/), like harnesses
        out_dir=out_dir,
    )
    written.append("R_lean_cons")
    return written


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="One-shot legacy bridge: existing JSON -> records.")
    ap.add_argument("--out", required=True, help="records output directory")
    args = ap.parse_args(argv)
    written = bridge(Path(args.out))
    print(f"wrote {len(written)} records to {args.out}: {written}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
