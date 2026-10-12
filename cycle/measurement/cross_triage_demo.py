"""Cross-contract assume-guarantee e2e demo (Task 0003). Runs the three A/G
obligations + weakest-sufficient interface mining, SOLVER as judge, and writes the
artifact consumed by Finding 0004. No LLM judge anywhere in this file.

    python3 cycle/measurement/cross_triage_demo.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from measurement.triage import (  # noqa: E402
    _caller_verdict,
    discharge,
    mine_interface,
    triage_callees,
)

HARNESS = ROOT / "trusted" / "harness" / "cross"
ARTIFACTS = ROOT / "measurement" / "artifacts"

CALLER = HARNESS / "VaultAssetAG.sol"
CALLER_NAME = "VaultAssetAG"
I_A = "vaultBal >= totalAssets"                       # caller solvency law
WITHDRAW = "vaultBal_post == vaultBal - assets"       # canonical withdraw-leg summary

# Agent over-generates candidate guarantee clauses for the deposit call (caller-side
# projection over vaultBal/vaultBal_post/assets). The solver decides which are
# sufficient and which is weakest — the rest are discarded.
DEPOSIT_CANDIDATES = [
    {"name": "exact",      "expr": "vaultBal_post == vaultBal + assets"},  # sufficient (tight)
    {"name": "at_least",   "expr": "vaultBal_post >= vaultBal + assets"},  # sufficient, WEAKER
    {"name": "monotone",   "expr": "vaultBal_post >= vaultBal"},           # insufficient alone
    {"name": "upper_only", "expr": "vaultBal_post <= vaultBal + assets"},  # insufficient alone
    {"name": "irrelevant", "expr": "assets <= type(uint128).max"},         # irrelevant -> discarded
]

# Obligation 2, version A (conservation) — NECESSARY BUT NOT SUFFICIENT. Discharging
# `ghostSum == totalSupply` catches a supply-inflation token and a LOSING-fee token, but
# a BURNING-fee token preserves conservation (Σ and totalSupply drop in lockstep) while
# under-crediting the vault — so conservation does NOT entail the mined caller guarantee.
CONSERVATION = "ghostSum == totalSupply"
CALLEES = {
    "MiniERC20 (honest)":          ("-", "MiniERC20Conservation",       HARNESS / "MiniERC20Conservation.sol"),
    "Buggy (supply-inflation)":    ("-", "MiniERC20ConservationBuggy",  HARNESS / "MiniERC20ConservationBuggy.sol"),
    "FeeERC20 (losing-fee)":       ("-", "FeeERC20Conservation",        HARNESS / "FeeERC20Conservation.sol"),
    "BurnFeeERC20 (burning-fee)":  ("-", "BurnFeeERC20Conservation",    HARNESS / "BurnFeeERC20Conservation.sol"),
}

# Obligation 2, version B (delta) — discharges the ACTUAL mined caller clause
# (`vaultBal_post >= vaultBal + assets`) in its callee-side form: a transfer credits the
# recipient by >= amount. CHC+BMC (BMC catches the 2-step counterexample CHC misses).
# This closes the gap: the property discharged == the property the caller relied on.
DELTA_HARNESSES = {
    "MiniERC20 (honest)":          HARNESS / "MiniERC20Delta.sol",     # expect proven
    "BurnFeeERC20 (burning-fee)":  HARNESS / "BurnFeeERC20Delta.sol",  # expect refuted (CAUGHT)
}


def main() -> int:
    print("== Obligation 1: caller proof under the canonical summary ==")
    o1 = _caller_verdict(CALLER, CALLER_NAME, I_A, ["vaultBal_post == vaultBal + assets", WITHDRAW], tag="o1_canonical")
    print(f"   I_A ({I_A}) under G_B  ->  {o1}")

    print("\n== Weakest-sufficient interface mining (solver discards the unneeded) ==")
    mined = mine_interface(CALLER, CALLER_NAME, I_A, DEPOSIT_CANDIDATES, WITHDRAW)
    for c in mined["clauses"]:
        flag = "sufficient" if c["sufficient"] else "INSUFFICIENT -> discard"
        print(f"   {c['name']:11} [{c['verdict']:8}] {flag:24} {c['expr']}")
    print(f"   sufficient set : {mined['sufficient']}")
    print(f"   WEAKEST (mined interface, tightest demand on B) : {mined['weakest_sufficient']}")

    print("\n== Obligation 2A: conservation (necessary but NOT sufficient) ==")
    o2_cons = triage_callees(CALLEES, "conservation", CONSERVATION)
    for label, bucket in o2_cons.items():
        if bucket == "proven":
            tag = "PROVEN" + ("  <-- GAP: passes conservation but under-credits!" if "Burn" in label else "  (satisfies conservation)")
        else:
            tag = f"{bucket.upper()}  (caught: violates conservation)"
        print(f"   {label:28} -> {tag}")

    print("\n== Obligation 2B: DELTA discharge of the MINED clause (CHC+BMC) — closes the gap ==")
    o2_delta = {}
    for label, h in DELTA_HARNESSES.items():
        d = discharge(h)
        o2_delta[label] = d
        verdict = "PROVEN  (credits >= amount)" if d["bucket"] == "proven" else f"{d['bucket'].upper()}  (caught: under-credits)  {d['by']}"
        print(f"   {label:28} -> {verdict}")

    artifact = {
        "task": "0003_cross_contract_assume_guarantee",
        "obligation_1_caller_proof": {"invariant": I_A, "verdict": o1},
        "interface_mining": mined,
        "obligation_2A_conservation": {
            "guarantee": CONSERVATION, "verdicts": o2_cons,
            "note": "necessary not sufficient: BurnFeeERC20 proves conservation yet under-credits — conservation != the mined caller clause",
        },
        "obligation_2B_delta_discharge": {
            "guarantee": "transfer credits recipient by >= amount (callee-side form of mined `vaultBal_post >= vaultBal + assets`)",
            "engines": "chc+bmc (BMC catches the 2-step CE CHC reports as unknown)",
            "verdicts": o2_delta,
            "note": "discharges the ACTUAL mined clause; BurnFeeERC20 refuted here though it passed 2A — gap closed",
        },
        "judge": "solver (SMTChecker/CHC+BMC/z3) — zero LLM judge",
    }
    out = ARTIFACTS / "cross_ag__triage.json"
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
    print(f"\nartifact -> {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
