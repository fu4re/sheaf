"""Vacuity gate — a 'proved' can be EMPTY. Probe R always; Probe M opt-in.

A proof holds VACUOUSLY when the asserted point is unreachable (antecedent
failure) or a component of the invariant carries no load. This gate (Finding
0005) catches both — the SOLVER is the judge, zero LLM.

Two probes with different reach:
  Probe R (reachability, CHC-only): runs on ANY contract immediately. assert(false)
    PROVED ⇒ the point is unreachable ⇒ the proof is vacuous ⇒ FLAG. Refuted ⇒
    reachable ⇒ PASS. (CHC-only: BMC reports spurious violations on dead points.)
  Probe M (load-bearing, engine matched to quantifier): needs an ADVERSARY FAMILY
    to weaken-and-re-discharge against. There is NO automatic family for an
    arbitrary user contract (an open T1 subtask), so without --family the
    load-bearing dimension is M_UNASSESSED — honestly "not certified", NOT PASS.
    Absence of a family can never produce a false green.

Verdict → exit:  PASS=0 · M_UNASSESSED/BLOCKED=2 · FLAG=3. A FLAG/BLOCKED/
M_UNASSESSED feeds the two-tier predicate (Task 0008) and blocks green.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from tcg import outcome as oc
from tcg import phi as phi_mod
from tcg import runs
from tcg.outcome import Exit

CYCLE = runs.REPO / "cycle"
if str(CYCLE) not in sys.path:
    sys.path.insert(0, str(CYCLE))

from gateway.translator import _strip_header  # noqa: E402
from measurement.vacuity import reachability_probe, vacuity_gate  # noqa: E402

# standalone-command exit per gate verdict
_EXIT = {"PASS": int(Exit.GREEN), "FLAG": int(Exit.DEFECT),
         "BLOCKED": int(Exit.UNKNOWN), "M_UNASSESSED": int(Exit.UNKNOWN)}


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _build_reach_template(contract_path: Path, name: str, post_expr: str, out_dir: Path) -> Path:
    """A subclass harness whose view asserts the invariant, tagged __INVARIANT__ so
    reachability_probe can substitute `false` and ask CHC whether the point is reachable."""
    body = _strip_header(contract_path.read_text())
    src = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{body}

contract __ReachHarness is {name} {{
    function __check_invariant() public view {{
        assert({post_expr}); // __INVARIANT__ (reachability probe injects false)
    }}
}}
"""
    out_dir.mkdir(parents=True, exist_ok=True)
    p = out_dir / f"{name}__reach_template.sol"
    p.write_text(src)
    return p


def _load_family(path: Path) -> dict:
    m = yaml.safe_load(path.read_text())

    def ct(d: dict) -> tuple[Path, str]:
        t = Path(d["template"])
        if not t.is_absolute():
            t = CYCLE / t
        return (t, d["contract"])

    return {
        "name": m.get("name", path.stem),
        "invariant": m["invariant"],
        "engines": tuple(m.get("engines", ["chc"])),
        "reach_target": ct(m["reach_target"]),
        "members": {label: ct(d) for label, d in m["members"].items()},
    }


def _gate_outcome(run_dir: Path, phi: dict, vac_verdict: str) -> None:
    """Re-derive outcome.json with the vacuity verdict folded in (gates acceptance)."""
    check_path = run_dir / "check.json"
    if not check_path.exists():
        return
    c = json.loads(check_path.read_text())
    k = oc.KResult(c["k_result"], reason=c.get("reason"), witness=c.get("witness"),
                   certificate=c.get("certificate"))
    outcome = oc.two_tier_outcome(
        k=k, vacuity=vac_verdict,
        phi_checked=phi_mod.phi_checked(phi), phi_context=phi_mod.phi_context(phi),
        bytecode_identity="unverified", lint="not_run",
    )
    proc_exit = outcome.exit_code if k.is_accept else k.gate_exit
    out = {
        "schema": "tcg/outcome/v1", "stage": "vacuity",
        "contract": phi["contract"], "method": phi["method"],
        "k_result": k.kind, "vacuity": vac_verdict,
        "terminal": outcome.label, "terminal_exit": outcome.exit_code,
        "process_exit": proc_exit, "verified": outcome.verified,
        "phi_checked": phi_mod.phi_checked(phi), "phi_context": phi_mod.phi_context(phi),
        "bytecode_identity": "unverified",
        "reasons": outcome.reasons, "open_dischargeable": outcome.open_dischargeable,
        "assumed_irreducible": outcome.assumed_irreducible, "pending_gates": outcome.pending_gates,
        "claim_scope": outcome.claim_scope,
    }
    (run_dir / "outcome.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))


def run(args) -> int:
    build_dir = runs.TCG_RUNS / "vacuity_build"
    run_dir = None
    phi = None
    probe_R = None

    # ---------- determine reachability target & run Probe R --------------------
    if args.template:
        if not args.contract:
            _log("error: --template requires --contract")
            return int(Exit.USAGE)
        probe_R = reachability_probe(runs.resolve(args.template), args.contract, tag=args.contract)
    elif args.run_dir:
        run_dir = runs.resolve(args.run_dir)
        frozen = run_dir / "phi.frozen.yaml"
        if not frozen.exists():
            _log(f"error: no frozen φ in {run_dir} — run `tcg validate --approve` first")
            return int(Exit.USAGE)
        phi = phi_mod.load(frozen)
        ok, *_ = phi_mod.verify_frozen(phi)
        if not ok:
            _log("refuse: φ freeze hash mismatch (Inv.6) — vacuity not run")
            return int(Exit.USAGE)
        reach_tmpl = _build_reach_template(
            run_dir / "contract.sol", phi["contract"],
            phi["spec"]["post"][0]["solidity_expr"], build_dir)
        probe_R = reachability_probe(reach_tmpl, phi["contract"], tag=phi["contract"])
    elif not args.family:
        _log("error: need --run-dir, or --template+--contract, or --family")
        return int(Exit.USAGE)

    # ---------- Probe M (opt-in via --family) ----------------------------------
    family_gate = None
    if args.family:
        fam = _load_family(runs.resolve(args.family))
        family_gate = vacuity_gate(fam["reach_target"], fam["members"], fam["invariant"],
                                   tag=fam["name"], engines=fam["engines"])
        # The family gate's own verdict (it runs R on the family's reach_target + M).
        vac_verdict = family_gate["verdict"]  # PASS | FLAG | BLOCKED
    else:
        R = probe_R["result"]  # PASS | FLAG | UNKNOWN
        if args.reachability_only:
            vac_verdict = {"PASS": "PASS", "FLAG": "FLAG", "UNKNOWN": "BLOCKED"}[R]
        elif R == "FLAG":
            vac_verdict = "FLAG"
        elif R == "UNKNOWN":
            vac_verdict = "BLOCKED"
        else:  # R PASS, no family ⇒ load-bearing not assessed (honest, not PASS)
            vac_verdict = "M_UNASSESSED"

    # ---------- vacuity.json ---------------------------------------------------
    vacuity_json = {
        "schema": "tcg/vacuity/v1",
        "verdict": vac_verdict,
        "mode": ("family" if args.family else
                 "reachability_only" if args.reachability_only else "no_family"),
        "probe_R": probe_R,
        "probe_M": ("not assessed — no --family (load-bearing dimension)" if not args.family
                    else "see family_gate.probe_M"),
        "family_gate": family_gate,
        "judge": "solver (SMTChecker — CHC for Probe R; per-family engines for Probe M, z3) — zero LLM",
    }
    if run_dir:
        out_path = run_dir / "vacuity.json"
    elif args.out:
        out_path = runs.resolve(args.out)
    else:
        out_path = (runs.resolve(args.family).parent if args.family else Path.cwd()) / "vacuity.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(vacuity_json, indent=2, ensure_ascii=False))

    # ---------- gate acceptance (re-derive outcome.json) -----------------------
    if run_dir and phi is not None:
        _gate_outcome(run_dir, phi, vac_verdict)

    # ---------- report ---------------------------------------------------------
    icon = {"PASS": "✅", "FLAG": "❌", "BLOCKED": "🚫", "M_UNASSESSED": "🚧"}
    print(f"\n  tcg vacuity — {vacuity_json['mode']} mode")
    if probe_R:
        print(f"  Probe R (reachability): {probe_R['result']} ({probe_R['solver_verdict']})"
              + (f" — {probe_R.get('reason')}" if probe_R.get('reason') else ""))
    if family_gate:
        b = family_gate["probe_M"]["base"]
        print(f"  Probe M (family {Path(args.family).stem}): {family_gate['verdict']}")
        for why in family_gate["flag_reasons"]:
            print(f"    FLAG : {why}")
        for why in family_gate["blocked_reasons"]:
            print(f"    BLOCK: {why}")
        print(f"    honest={b['honest']} refuted={b['refuted_adversaries']} "
              f"blind={b['blind_spots']} undecided={b['undecided']}")
    elif not args.reachability_only and not args.template:
        print("  Probe M (load-bearing): M_UNASSESSED — no --family; absence cannot green")
    print(f"  {icon.get(vac_verdict, '?')} verdict: {vac_verdict}")
    if run_dir:
        print(f"  gated outcome.json (stage=vacuity)")
    print(f"  artifact: {runs.disp(out_path)}")
    print(f"  exit {_EXIT[vac_verdict]}\n")
    return _EXIT[vac_verdict]
