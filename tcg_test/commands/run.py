"""tcg run — e2e sequencer: formalize → validate → check → vacuity → package.

PURE SEQUENCING. `run` introduces ZERO new gate logic — that would be a second
path to "accepted" past the K gate (Inv.1 violation). The only component that
decides a terminal is `outcome.py` (Task 0008), invoked inside check/vacuity; this
sequencer merely runs each stage, reads the `outcome.json` those stages wrote, and
stops at the first stage that produces a terminal ⊥. It NEVER imports the acceptance
predicate (`two_tier_outcome`/`classify`) — grep-checkable (DoD#6).

Stop-and-emit table (all decided upstream, read here):
  formalize abstains            → ⊥_spec        (exit 4)
  check refute/unknown          → ⊥_gen         (exit 5, witness handed to the human)
  vacuity FLAG / hard-BLOCKED    → vacuous/blocked (exit 3 / 2)
  all stages pass               → ⊥_assumptions_open (exit 6) — honest non-green at source

There is no autonomous --intent loop and no --k-max: G is external (a human re-vibes
on a refute). That loop is an explicit future seam (Finding 0006 negative zone).
"""
from __future__ import annotations

import json
import sys
from argparse import Namespace
from pathlib import Path

from tcg import runs
from tcg.commands import check, formalize, package, validate, vacuity
from tcg.outcome import EXIT_MEANING, Exit


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _read_outcome(run_dir: Path) -> dict:
    p = run_dir / "outcome.json"
    return json.loads(p.read_text()) if p.exists() else {}


def _stop(run_dir: Path, stage: str, terminal: str, exit_code: int, extra: str = "") -> int:
    print(f"\n  ⛔ run stopped at stage '{stage}' → {terminal}")
    if extra:
        print(f"     {extra}")
    print(f"  terminal: {terminal}  ·  exit {exit_code} — {EXIT_MEANING.get(Exit(exit_code), '')}")
    print(f"  run dir : {runs.disp(run_dir)}\n")
    return exit_code


def run(args) -> int:
    # --- workspace -------------------------------------------------------------
    if args.run_dir:
        run_dir = runs.resolve(args.run_dir)
        run_dir.mkdir(parents=True, exist_ok=True)
    else:
        run_dir = runs.new_run_dir(args.name)
    rel = runs.disp(run_dir)
    print(f"\n  tcg run — e2e gate over {args.name}.{args.method}  (run dir: {rel})")
    print("  pipeline: formalize → validate → check → vacuity → package\n")

    if not args.reviewer:
        _log("error: tcg run needs --reviewer (H freezes φ as part of the run — Assumption 7)")
        return int(Exit.USAGE)

    # --- [F] formalize ---------------------------------------------------------
    print("  [F] formalize …")
    rc = formalize.run(Namespace(
        contract=args.contract, name=args.name, method=args.method, model=args.model,
        spec_file=args.spec_file, intent=args.intent, run_dir=str(run_dir)))
    if rc == int(Exit.BOT_SPEC):
        return _stop(run_dir, "formalize", "⊥_spec", int(Exit.BOT_SPEC),
                     "F abstained — no parsable invariant; human supplies intent and re-runs")
    if rc != int(Exit.GREEN):
        return _stop(run_dir, "formalize", "error", rc)

    # --- [H] validate --approve (freeze φ) ------------------------------------
    print("  [H] validate --approve …")
    rc = validate.run(Namespace(
        run_dir=str(run_dir), approve=True, reject=False, verify=False,
        reviewer=args.reviewer, reason=None, intent_attestation=None,
        engine="chc", ext_calls="untrusted", targets="assert",
        evm_version="solc-default", timeout_ms=20000))
    if rc != int(Exit.GREEN):
        return _stop(run_dir, "validate", "⊥_spec", int(Exit.BOT_SPEC),
                     "H did not freeze φ")

    # --- [K] check -------------------------------------------------------------
    print("  [K] check …")
    check.run(Namespace(run_dir=str(run_dir)))
    oc = _read_outcome(run_dir)
    if oc.get("terminal") == "⊥_gen":
        wit = oc.get("witness")
        return _stop(run_dir, "check", "⊥_gen", int(oc.get("terminal_exit", Exit.BOT_GEN)),
                     f"K refuted/unknown — witness handed to human (G is external): "
                     f"{wit.get('assignments') if wit else oc.get('reasons')}")
    # accept → outcome is the ⊥_assumptions_open ceiling; continue.

    # --- vacuity ---------------------------------------------------------------
    print("  [vacuity] …")
    vacuity.run(Namespace(
        run_dir=str(run_dir), template=None, contract=None, family=args.family,
        reachability_only=False, out=None))
    oc = _read_outcome(run_dir)
    if oc.get("terminal") in ("vacuous_proof", "blocked"):
        return _stop(run_dir, "vacuity", oc["terminal"], int(oc.get("terminal_exit", Exit.DEFECT)),
                     "; ".join(oc.get("reasons", [])))
    # M_UNASSESSED / PASS → ⊥_assumptions_open ceiling; continue.

    # --- package ---------------------------------------------------------------
    print("  [package] …")
    prc = package.run(Namespace(run_dir=str(run_dir), lean_axioms=args.lean_axioms))
    if prc != int(Exit.GREEN):
        return _stop(run_dir, "package", "package-invalid", prc,
                     "assurance package did not lint WELL-FORMED")

    # --- terminal (decided upstream by outcome.py, read here) ------------------
    oc = _read_outcome(run_dir)
    terminal = oc.get("terminal", "⊥_assumptions_open")
    exit_code = int(oc.get("terminal_exit", Exit.BOT_ASSUMPTIONS_OPEN))
    print(f"\n  ✔ pipeline complete — terminal: {terminal}")
    print(f"  verified : {oc.get('verified')}   claim scope: {oc.get('claim_scope')}")
    if oc.get("open_dischargeable"):
        print(f"  open DISCHARGEABLE leaves (cap below green): {oc['open_dischargeable']}")
    print(f"  exit {exit_code} — {EXIT_MEANING.get(Exit(exit_code), '')}")
    print(f"  package  : {runs.disp(run_dir / 'package')}")
    print(f"  run dir  : {rel}\n")
    return exit_code
