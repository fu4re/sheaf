"""H — Human-oracle gate. Validates φ against intent and FREEZES it.

H is the one non-formal trusted role (ADR Assumption 7): a human attests that φ
captures the economic intent, then freezes φ. The freeze is the mechanism behind
Inv.6 (φ immutable after H) and Inv.9 (checker parameters pinned): a content hash
over the spec/coverage plus the pinned solver parameters is written into
`phi.frozen.yaml`, and every downstream command recomputes it and REFUSES on
mismatch. Without this, a generator (or a future autonomous loop) could quietly
weaken the very spec it is being checked against.

Modes:
  --approve --reviewer <who>   write phi.frozen.yaml (freeze block + checker_params)
  --reject                     ⊥_spec (H rejects the spec)
  --verify                     recompute the frozen hash; tamper ⇒ exit 3 (DEFECT)
  (no flag)                    render φ and exit 2 (nothing frozen)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

from tcg import phi as phi_mod
from tcg import runs
from tcg.outcome import Exit

CYCLE = runs.REPO / "cycle"
if str(CYCLE) not in sys.path:
    sys.path.insert(0, str(CYCLE))


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _render(phi: dict) -> None:
    print("\n  tcg validate — φ for human review (NOT frozen)")
    print(f"  contract: {phi.get('contract')}.{phi.get('method')}")
    sp = phi.get("spec", {})
    print("  Pre:")
    for g in sp.get("pre", []):
        print(f"    - {g['solidity_expr']}   [{g['checked_as']}]")
    print("  Trace:")
    for t in sp.get("trace", []):
        print(f"    - {t['id']} ({t.get('status')}) — {t.get('checked_as')}")
    print("  Post:")
    for p in sp.get("post", []):
        print(f"    - {p['solidity_expr']}   [{p['checked_as']}]")
    ex = sp.get("exit", {})
    print(f"  Exit: admissible={ex.get('admissible')} status={ex.get('status')}")
    print(f"  φ_checked: {phi_mod.phi_checked(phi)}")
    print(f"  φ_context: {phi_mod.phi_context(phi)}")
    print("  → review, then: --approve --reviewer <you>  |  --reject\n")


def run(args) -> int:
    run_dir = runs.resolve(args.run_dir)
    if not run_dir.exists():
        _log(f"error: run dir not found: {run_dir}")
        return int(Exit.USAGE)

    # --- --verify: standalone tamper-guard on an already-frozen φ --------------
    if args.verify:
        frozen_path = run_dir / "phi.frozen.yaml"
        if not frozen_path.exists():
            _log(f"error: nothing frozen yet at {frozen_path}")
            return int(Exit.UNKNOWN)
        fphi = phi_mod.load(frozen_path)
        ok, expected, got = phi_mod.verify_frozen(fphi)
        if ok:
            print(f"  ✅ φ freeze intact — content_hash matches ({expected[:16]}…)")
            return int(Exit.GREEN)
        print("  ❌ φ TAMPERED — frozen spec no longer matches its content_hash (Inv.6)")
        print(f"     expected: {expected}")
        print(f"     got:      {got}")
        return int(Exit.DEFECT)

    draft_path = run_dir / "phi.draft.yaml"
    if not draft_path.exists():
        _log(f"error: no phi.draft.yaml in {run_dir} (run `tcg formalize` first)")
        return int(Exit.USAGE)
    phi = phi_mod.load(draft_path)

    # --- --reject: H rejects the spec ⇒ ⊥_spec --------------------------------
    if args.reject:
        rec = {
            "decision": "reject", "reviewer": args.reviewer or "(unspecified)",
            "rejected_at": datetime.now(timezone.utc).isoformat(),
            "reason": args.reason or "(none given)",
        }
        phi_mod.dump(rec, run_dir / "validation.reject.yaml")
        print("⊥_spec — H rejected φ")
        return int(Exit.BOT_SPEC)

    # --- --approve: freeze φ ---------------------------------------------------
    if args.approve:
        if not args.reviewer:
            _log("error: --approve requires --reviewer (H must identify the human "
                 "attesting intent — Assumption 7)")
            return int(Exit.USAGE)
        from trusted.solver import solc_version
        checker_params = {
            "solc_version": solc_version(),          # full commit string — Inv.9
            "evm_version": args.evm_version,         # solc default unless overridden
            "engine": args.engine,
            "ext_calls": args.ext_calls,
            "targets": [t.strip() for t in args.targets.split(",") if t.strip()],
            "solvers": ["z3"],
            "model_checker_timeout_ms": args.timeout_ms,
            "note": "the judging z3 is solc's statically-linked build (opaque "
                    "version); see setup_report.json::P0",
        }
        frozen = phi_mod.freeze(
            phi,
            approved_by=args.reviewer,
            approved_at=datetime.now(timezone.utc).isoformat(),
            intent_attestation=args.intent_attestation
            or f"{args.reviewer} attests φ captures the intent in intent.txt",
            checker_params=checker_params,
        )
        out = phi_mod.dump(frozen, run_dir / "phi.frozen.yaml")
        ok, expected, _ = phi_mod.verify_frozen(frozen)  # self-check
        print("\n  tcg validate --approve — φ FROZEN (Inv.6 + Inv.9)")
        print(f"  reviewer    : {args.reviewer}")
        print(f"  content_hash: {expected}")
        print(f"  hashed_keys : {frozen['freeze']['hashed_keys']}")
        print(f"  checker     : solc {checker_params['solc_version'].split('+')[0]} · "
              f"engine={checker_params['engine']} · ext-calls={checker_params['ext_calls']} · "
              f"targets={checker_params['targets']}")
        print(f"  self-check  : {'intact' if ok else 'FAILED'}")
        print(f"  frozen      : {runs.disp(out)}")
        print(f"  next: tcg check --run-dir {runs.disp(run_dir)}\n")
        return int(Exit.GREEN) if ok else int(Exit.USAGE)

    # --- no flag: render and refuse to freeze ---------------------------------
    _render(phi)
    return int(Exit.UNKNOWN)  # nothing frozen — "could not proceed without a decision"
