"""emit.py — the reusable, backend-agnostic surface a component calls to drop an
evidence record in the package's vocabulary.

A component (any solver, any prover, any orchestrator) integrates by calling one of
these from its own native output. It never imports the package schema or learns the
graph format — it just hands over what it natively knows. That call IS the "emit
toward the format" half of the hybrid: no translation layer downstream.

  emit_smt(...)     an SMTChecker / cvc5 / z3 solve result
  emit_lean(...)    a Lean theorem (its `lake build` outcome)
  emit_verdict(...) generic escape hatch for any other checker

Each returns the EvidenceRecord and, if `out_dir` is given, writes
`<record_id>.record.yaml` there for the assembler to pick up.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

from .evidence_record import EvidenceRecord, Result, Subject


def _write(rec: EvidenceRecord, out_dir: Path | None) -> EvidenceRecord:
    if out_dir is not None:
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        rec.dump(out_dir / f"{rec.record_id}.record.yaml")
    return rec


def emit_smt(
    record_id: str,
    *,
    human: str,
    formal: str,
    verdict: str,
    engine: str,
    shape: str | None = None,
    harness: str | None = None,
    witness: Any = None,
    reproduce: str | None = None,
    raw_ref: str | None = None,
    produced_by: dict | None = None,
    out_dir: Path | None = None,
    **extra: Any,
) -> EvidenceRecord:
    """Record one SMT solve. `formal` is the SMT-LIB / Solidity assertion checked;
    `engine` is solver+version+mode (e.g. 'solc 0.8.35 chc z3 4.16.0'); `harness`
    is the .sol file that reproduces it."""
    rec = EvidenceRecord(
        record_id=record_id,
        kind="smt_solve",
        subject=Subject(human=human, formal=formal, shape=shape),
        result=Result(verdict=verdict, engine=engine, witness=witness,
                      reproduce=reproduce, raw_ref=raw_ref),
        produced_by=produced_by or {"component": "smt_solver"},
        artifacts=[harness] if harness else [],
        extra=extra,
    )
    return _write(rec, out_dir)


# A clean Mathlib proof may depend ONLY on these axioms. `sorryAx` (a stub) or any
# contract/hypothesis axiom makes the term vacuous or unfaithful — NOT a proof.
_ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}


def emit_lean(
    record_id: str,
    *,
    human: str,
    formal: str,
    theorem_name: str,
    lean_file: str,
    build_status: str,
    axioms: list[str] | None = None,
    engine: str = "Lean 4 + Mathlib",
    reproduce: str | None = "lake build",
    produced_by: dict | None = None,
    out_dir: Path | None = None,
    **extra: Any,
) -> EvidenceRecord:
    """Record one Lean theorem. A build pass is NOT a proof: a `sorry` term also
    builds. `build_status` in {ok, failed, not_built} is the `lake build` ground
    truth; `axioms` is the kernel `#print axioms` result. The verdict is `proven`
    ONLY when the build is `ok` AND the axiom set is clean (⊆ {propext,
    Classical.choice, Quot.sound}, no `sorryAx`) — build rc alone can never carry it
    (Task 0014, Б2). `axioms=None` means the audit was not run: NOT proven."""
    audited = axioms is not None
    clean = audited and all(a in _ALLOWED_AXIOMS for a in axioms)
    if build_status != "ok":
        verdict = "not_built"
    elif clean:
        verdict = "proven"
    else:
        verdict = "unknown"     # built, but no clean kernel proof (unaudited or dirty axioms)
    audit_status = "clean" if clean else ("dirty" if audited else "unaudited")
    rec = EvidenceRecord(
        record_id=record_id,
        kind="lean_theorem",
        subject=Subject(human=human, formal=formal, shape=None),
        result=Result(verdict=verdict, engine=engine, reproduce=reproduce),
        produced_by=produced_by or {"component": "lean"},
        artifacts=[lean_file],
        extra={"theorem_name": theorem_name, "build_status": build_status,
               "axioms": axioms, "axiom_audit": audit_status, **extra},
    )
    return _write(rec, out_dir)


def emit_verdict(
    record_id: str,
    *,
    kind: str,
    human: str,
    formal: str,
    verdict: str,
    engine: str,
    shape: str | None = None,
    witness: Any = None,
    reproduce: str | None = None,
    raw_ref: str | None = None,
    artifacts: list[str] | None = None,
    produced_by: dict | None = None,
    out_dir: Path | None = None,
    **extra: Any,
) -> EvidenceRecord:
    """Generic escape hatch: any other checker (mined-guarantee triage, vacuity
    probe, diff-fuzz harness) drops a record without a bespoke helper."""
    rec = EvidenceRecord(
        record_id=record_id,
        kind=kind,
        subject=Subject(human=human, formal=formal, shape=shape),
        result=Result(verdict=verdict, engine=engine, witness=witness,
                      reproduce=reproduce, raw_ref=raw_ref),
        produced_by=produced_by or {"component": kind},
        artifacts=artifacts or [],
        extra=extra,
    )
    return _write(rec, out_dir)
