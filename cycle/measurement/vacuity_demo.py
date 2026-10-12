"""Vacuity-gate e2e demo (Task T1). The SOLVER is the judge; ZERO LLM anywhere.

Runs the two probes over the current cross-contract experiment:
  Probe R (reachability, CHC) over the 2 deliberately-vacuous fixtures (must FLAG) and
    the live callee harnesses (must PASS);
  Probe M (load-bearing, CHC+BMC) over the conservation family and the delta family —
    which AUTO-REDISCOVERS the conservation≠delta gap (conservation is blind to the
    burning-fee callee; delta is not), the gap we found by hand under review last session.

    python3 -m cycle.measurement.vacuity_demo
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gateway.translator import build_from_harness  # noqa: E402
from measurement.vacuity import BUILD, reachability_probe, vacuity_gate  # noqa: E402
from trusted.solver import run_solver  # noqa: E402

HARNESS = ROOT / "trusted" / "harness" / "cross"
ARTIFACTS = ROOT / "measurement" / "artifacts"


def _bmc_spurious_evidence(reach, invariant):
    """Capture the witness that justifies the per-family engine policy: BMC SPURIOUSLY
    'refutes' the honest reachable-state invariant from a constructor-unreachable free
    state, while CHC correctly proves it. Retained in the report (claim ledger), not prose."""
    h = build_from_harness(reach[0], reach[1], invariant, BUILD, tag="evidence_bmc_spurious")
    chc, bmc = run_solver(h, engine="chc"), run_solver(h, engine="bmc")
    return {
        "harness": f"{reach[1]} (honest)", "invariant": invariant,
        "CHC": chc.verdict, "BMC": bmc.verdict,
        "BMC_witness": bmc.witness, "BMC_reason": bmc.reason,
        "reading": "CHC=proved (sound) vs BMC=counterexample (SPURIOUS — free state unreachable "
                   "from constructor) ⇒ BMC unsound on a reachable-state invariant",
    }


def _ct(name):  # (template_path, contract_name)
    return (HARNESS / f"{name}.sol", name)


# --- the conservation family: invariant `ghostSum == totalSupply`, in __check() view ---
CONSERVATION_INV = "ghostSum == totalSupply"
CONSERVATION_REACH = _ct("MiniERC20Conservation")
CONSERVATION_FAMILY = {
    "honest:MiniERC20":   _ct("MiniERC20Conservation"),
    "adv:SupplyInflation": _ct("MiniERC20ConservationBuggy"),
    "adv:LosingFee":       _ct("FeeERC20Conservation"),
    "adv:BurnFee":         _ct("BurnFeeERC20Conservation"),  # the GAP: conservation holds
}

# --- the delta family: invariant `balanceOf[to] >= beforeTo + amount`, inline in transfer ---
DELTA_INV = "balanceOf[to] >= beforeTo + amount"
DELTA_REACH = _ct("MiniERC20Delta")
DELTA_FAMILY = {
    "honest:MiniERC20": _ct("MiniERC20Delta"),
    "adv:BurnFee":      _ct("BurnFeeERC20Delta"),  # delta CATCHES what conservation missed
}

# --- the deliberately-vacuous fixtures: Probe R must FLAG both ---
FIXTURES = {
    "VaultAssetAGDead (require(false))":          _ct("VaultAssetAGDead"),
    "MiniERC20NoMintConservation (dead underflow)": _ct("MiniERC20NoMintConservation"),
}

# live single-assert callee harnesses — Probe R must find them all reachable (PASS)
LIVE = {
    "MiniERC20Conservation":        CONSERVATION_REACH,
    "MiniERC20ConservationBuggy":   _ct("MiniERC20ConservationBuggy"),
    "FeeERC20Conservation":         _ct("FeeERC20Conservation"),
    "BurnFeeERC20Conservation":     _ct("BurnFeeERC20Conservation"),
    "MiniERC20Delta":               DELTA_REACH,
    "BurnFeeERC20Delta":            _ct("BurnFeeERC20Delta"),
}


def main() -> int:
    print("== Probe R — reachability / antecedent failure (CHC-only) ==")
    print("   the 2 deliberately-vacuous fixtures MUST FLAG; live harnesses MUST PASS\n")
    r_fixtures, r_live = {}, {}
    for label, (tmpl, contract) in FIXTURES.items():
        res = reachability_probe(tmpl, contract, tag=f"fix_{contract}")
        r_fixtures[label] = res
        print(f"   FIXTURE {label:46} -> {res['result']:4} ({res['solver_verdict']})")
    print()
    for label, (tmpl, contract) in LIVE.items():
        res = reachability_probe(tmpl, contract, tag=f"live_{contract}")
        r_live[label] = res
        print(f"   live    {label:46} -> {res['result']:7} ({res['solver_verdict']})")
    print("   note: UNKNOWN on BurnFeeERC20Delta is immaterial — it is an ADVERSARY whose")
    print("         reachability is self-certified by its Probe-M refutation (a refuting")
    print("         trace reaches the assert). Probe R matters for harnesses we expect to PROVE.")

    print("\n== Probe M — load-bearing gate. conservation (CHC) vs delta (CHC+BMC) ==")
    print("   engine matched to invariant kind: conservation is a REACHABLE-STATE invariant")
    print("   (BMC spurious — free-state CE); delta is a 2-STATE Hoare property (BMC needed)\n")
    # conservation: reachable-state invariant -> CHC-only (BMC yields spurious free-state CEs)
    cons = vacuity_gate(CONSERVATION_REACH, CONSERVATION_FAMILY, CONSERVATION_INV,
                        tag="conservation", engines=("chc",))
    # delta: 2-state Hoare property -> CHC+BMC (CHC reports under-credit as inconclusive)
    delta = vacuity_gate(DELTA_REACH, DELTA_FAMILY, DELTA_INV,
                         tag="delta", engines=("chc", "bmc"))

    for g in (cons, delta):
        b = g["probe_M"]["base"]
        print(f"   invariant: {g['invariant']}   [engines: {g['engines']}]")
        print(f"     verdict: {g['verdict']}")
        for why in g["flag_reasons"]:
            print(f"       FLAG : {why}")
        for why in g["blocked_reasons"]:
            print(f"      BLOCK : {why}")
        print(f"     honest: {b['honest']}  refuted: {b['refuted_adversaries']}  "
              f"blind(proved): {b['blind_spots']}  undecided: {b['undecided']}")
        print("     component mutation profile (M2 — which component defends against which adversary):")
        for m in g["probe_M"]["mutations"]:
            tail = f"refutes={m['refuted_adversaries']}"
            if m["lost_to_blind"]:
                tail += f"  lost→blind={m['lost_to_blind']}"
            if m["lost_to_undecided"]:
                tail += f"  lost→undecided={m['lost_to_undecided']}"
            print(f"       [{m['classification']:13}] {m['mutation']:18} {m['weakens']:28} {tail}")
        print()

    # the headline: did Probe M auto-rediscover conservation≠delta?
    cons_blind = cons["probe_M"]["base"]["blind_spots"]
    delta_blind = delta["probe_M"]["base"]["blind_spots"]
    rediscovered = bool(cons_blind) and not delta_blind
    print("== Headline ==")
    print(f"   conservation blind spots : {cons_blind}  -> {cons['verdict']}")
    print(f"   delta        blind spots : {delta_blind}  -> {delta['verdict']}")
    print(f"   conservation≠delta gap auto-rediscovered by the gate: {rediscovered}")

    # evidence for the engine policy (claim ledger): the BMC-spurious witness, retained
    evidence = _bmc_spurious_evidence(CONSERVATION_REACH, CONSERVATION_INV)
    print(f"\n== Evidence: BMC-spurious on honest conservation (justifies CHC-only) ==")
    print(f"   CHC={evidence['CHC']}  BMC={evidence['BMC']}  BMC_witness={evidence['BMC_witness']['assignments'] if evidence['BMC_witness'] else None}")

    # ---- ACCEPTANCE CHECK: lock the result; NON-ZERO exit on any regression ----
    delta_muts = delta["probe_M"]["mutations"]
    honest_live = ["MiniERC20Conservation", "MiniERC20ConservationBuggy", "FeeERC20Conservation",
                   "BurnFeeERC20Conservation", "MiniERC20Delta"]
    checks = {
        "both fixtures FLAG (Probe R)": all(v["result"] == "FLAG" for v in r_fixtures.values()),
        "honest+conservation live reachable (PASS)": all(r_live[k]["result"] == "PASS" for k in honest_live),
        "conservation gate FLAG, blind=[BurnFee]": cons["verdict"] == "FLAG" and cons_blind == ["adv:BurnFee"],
        "delta gate PASS, no blind": delta["verdict"] == "PASS" and delta_blind == [],
        "honest proves on both families": cons["honest"].get("honest:MiniERC20") == "proven"
                                          and delta["honest"].get("honest:MiniERC20") == "proven",
        "gap auto-rediscovered": rediscovered is True,
        "delta M2 has load_bearing AND inert": (any(m["classification"] == "load_bearing" for m in delta_muts)
                                                and any(m["classification"] == "inert" for m in delta_muts)),
        "BMC spurious confirmed (CHC=proved, BMC=counterexample)": evidence["CHC"] == "proved"
                                                                   and evidence["BMC"] == "counterexample",
    }
    passed = all(checks.values())

    artifact = {
        "task": "T1_vacuity_gate",
        "layer": "trusted measurement layer next to the solver (NOT the agent)",
        "acceptance": {"passed": passed, "checks": checks},
        "engine_policy_evidence": evidence,
        "probe_R": {
            "policy": "CHC-only (BMC gives spurious violations on unreachable points — measured)",
            "fixtures_expected_FLAG": {k: v["result"] for k, v in r_fixtures.items()},
            "live_expected_PASS": {k: v["result"] for k, v in r_live.items()},
            "detail": {"fixtures": r_fixtures, "live": r_live},
        },
        "probe_M": {
            "policy": "engine matched to invariant quantification (declared per family)",
            "engine_rationale": {
                "conservation": "CHC-only — reachable-state invariant; BMC yields spurious "
                                "refutations from constructor-unreachable free states "
                                "(measured: honest conservation 'refuted' by BMC with "
                                "ghostSum=1,totalSupply=0, empty trace) — the dual of a vacuous proof",
                "delta": "CHC+BMC — 2-state Hoare property holding from any precondition-"
                         "satisfying entry; CHC reports the under-credit as inconclusive, BMC catches it",
            },
            "conservation_gate": cons,
            "delta_gate": delta,
        },
        "headline": {
            "conservation_blind_spots": cons_blind,
            "delta_blind_spots": delta_blind,
            "conservation_neq_delta_auto_rediscovered": rediscovered,
            "note": "conservation PROVES on the burning-fee callee (blind) while delta REFUTES it; "
                    "the gate flags conservation as a vacuous proxy and clears delta — the same gap "
                    "found by hand under review last session, now caught automatically.",
        },
        "judge": "solver (SMTChecker CHC[R] / CHC+BMC[M], z3) — zero LLM judge",
    }
    out = ARTIFACTS / "vacuity_report.json"
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
    print(f"\nartifact -> {out.relative_to(ROOT)}")

    print("\n== Acceptance check (non-zero exit on regression) ==")
    for name, ok in checks.items():
        print(f"   [{'OK  ' if ok else 'FAIL'}] {name}")
    print(f"\nACCEPTANCE: {'PASS' if passed else 'FAIL — gate regressed'}")
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
