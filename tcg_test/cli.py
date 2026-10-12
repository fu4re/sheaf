"""tcg CLI root — argparse dispatch over the trusted-gate subcommands.

argparse + py3.12 + PyYAML only: no Click/typer. ADR-0002 asks for artifacts a
third party can re-check with minimal tooling; adding a CLI framework dependency
would cut against that. Subparsers, a small dispatch table, done.

This file owns only PARSING and ROUTING. Every gate decision lives in its
command module, and every exit code comes from `tcg.outcome.Exit` — so there is
no second place a "green" can be minted (Inv.1). Task 0006 wires `setup-check`;
later tasks register their subcommand here (formalize, validate, check, vacuity,
package, run, status) without touching the routing contract.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from tcg.outcome import Exit


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="tcg",
        description="trusted gate around vibe-coded Solidity (ADR-0003 productization). "
        "Never prints green outside full ADR-conformance.",
    )
    sub = ap.add_subparsers(dest="command", metavar="<command>")

    # --- setup-check (Task 0006) — the empirical toolchain spike ---------------
    sc = sub.add_parser(
        "setup-check",
        help="empirically verify the toolchain (solc/SMTChecker/z3/lake) on "
        "known-good and known-bad fixtures; fail if the setup silently lies",
    )
    sc.add_argument(
        "--json",
        action="store_true",
        help="print the full setup_report.json to stdout (always written to disk)",
    )
    sc.add_argument(
        "--probe-neural-lean",
        action="store_true",
        help="emit the neural_lean_seam handoff (open + reproduction ghost-axiom "
        "targets from axiom_registry.json) for Task 0013 — data, not execution",
    )
    sc.add_argument(
        "--skip-lean",
        action="store_true",
        help="skip P7 (lake build of the trusted base) — useful for a fast probe",
    )

    # --- formalize (Task 0007) — F: lift the invariant into the φ tuple --------
    fo = sub.add_parser(
        "formalize",
        help="F (untrusted): propose/replay the economic invariant and lift it "
        "into the full φ=(Pre,Trace,Post,Exit) draft",
    )
    fo.add_argument("--contract", required=True, help="path to the SUT .sol")
    fo.add_argument("--name", required=True, help="contract name")
    fo.add_argument("--method", default="deposit", help="target method")
    fo.add_argument("--model", default="sonnet", help="model for live F generation")
    fo.add_argument("--spec-file", default=None,
                    help="replay a seed spec JSON instead of calling the model")
    fo.add_argument("--intent", default=None, help="economic intent text (→ intent.txt)")
    fo.add_argument("--run-dir", default=None,
                    help="run directory (default: a new stamped runs/<name>-<UTC>/)")

    # --- validate (Task 0007) — H: review + freeze φ --------------------------
    va = sub.add_parser(
        "validate",
        help="H (human oracle): review φ and freeze it (Inv.6 + Inv.9), or reject "
        "(⊥_spec), or --verify a frozen φ against tampering",
    )
    va.add_argument("--run-dir", required=True, help="run directory from `tcg formalize`")
    va.add_argument("--approve", action="store_true", help="freeze φ → phi.frozen.yaml")
    va.add_argument("--reject", action="store_true", help="reject φ → ⊥_spec")
    va.add_argument("--verify", action="store_true",
                    help="recompute the frozen hash; tamper ⇒ exit 3")
    va.add_argument("--reviewer", default=None, help="the human attesting intent (required for --approve)")
    va.add_argument("--reason", default=None, help="reason text for --reject")
    va.add_argument("--intent-attestation", default=None, help="explicit H attestation text")
    va.add_argument("--engine", default="chc", help="checker engine to pin (default chc)")
    va.add_argument("--ext-calls", default="untrusted", help="ext-calls mode to pin (default untrusted)")
    va.add_argument("--targets", default="assert", help="comma-separated SMTChecker targets to pin")
    va.add_argument("--evm-version", default="solc-default", help="EVM version to pin")
    va.add_argument("--timeout-ms", type=int, default=20000, dest="timeout_ms",
                    help="model-checker timeout to pin (ms)")

    # --- check (Task 0008) — K: the sole acceptance gate ----------------------
    ck = sub.add_parser(
        "check",
        help="K (trusted): hash-recheck frozen φ, run the pinned solver, classify "
        "Accept|Refute|Unknown, and decide the two-tier terminal (never green at "
        "source level)",
    )
    ck.add_argument("--run-dir", required=True, help="run directory with a frozen φ")

    # --- vacuity (Task 0009) — Probe R always, Probe M opt-in -----------------
    vc = sub.add_parser(
        "vacuity",
        help="vacuity gate: Probe R (reachability, any contract) always; Probe M "
        "(load-bearing) only with --family. No family ⇒ M_UNASSESSED (not PASS)",
    )
    vc.add_argument("--run-dir", default=None, help="run directory with a frozen φ (Probe R on its invariant)")
    vc.add_argument("--template", default=None, help="a pre-built __INVARIANT__-tagged harness (direct Probe R)")
    vc.add_argument("--contract", default=None, help="contract name for --template")
    vc.add_argument("--family", default=None, help="family manifest YAML (enables Probe M)")
    vc.add_argument("--reachability-only", action="store_true", dest="reachability_only",
                    help="run Probe R alone; exit on its verdict (PASS=0/FLAG=3/UNKNOWN=2)")
    vc.add_argument("--out", default=None, help="vacuity.json path (default: run-dir or next to manifest)")

    # --- package (Task 0010) — assurance package (T2) -------------------------
    pk = sub.add_parser(
        "package",
        help="assemble a self-contained, re-checkable assurance package: emit → "
        "spine → assemble → lint, with the render-rule (no green over an open "
        "dischargeable leaf)",
    )
    pk.add_argument("--run-dir", required=True, help="run directory (frozen φ + check.json + outcome.json)")
    pk.add_argument("--lean-axioms", default=None,
                    help="comma-separated axiom_registry ids to attach as Lean leaves (real lake "
                    "build). ONLY for a contract whose proof genuinely uses the axiom — attaching "
                    "an unused axiom is a false dependency.")

    # --- run (Task 0011) — e2e sequencer (no new gate logic) ------------------
    rn = sub.add_parser(
        "run",
        help="e2e: formalize → validate → check → vacuity → package, stopping at the "
        "first terminal ⊥. Pure sequencing — the only green decision is the K gate's",
    )
    rn.add_argument("--contract", required=True)
    rn.add_argument("--name", required=True)
    rn.add_argument("--method", default="deposit")
    rn.add_argument("--model", default="sonnet")
    rn.add_argument("--spec-file", default=None, help="replay a seed spec (deterministic)")
    rn.add_argument("--intent", default=None)
    rn.add_argument("--reviewer", default=None, help="H who freezes φ (required)")
    rn.add_argument("--family", default=None, help="vacuity family manifest (optional)")
    rn.add_argument("--lean-axioms", default=None, help="Lean leaves for package (optional)")
    rn.add_argument("--run-dir", default=None)

    # --- status (Task 0011) — read-only gate view -----------------------------
    st = sub.add_parser("status", help="read-only: gate states + terminal for a run dir")
    st.add_argument("--run-dir", required=True)

    return ap


def main(argv: Sequence[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.command is None:
        ap.print_help(sys.stderr)
        return int(Exit.USAGE)

    # Imported lazily so `tcg --help` does not pay the cost of pulling in the
    # cycle/ solver stack.
    if args.command == "setup-check":
        from tcg.commands import setup_check

        return setup_check.run(args)
    if args.command == "formalize":
        from tcg.commands import formalize

        return formalize.run(args)
    if args.command == "validate":
        from tcg.commands import validate

        return validate.run(args)
    if args.command == "check":
        from tcg.commands import check

        return check.run(args)
    if args.command == "vacuity":
        from tcg.commands import vacuity

        return vacuity.run(args)
    if args.command == "package":
        from tcg.commands import package

        return package.run(args)
    if args.command == "run":
        from tcg.commands import run as run_cmd

        return run_cmd.run(args)
    if args.command == "status":
        from tcg.commands import status

        return status.run(args)

    # Unreachable while argparse owns the subcommand set, but explicit beats a
    # silent fall-through to 0.
    ap.error(f"unknown command: {args.command}")
    return int(Exit.USAGE)
