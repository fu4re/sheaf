"""Assurance package (T2) — emit → spine → assemble → lint, with the render-rule.

Turns a run into a self-contained, independently re-checkable assurance package by
REUSING the validated assurance layer (emit / assemble / verify_package). The only
tcg-specific synthesis is the spine (tcg.templates) and the choice of which named
leaves to carry — split IRREDUCIBLE vs DISCHARGEABLE so the render-rule can cap a
proven Post over an open dischargeable leaf below green (Finding 0007).

The package's `meta.assurance_level` is the run's terminal (e.g. ⊥_assumptions_open);
the linter's render-cap check refuses to let it be declared green over an open
dischargeable leaf.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml

from tcg import phi as phi_mod
from tcg import runs
from tcg import templates
from tcg.outcome import Exit

CYCLE = runs.REPO / "cycle"
if str(CYCLE) not in sys.path:
    sys.path.insert(0, str(CYCLE))

from assurance import axiom_audit  # noqa: E402
from assurance.assemble import assemble  # noqa: E402
from assurance.emit import emit_lean, emit_smt  # noqa: E402
from assurance.verify_package import lint  # noqa: E402

AXIOM_REGISTRY = CYCLE / "trusted" / "proofs" / "axiom_registry.json"

# a discharged entry's `lean_theorem` may name one or more theorems (e.g.
# "AaveArith.rayMul_lower (+ AaveArith.rayMul_upper)") — pull the dotted identifiers out.
_THEOREM_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_']+)+")


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _emit_lean_leaves(axiom_ids: list[str], records_dir: Path) -> list[dict]:
    """For each requested ghost axiom: pull it from axiom_registry.json, run a REAL
    `lake build` for build_status AND the kernel `#print axioms` audit (Task 0014 Б2),
    and emit a Lean record. A leaf is `proven` ONLY when the build is ok AND every
    theorem it covers has a clean axiom set — a build pass alone is never enough."""
    if not axiom_ids:
        return []
    reg = json.loads(AXIOM_REGISTRY.read_text())
    prover = reg.get("prover", {})
    proj_rel = prover.get("project", "cycle/trusted/proofs/aave_arith")
    lean_file = f"{proj_rel}/{prover.get('file', 'AaveArith/Basic.lean')}"
    by_id = {d["id"]: d for d in reg.get("discharged", [])}
    project_abs = runs.REPO / proj_rel

    # one real build for build_status, plus the kernel axiom audit (build-pass ≠ proof).
    import shutil
    if shutil.which("lake"):
        rc = subprocess.run(["lake", "build"], cwd=str(project_abs),
                            capture_output=True, text=True, timeout=600).returncode
        build_status = "ok" if rc == 0 else "failed"
        audit = axiom_audit.run(project_abs)
        if not audit.available:
            _log(f"warning: axiom audit unavailable ({audit.reason}) — Lean leaves cannot be 'proven'")
    else:
        build_status = "not_built"
        audit = axiom_audit.AxiomAudit(False, "lake not on PATH", {})

    leaves = []
    for aid in axiom_ids:
        d = by_id.get(aid)
        if not d:
            _log(f"warning: axiom '{aid}' not in axiom_registry.json — skipped")
            continue
        theorem_name = d.get("lean_theorem", "")
        # union the kernel axioms over every theorem this leaf covers; clean iff all covered.
        axioms = None
        if audit.available:
            names = _THEOREM_TOKEN.findall(theorem_name)
            per = [audit.axioms_for(n) for n in names]
            covered = [a for a in per if a is not None]
            if covered and len(covered) == len(names):
                axioms = sorted({ax for lst in covered for ax in lst})
            else:
                _log(f"warning: axiom '{aid}' — audit did not cover all of {names}; leaf not 'proven'")
        clean = axiom_audit.is_clean(axioms)
        status = "proven" if (build_status == "ok" and clean) else "assumed"
        rid = f"R_lean_{aid}"
        emit_lean(
            rid, human=d.get("informal") or d.get("math_statement") or aid,
            formal=d.get("lean_statement", ""), theorem_name=theorem_name,
            lean_file=lean_file, build_status=build_status, axioms=axioms,
            produced_by={"component": "lean", "project": proj_rel},
            lean_project=proj_rel, out_dir=records_dir,
        )
        leaf = {"id": f"L_{aid}", "record_id": rid,
                "human": d.get("informal") or d.get("lean_statement", aid),
                "status": status}
        if axioms is not None:
            leaf["axioms"] = axioms
        leaves.append(leaf)
    return leaves


def run(args) -> int:
    run_dir = runs.resolve(args.run_dir)

    frozen = run_dir / "phi.frozen.yaml"
    check_path = run_dir / "check.json"
    outcome_path = run_dir / "outcome.json"
    for p in (frozen, check_path, outcome_path):
        if not p.exists():
            _log(f"error: missing {p.name} in {run_dir} — run formalize→validate→check first")
            return int(Exit.USAGE)

    phi = phi_mod.load(frozen)
    ok, *_ = phi_mod.verify_frozen(phi)
    if not ok:
        _log("refuse: φ freeze hash mismatch (Inv.6) — package not built")
        return int(Exit.USAGE)
    check = json.loads(check_path.read_text())
    outcome = json.loads(outcome_path.read_text())

    cp = check.get("checker_params_used", {})
    engine = (f"solc {cp.get('solc_version', '?')} {cp.get('engine', 'chc')} "
              f"z3(bundled) targets={cp.get('targets')}")

    records_dir = run_dir / "records"
    records_dir.mkdir(parents=True, exist_ok=True)

    # --- emit the Post SMT record (verdict from the K gate) --------------------
    post = phi["spec"]["post"][0]
    k_result = check["k_result"]
    rec_verdict = {"accept": "proven", "refute": "refuted"}.get(k_result, "inconclusive")
    emit_smt(
        "R_post",
        human=post.get("informal") or post["solidity_expr"],
        formal=post["solidity_expr"],
        verdict=rec_verdict, engine=engine,
        shape=post.get("shape", "stateless"),
        harness=check.get("harness"),
        witness=check.get("witness") if rec_verdict == "refuted" else None,
        reproduce=" ".join(check.get("command") or []) or None,
        produced_by={"component": "tcg.check", "solc": cp.get("solc_version")},
        out_dir=records_dir,
    )

    lean_leaves = _emit_lean_leaves(
        [a.strip() for a in (args.lean_axioms or "").split(",") if a.strip()], records_dir)

    # --- synthesize the spine --------------------------------------------------
    spine = templates.build_spine(
        phi=phi, k_result=k_result, engine=engine,
        assurance_level=outcome.get("terminal", "⊥_assumptions_open"),
        claim_scope=outcome.get("claim_scope", ""),
        phi_context=phi_mod.phi_context(phi), lean_leaves=lean_leaves,
        date=datetime.now(timezone.utc).date().isoformat(),
    )
    spine_path = run_dir / "spine.yaml"
    spine_path.write_text(yaml.safe_dump(spine, sort_keys=False, allow_unicode=True))

    # --- assemble + lint -------------------------------------------------------
    pkg = run_dir / "package"
    assemble(spine_path, records_dir, pkg, runs.REPO)
    rep = lint(pkg, replay=False)

    # --- report ----------------------------------------------------------------
    print(f"\n  tcg package — assurance package (T2)")
    print(f"  contract     : {phi['contract']}.{phi['method']}")
    print(f"  top claim C1 : {rec_verdict}  ({post['solidity_expr']})")
    print(f"  assurance    : {spine['meta']['assurance_level']}  (declared in meta)")
    print(f"  leaves       : "
          f"{sum(1 for a in spine['ledger']['assumptions'] if a['leaf_class']=='irreducible')} IRREDUCIBLE, "
          f"{sum(1 for a in spine['ledger']['assumptions'] if a['leaf_class']=='dischargeable') + len(spine['ledger']['harness_faithfulness'])} DISCHARGEABLE, "
          f"{len(lean_leaves)} lean")
    for f in rep.findings:
        if f.check == "render-cap":
            print(f"  render-cap   : [{f.status}] {f.message}")
    print(f"  lint verdict : {rep.verdict}  (exit {rep.exit_code})")
    print(f"  package      : {runs.disp(pkg)}")
    print(f"  re-check     : python -m cycle.assurance.verify_package "
          f"{pkg.resolve()} --replay\n")
    return rep.exit_code
