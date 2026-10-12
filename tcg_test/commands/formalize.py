"""F — Formalizer (UNTRUSTED). Lifts the agent's single economic invariant into
the full φ = (Pre, Trace, Post, Exit) tuple on disk.

F is untrusted: its output is a DRAFT (`phi.draft.yaml`), proposed not trusted.
The lift is deliberately HONEST about coverage — Trace and Exit are materialized
as explicit dimensions with `status: declared/deferred`, never silently dropped
(ADR §2.2). The single mechanically-discharged economic invariant becomes
`spec.post[0]`; the SUT's pre-fixed overflow guards become `spec.pre` (detected
from the source by the gateway side, NOT authored by the model); Trace/Exit are
filled with explicit defaults that say what the MVP actually checks vs defers.

A genuinely empty F output (no parsable invariant) is an ABSTENTION → ⊥_spec,
not a crash and not a silent pass.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from tcg import phi as phi_mod
from tcg import runs
from tcg.outcome import Exit

# cycle/ as a library (same idiom as orchestrator.py / vacuity.py / setup_check.py)
CYCLE = runs.REPO / "cycle"
if str(CYCLE) not in sys.path:
    sys.path.insert(0, str(CYCLE))


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


# --- Pre detection: pre-fixed guards from the SUT (gateway-side, not the model) ---

def _method_body(src: str, method: str) -> str | None:
    m = re.search(rf"function\s+{re.escape(method)}\s*\(", src)
    if not m:
        return None
    i = src.find("{", m.end())
    if i == -1:
        return None
    depth = 0
    for j in range(i, len(src)):
        if src[j] == "{":
            depth += 1
        elif src[j] == "}":
            depth -= 1
            if depth == 0:
                return src[i + 1:j]
    return None


def _top_level_condition(args: str) -> str:
    """`require(<cond>, "msg")` → <cond>: split at the first TOP-LEVEL comma."""
    depth = 0
    for i, c in enumerate(args):
        if c in "([":
            depth += 1
        elif c in ")]":
            depth -= 1
        elif c == "," and depth == 0:
            return args[:i]
    return args


def extract_pre_guards(src: str, method: str) -> list[str]:
    """Extract `require(...)` conditions from the target method body — the SUT's
    pre-fixed guards. Detected from the source (the compiler enforces them), never
    invented. Honest fallback: method not found / no requires → []."""
    body = _method_body(src, method)
    if body is None:
        return []
    out, k = [], 0
    while True:
        idx = body.find("require(", k)
        if idx == -1:
            break
        p = idx + len("require")  # points at '('
        depth, end = 0, None
        for j in range(p, len(body)):
            if body[j] == "(":
                depth += 1
            elif body[j] == ")":
                depth -= 1
                if depth == 0:
                    end = j
                    break
        if end is None:
            break
        out.append(_top_level_condition(body[p + 1:end]).strip())
        k = end + 1
    return out


# --- the lift: single invariant + SUT → full φ tuple --------------------------

def lift_to_phi(spec: dict, contract: str, method: str, sut_source: str,
                spec_source: str) -> dict:
    inv = spec.get("invariant", {}) or {}
    expr = inv.get("solidity_expr")
    inv_name = inv.get("name", "invariant")

    pre = [
        {"id": f"pre_guard_{n}", "solidity_expr": g, "checked_as": "assume",
         "source": "sut_prefixed_guard"}
        for n, g in enumerate(extract_pre_guards(sut_source, method))
    ]
    trace = [{
        "id": "trace_nonreentrant", "kind": "reentrancy_frame",
        "checked_as": "ext_calls_untrusted", "status": "declared",
        "note": "MVP mechanically checks only the non-reentrant subset via "
                "--model-checker-ext-calls untrusted (havoc wall); deep Trace deferred",
    }]
    post = [{
        "id": f"post_{inv_name}", "solidity_expr": expr,
        "shape": "stateless", "checked_as": "assert",
        "informal": inv.get("informal"),
    }]
    exit_ = {
        "admissible": ["halt", "revert"],
        "forbidden_conditions": [
            {"condition": "overflow", "target": "overflow"},
            {"condition": "underflow", "target": "underflow"},
            {"condition": "div_by_zero", "target": "divByZero"},
        ],
        "checked_as": "smtchecker_safety_targets",
        "status": "deferred",
        "note": "overflow/underflow/div-by-zero ARE SMTChecker safety targets, but the "
                "current solver runner parses assert-target verdicts only (the 'Overflow … "
                "happens here' phrasing is not parsed) ⇒ exit-safety is NOT soundly "
                "discharged yet and is deferred, not claimed. Out-of-gas also deferred.",
    }
    coverage = {
        "checked_dimensions": ["pre", "post"],
        "deferred_dimensions": ["trace-deep", "exit-safety", "exit-outofgas"],
        "note": "K mechanically PROVES Post (assert) and INCORPORATES Pre (assume/require). "
                "Trace-deep hits the havoc wall (setup P8); exit-safety needs a safety-verdict "
                "parser the runner lacks; exit-outofgas is out of SMTChecker scope. These are "
                "represented in φ but NOT discharged ⇒ φ_context non-empty ⇒ a source-level run "
                "is ⊥_assumptions_open, NOT green.",
    }
    return {
        "schema": phi_mod.SCHEMA,
        "contract": contract,
        "method": method,
        "intent_ref": "intent.txt",
        "spec": {"pre": pre, "trace": trace, "post": post, "exit": exit_},
        "coverage": coverage,
        "provenance": {
            "spec_source": spec_source,
            "model": (spec.get("_provenance", {}) or {}).get("model_requested"),
            "invariant_name": inv_name,
        },
    }


def run(args) -> int:
    contract_path = runs.resolve(args.contract)
    if not contract_path.exists():
        _log(f"error: contract not found: {contract_path}")
        return int(Exit.USAGE)

    # --- [1] UNTRUSTED — agent proposes, or deterministic replay from a seed ---
    if args.spec_file:
        spec = json.loads(runs.resolve(args.spec_file).read_text())
        spec_source = f"replay:{Path(args.spec_file).name}"
    else:
        from untrusted.economic_spec_generator.spec_runner import generate_spec
        _log(f"[F] economic_spec_generator -> {args.model} ...")
        spec = generate_spec(contract_path, args.name, args.method, model=args.model)
        spec_source = "claude -p"

    # --- F-abstention: no parsable invariant ⇒ ⊥_spec (honest, not a crash) ----
    expr = (spec.get("invariant", {}) or {}).get("solidity_expr")
    if not expr:
        _log("[F] abstained: no parsable invariant in F output → ⊥_spec")
        print("⊥_spec — F produced no parsable invariant (F abstained)")
        return int(Exit.BOT_SPEC)

    phi = lift_to_phi(spec, args.name, args.method, contract_path.read_text(), spec_source)

    # --- workspace -------------------------------------------------------------
    run_dir = runs.resolve(args.run_dir) if args.run_dir else runs.new_run_dir(args.name)
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "contract.sol").write_text(contract_path.read_text())
    intent = args.intent or (spec.get("invariant", {}) or {}).get("informal") \
        or "(no intent text; seed/replay)"
    (run_dir / "intent.txt").write_text(intent + "\n")
    draft = phi_mod.dump(phi, run_dir / "phi.draft.yaml")

    # --- report ----------------------------------------------------------------
    print(f"\n  tcg formalize — φ draft (UNTRUSTED, not yet frozen)")
    print(f"  contract: {args.name}.{args.method}   source: {spec_source}")
    print(f"  φ tuple (all four dimensions materialized):")
    print(f"    pre   : {len(phi['spec']['pre'])} guard(s) from SUT")
    print(f"    trace : {phi['spec']['trace'][0]['id']} ({phi['spec']['trace'][0]['status']})")
    print(f"    post  : {phi['spec']['post'][0]['solidity_expr']}")
    print(f"    exit  : {len(phi['spec']['exit']['forbidden_conditions'])} forbidden condition(s) ({phi['spec']['exit']['status']})")
    print(f"  φ_checked : {phi_mod.phi_checked(phi)}")
    print(f"  φ_context : {phi_mod.phi_context(phi)}  ← non-empty ⇒ ⊥_assumptions_open, not green")
    print(f"  run dir   : {runs.disp(run_dir)}")
    print(f"  draft     : {runs.disp(draft)}")
    print(f"  next: tcg validate --run-dir {runs.disp(run_dir)} --approve --reviewer <you>\n")
    return int(Exit.GREEN)  # command success (draft emitted) — NOT a Verified verdict
