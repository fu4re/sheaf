"""Orchestrator — wires the trust line [1] -> [4] -> [5] -> [6] and emits the
per-run artifact. This is the executable form of the separation-of-responsibility
hypothesis: an untrusted agent proposes, a deterministic gateway validates, a
trusted solver discharges, and the measurement layer scores against ground truth.

Usage:
  python orchestrator.py --contract contracts/MiniVault.sol      --name MiniVault
  python orchestrator.py --contract contracts/MiniVaultBuggy.sol --name MiniVaultBuggy
  # deterministic replay (no model call):
  python orchestrator.py --contract contracts/MiniVault.sol --name MiniVault \
         --spec-file measurement/artifacts/MiniVault__spec.seed.json
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from gateway.translator import (  # noqa: E402
    build_cross_harness,
    build_from_harness,
    build_harness,
    validate_compiles,
)
from measurement.comparator import compare  # noqa: E402
from trusted.solver import run_solver  # noqa: E402
from untrusted.economic_spec_generator.spec_runner import generate_spec  # noqa: E402

ARTIFACTS = ROOT / "measurement" / "artifacts"
BUILD = ARTIFACTS / "build"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contract", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--method", default="deposit")
    ap.add_argument("--model", default="sonnet")
    ap.add_argument("--engine", default="chc")
    ap.add_argument("--spec-file", default=None)
    ap.add_argument(
        "--harness",
        default=None,
        help="trusted pre-fixed proof harness (ghost) to inject the invariant into; "
        "the agent still reads --contract. Omit for subclass mode (Slice 1).",
    )
    ap.add_argument(
        "--cross-template",
        default=None,
        help="trusted cross-contract A/G harness (Task 0003): the agent's invariant I_A "
        "is injected into the __INVARIANT__ assert(s) and the spec's `summary_clauses` "
        "(assumed callee guarantee G_B) into the __SUMMARY__ require(s). The external "
        "call is replaced by havoc+require(G_B); G_B is discharged separately.",
    )
    args = ap.parse_args()

    contract_path = Path(args.contract)
    if not contract_path.is_absolute():
        contract_path = ROOT / contract_path
    ARTIFACTS.mkdir(parents=True, exist_ok=True)

    # [1] UNTRUSTED — agent proposes (or deterministic replay from cache).
    # NB: cross mode needs the CROSS prompt (untrusted/economic_spec_generator/prompt_cross.md,
    # which emits I_A + summary_clauses). generate_spec() still uses the single-invariant
    # prompt, so live cross-agent generation is NOT wired — refuse rather than silently run
    # the wrong prompt. Live N-run agent measurement is an explicit next step (Finding 0004).
    if args.cross_template and not args.spec_file:
        raise SystemExit(
            "cross mode: pass --spec-file (e.g. measurement/artifacts/VaultAsset__cross_spec.seed.json); "
            "live agent generation via prompt_cross.md is not yet wired into generate_spec."
        )
    if args.spec_file:
        spec = json.loads(Path(args.spec_file).read_text())
        spec_source = f"replay:{Path(args.spec_file).name}"
    else:
        _log(f"[1] economic_spec_generator -> {args.model} ...")
        spec = generate_spec(contract_path, args.name, args.method, model=args.model)
        (ARTIFACTS / f"{args.name}__spec.json").write_text(
            json.dumps(spec, indent=2, ensure_ascii=False)
        )
        spec_source = "claude -p"

    invariant_expr = spec["invariant"]["solidity_expr"]
    _log(f"    proposed invariant: {invariant_expr}")

    # [4] GATEWAY — translate to harness + deterministic compile check.
    # Harness mode (Slice 2): inject into a trusted ghost harness; the agent only
    # supplies the invariant, the ghost scaffolding stays pre-fixed & trusted.
    if args.cross_template:
        template = Path(args.cross_template)
        if not template.is_absolute():
            template = ROOT / template
        summary_clauses = spec.get("summary_clauses")
        if not summary_clauses:
            raise SystemExit("--cross-template requires `summary_clauses` in the spec (assumed G_B)")
        harness = build_cross_harness(template, args.name, invariant_expr, summary_clauses, BUILD)
        harness_mode = f"cross:{template.name}"
    elif args.harness:
        template = Path(args.harness)
        if not template.is_absolute():
            template = ROOT / template
        harness = build_from_harness(template, args.name, invariant_expr, BUILD)
        harness_mode = f"ghost:{template.name}"
    else:
        harness = build_harness(contract_path, args.name, invariant_expr, BUILD)
        harness_mode = "subclass"
    ok, errors, _raw = validate_compiles(harness)
    _log(f"[4] gateway ({harness_mode}): compiles={ok}")

    # [5] TRUSTED — solver core discharges the invariant.
    if not ok:
        verdict = {"verdict": "compile_error", "reason": errors}
    else:
        verdict = asdict(run_solver(harness, engine=args.engine))
    _log(f"[5] solver verdict: {verdict['verdict']}")

    # [6] MEASUREMENT — ground-truth delta (outside the loop).
    if args.cross_template:
        delta = {"match": "n/a", "note": "cross-contract A/G; interface mining + callee "
                 "discharge tracked in measurement/artifacts/cross_ag__triage.json"}
    else:
        delta = compare(spec, args.name)
    _log(f"[6] ground-truth delta: {delta['match']}")

    artifact = {
        "contract": args.name,
        "method": args.method,
        "spec_source": spec_source,
        "invariant": spec.get("invariant"),
        "gateway": {
            "mode": harness_mode,
            "harness": str(harness.relative_to(ROOT)),
            "compiles": ok,
        },
        "verdict": verdict,
        "ground_truth_delta": delta,
        "provenance": spec.get("_provenance"),
    }
    out = ARTIFACTS / f"{args.name}__verdict.json"
    out.write_text(json.dumps(artifact, indent=2, ensure_ascii=False))
    print(json.dumps(artifact, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
