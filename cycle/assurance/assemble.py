"""assemble.py — compose a package from a human-authored spine + evidence records.

This is the one irreducible step the hybrid keeps separate (see FORMAT.md): the
records carry mechanical facts (a solve, a build) but no judgment; the spine carries
the epistemic judgment (which claim is top, which edge is `proven` vs `assumed`,
what enters the trusted base) but no evidence. assemble() fuses them into the
package and copies cited artifacts in so the result is self-contained.

It is format-owned and backend-agnostic: it reads only EvidenceRecords (the stable
contract) and a spine in the format's own vocabulary. No knowledge of any
orchestrator/solver leaks in. Swapping the backend changes which component *emits*
records — not this file.

Spine (`spine.yaml`):

    meta: {contract: ..., date: ...}
    claims:
      - id: C1
        shape: stateless                 # epistemic (F0001 taxonomy), author-set
        evidence_record: R_caller        # the record backing this claim
        human: "..."                     # optional; else taken from the record
        depends_on:
          - {kind: assumption, ref: A_guarantee, status: assumed, human: "..."}
          - {kind: lean_theorem, ref: L_cons, status: proven, human: "..."}
    ledger:
      lean_theorems:
        - {id: L_cons, evidence_record: R_lean, status: proven}
      assumptions:
        - {id: A_guarantee, statement_human: ..., statement_formal: ...,
           why_assumed: ..., risk_if_false: ..., status: assumed}
      harness_faithfulness:
        - {id: H_model, target: ..., claim: ..., evidence: ..., evidence_ref: ..., status: ...}
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # cycle/ on path

from assurance.evidence_record import EvidenceRecord, load_records  # noqa: E402


class AssembleError(ValueError):
    pass


def _claim_verdict(record_verdict: str) -> str:
    """Map a record verdict onto the (narrower, honest) claim vocabulary. unknown /
    unreachable / not_built all collapse to `inconclusive` — we never upgrade a
    non-result into proven."""
    if record_verdict == "proven":
        return "proven"
    if record_verdict == "refuted":
        return "refuted"
    return "inconclusive"


def _copy_artifact(src_root: Path, rel: str, dst_dir: Path, prefix: str = "") -> str:
    """Copy a cited artifact into the package, return its package-relative path."""
    src = Path(rel)
    if not src.is_absolute():
        src = (src_root / rel).resolve()
    dst_dir.mkdir(parents=True, exist_ok=True)
    name = (prefix + "__" if prefix else "") + src.name
    dst = dst_dir / name
    if src.exists():
        shutil.copy2(src, dst)
    else:
        # keep the package honest: record the missing source rather than fabricate.
        dst.write_text(f"// MISSING SOURCE at assembly time: {src}\n")
    return dst


def _pkg_rel(pkg: Path, p: Path) -> str:
    return str(Path(p).resolve().relative_to(pkg.resolve()))


def assemble(spine_path: Path, records_dir: Path, out_pkg: Path, src_root: Path) -> Path:
    spine = yaml.safe_load(Path(spine_path).read_text())
    records = load_records(records_dir)

    def rec(rid: str) -> EvidenceRecord:
        if rid not in records:
            raise AssembleError(f"spine references record '{rid}' not found in {records_dir}")
        return records[rid]

    out_pkg = Path(out_pkg)
    if out_pkg.exists():
        shutil.rmtree(out_pkg)
    (out_pkg / "trusted").mkdir(parents=True)
    smt_dir = out_pkg / "evidence" / "smt"
    lean_dir = out_pkg / "evidence" / "lean"

    # --- claims -------------------------------------------------------------
    claims_out: list[dict] = []
    for c in spine.get("claims", []):
        r = rec(c["evidence_record"])
        verdict = _claim_verdict(r.result.verdict)
        evidence: dict[str, Any] = {}
        if verdict == "refuted":
            if r.result.witness is None:
                raise AssembleError(f"claim {c['id']}: refuted record carries no witness")
            evidence["witness"] = r.result.witness
            # also carry the harness so --replay can re-find the counterexample.
            if r.artifacts:
                dst = _copy_artifact(src_root, r.artifacts[0], smt_dir, c["id"])
                evidence["smt_query"] = _pkg_rel(out_pkg, dst)
            if r.result.reproduce:
                evidence["reproduce"] = r.result.reproduce
        else:
            # proven/inconclusive: cite the reproducing artifact if any
            if r.kind == "lean_theorem" and r.artifacts:
                dst = _copy_artifact(src_root, r.artifacts[0], lean_dir, c["id"])
                evidence["lean_proof"] = _pkg_rel(out_pkg, dst)
            elif r.artifacts:
                dst = _copy_artifact(src_root, r.artifacts[0], smt_dir, c["id"])
                evidence["smt_query"] = _pkg_rel(out_pkg, dst)
            if r.result.reproduce:
                evidence["reproduce"] = r.result.reproduce
        claim = {
            "id": c["id"],
            "human": c.get("human") or r.subject.human,
            "formal": r.subject.formal,
            "shape": c.get("shape") or r.subject.shape or "stateless",
            "verdict": verdict,
            "engine": r.result.engine,
            "evidence": evidence,
            "depends_on": c.get("depends_on", []),
        }
        claims_out.append(claim)

    graph = {"meta": spine.get("meta", {}), "claims": claims_out}

    # --- ledger -------------------------------------------------------------
    led_spine = spine.get("ledger", {})
    lean_theorems: list[dict] = []
    lean_projects: dict[str, str] = {}
    for lt in led_spine.get("lean_theorems", []):
        entry: dict[str, Any]
        if lt.get("evidence_record"):
            r = rec(lt["evidence_record"])
            lean_file = r.artifacts[0] if r.artifacts else lt.get("file", "")
            dst = _copy_artifact(src_root, lean_file, lean_dir, lt["id"]) if lean_file else None
            entry = {
                "id": lt["id"],
                "statement_human": lt.get("statement_human") or r.subject.human,
                "statement_formal": lt.get("statement_formal") or r.subject.formal,
                "file": _pkg_rel(out_pkg, dst) if dst else lt.get("file", ""),
                "theorem_name": lt.get("theorem_name") or r.extra.get("theorem_name", ""),
                "build_status": lt.get("build_status") or r.extra.get("build_status", "not_built"),
                "status": lt.get("status", "proven"),
            }
            # Task 0014 Б2: carry the kernel #print axioms audit so the linter can gate
            # `proven` on a clean axiom set, not just build rc.
            ax = lt.get("axioms") if lt.get("axioms") is not None else r.extra.get("axioms")
            if ax is not None:
                entry["axioms"] = ax
            proj = r.extra.get("lean_project") or (r.produced_by or {}).get("project")
            if proj:
                lean_projects[lt["id"]] = proj
        else:
            entry = {k: lt[k] for k in (
                "id", "statement_human", "statement_formal", "file",
                "theorem_name", "build_status", "status")}
            if lt.get("axioms") is not None:
                entry["axioms"] = lt["axioms"]
        lean_theorems.append(entry)

    ledger = {
        "meta": led_spine.get("meta", {}),
        "lean_theorems": lean_theorems,
        "assumptions": led_spine.get("assumptions", []),
        "harness_faithfulness": led_spine.get("harness_faithfulness", []),
    }

    # --- write package ------------------------------------------------------
    (out_pkg / "assurance_graph.yaml").write_text(
        yaml.safe_dump(graph, sort_keys=False, allow_unicode=True))
    (out_pkg / "trusted" / "ledger.yaml").write_text(
        yaml.safe_dump(ledger, sort_keys=False, allow_unicode=True))

    # replay manifest for Lean: point at the canonical lake project by a
    # PACKAGE-RELATIVE path, so the package self-locates the project wherever the
    # repo is checked out (Mathlib makes vendoring the full project impractical).
    if lean_projects:
        import os
        proj_rel = sorted(set(lean_projects.values()))[0]
        proj_abs = Path(proj_rel)
        if not proj_abs.is_absolute():
            proj_abs = (src_root / proj_rel).resolve()
        pkg_rel = os.path.relpath(proj_abs, out_pkg.resolve())
        lean_dir.mkdir(parents=True, exist_ok=True)
        (lean_dir / "lean_project.json").write_text(json.dumps(
            {"project": pkg_rel, "project_note": "path relative to this package dir",
             "audit_module": "AaveArith.AxiomAudit",  # `--replay` re-derives #print axioms here (Б2)
             "theorems": lean_projects}, indent=2))

    return out_pkg


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Assemble an assurance package (spine + records).")
    ap.add_argument("--spine", required=True)
    ap.add_argument("--records", required=True, help="directory of *.record.yaml")
    ap.add_argument("--out", required=True, help="output package directory")
    ap.add_argument("--src-root", default=".", help="base to resolve artifact paths (default cwd)")
    args = ap.parse_args(argv)
    pkg = assemble(Path(args.spine), Path(args.records), Path(args.out), Path(args.src_root))
    print(f"assembled -> {pkg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
