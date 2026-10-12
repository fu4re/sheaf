"""K — the Checker (TRUSTED-formal). The sole acceptance gate (Inv.1).

`check` is the only command that runs the solver against the SUT. It:
  1. RE-CHECKS the frozen φ hash and refuses on mismatch / not-frozen — without
     running the solver (Inv.6: nobody may weaken the spec being checked).
  2. RE-PINS the checker parameters from the freeze block and refuses if the
     running solc differs from the pinned one (Inv.9).
  3. Injects Post → `assert`, applies the pinned engine / targets / ext-calls
     (Trace → --model-checker-ext-calls), runs the solver, and classifies the
     verdict into Accept | Refute | Unknown | gateway-reject.
  4. Decides the terminal via the two-tier predicate. Accept ≠ green: at source
     level the bytecode-identity leaf is open and φ_context is non-empty, so the
     honest terminal is ⊥_assumptions_open — NOT green. A Refute is ⊥_gen.

The `check` process exit is the K-GATE code (Refute→3, Unknown→2 — these must
never share a code, Inv.4/5; Accept→the two-tier ceiling, 6 at source level).
outcome.json additionally records the ⊥_gen terminal the sequencer (`tcg run`)
emits for a Refute/Unknown.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict
from pathlib import Path

from tcg import outcome as oc
from tcg import phi as phi_mod
from tcg import runs
from tcg.outcome import Exit

CYCLE = runs.REPO / "cycle"
if str(CYCLE) not in sys.path:
    sys.path.insert(0, str(CYCLE))

from gateway.translator import build_harness, validate_compiles  # noqa: E402
from trusted.solver import run_solver, solc_version  # noqa: E402


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def run(args) -> int:
    run_dir = runs.resolve(args.run_dir)
    frozen_path = run_dir / "phi.frozen.yaml"
    contract_path = run_dir / "contract.sol"

    # --- (1) hash-recheck: refuse on not-frozen / tamper BEFORE touching solver --
    if not frozen_path.exists():
        _log(f"refuse: no phi.frozen.yaml in {run_dir} — run `tcg validate --approve` first")
        return int(Exit.USAGE)
    phi = phi_mod.load(frozen_path)
    ok, expected, got = phi_mod.verify_frozen(phi)
    if not ok:
        _log("refuse: φ freeze hash mismatch (Inv.6) — spec tampered after H froze it. "
             "Solver NOT run.")
        _log(f"  expected {expected}\n  got      {got}")
        return int(Exit.USAGE)

    # --- (2) re-pin checker params; refuse if the judging compiler drifted -------
    cp = phi["freeze"]["checker_params"]
    cur_solc = solc_version()
    if cur_solc != cp["solc_version"]:
        _log(f"refuse: solc drift (Inv.9) — frozen {cp['solc_version']} vs running {cur_solc}. "
             f"Re-freeze under the running toolchain or restore the pinned solc.")
        return int(Exit.USAGE)
    engine = cp.get("engine", "chc")
    targets = tuple(cp.get("targets", ["assert"]))
    ext_calls = cp.get("ext_calls")
    timeout_ms = cp.get("model_checker_timeout_ms", 20000)

    # --- (3) build harness (Post → assert), run the pinned solver ---------------
    post = phi["spec"]["post"][0]
    post_expr = post["solidity_expr"]
    build_dir = run_dir / "build"
    harness = build_harness(contract_path, phi["contract"], post_expr, build_dir)
    compiles, errors, _ = validate_compiles(harness)
    if not compiles:
        verdict = {"verdict": "compile_error", "reason": "; ".join(errors)[:500],
                   "command": None}
    else:
        v = run_solver(harness, engine=engine, targets=targets, ext_calls=ext_calls,
                       model_checker_timeout_ms=timeout_ms)
        verdict = asdict(v)
        # absolute, so the package assembler can copy it regardless of where the run
        # dir lives (a developer's project, not necessarily under the tool's REPO).
        verdict["_harness"] = str(harness.resolve())

    k = oc.classify(verdict)

    # --- check.json -------------------------------------------------------------
    check_json = {
        "schema": "tcg/check/v1",
        "contract": phi["contract"], "method": phi["method"],
        "phi_hash": expected,
        "phi_hash_reconfirmed": True,
        "checker_params_used": {
            "solc_version": cur_solc, "engine": engine, "targets": list(targets),
            "ext_calls": ext_calls, "model_checker_timeout_ms": timeout_ms,
            "solvers": cp.get("solvers", ["z3"]),
        },
        "post_invariant": post_expr,
        "k_result": k.kind,
        "k_gate_exit": k.gate_exit if not k.is_accept else None,
        "reason": k.reason,
        "witness": k.witness,            # only populated for refute (Inv.5)
        "certificate": k.certificate,    # only populated for accept
        "solver_verdict": verdict.get("verdict"),
        "harness": verdict.get("_harness"),
        "command": verdict.get("command"),
    }
    (run_dir / "check.json").write_text(json.dumps(check_json, indent=2, ensure_ascii=False))

    # --- two-tier terminal: at check stage vacuity & lint are pending -----------
    # bytecode-identity is always 'unverified' at source level (MVP) → DISCHARGEABLE
    # leaf open → Accept can only reach ⊥_assumptions_open, never green.
    outcome = oc.two_tier_outcome(
        k=k, vacuity="not_run",
        phi_checked=phi_mod.phi_checked(phi), phi_context=phi_mod.phi_context(phi),
        bytecode_identity="unverified", lint="not_run",
    )

    proc_exit = outcome.exit_code if k.is_accept else k.gate_exit

    outcome_json = {
        "schema": "tcg/outcome/v1",
        "stage": "check",
        "contract": phi["contract"], "method": phi["method"],
        "k_result": k.kind,
        "k_gate_exit": None if k.is_accept else k.gate_exit,
        "terminal": outcome.label,
        "terminal_exit": outcome.exit_code,
        "process_exit": proc_exit,
        "verified": outcome.verified,
        "witness": k.witness,
        "phi_checked": phi_mod.phi_checked(phi),
        "phi_context": phi_mod.phi_context(phi),
        "bytecode_identity": "unverified",
        "reasons": outcome.reasons,
        "open_dischargeable": outcome.open_dischargeable,
        "assumed_irreducible": outcome.assumed_irreducible,
        "pending_gates": outcome.pending_gates,
        "claim_scope": outcome.claim_scope,
        "note": "check exits the K-gate code (refute=3 / unknown=2 / accept-ceiling=6); "
                "for a refute/unknown, `tcg run` emits the ⊥_gen loop terminal (exit 5). "
                "Pending gates (vacuity, lint) can only constrain further, never relax.",
    }
    (run_dir / "outcome.json").write_text(json.dumps(outcome_json, indent=2, ensure_ascii=False))

    # --- report -----------------------------------------------------------------
    print(f"\n  tcg check — K gate (the sole acceptance gate)")
    print(f"  contract   : {phi['contract']}.{phi['method']}")
    print(f"  post (assert): {post_expr}")
    print(f"  pinned     : solc {cur_solc.split('+')[0]} · {engine} · targets={list(targets)} · ext-calls={ext_calls}")
    print(f"  K result   : {k.kind.upper()}" + (f"  witness={k.witness.get('assignments') if k.witness else None}" if k.kind == 'refute' else ""))
    print(f"  terminal   : {outcome.label}  (terminal exit {outcome.exit_code})")
    if outcome.open_dischargeable:
        print(f"  open leaves: {outcome.open_dischargeable}  ← cap below green (DISCHARGEABLE)")
    if outcome.pending_gates:
        print(f"  pending    : {outcome.pending_gates}")
    print(f"  claim scope: {outcome.claim_scope}")
    print(f"  process exit {proc_exit} — {oc.EXIT_MEANING.get(Exit(proc_exit), '')}")
    print(f"  artifacts  : {runs.disp(run_dir / 'check.json')}, "
          f"{runs.disp(run_dir / 'outcome.json')}\n")
    return int(proc_exit)
