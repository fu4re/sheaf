"""axiom_audit.py — kernel-level `#print axioms` audit for Lean leaves (Task 0014, Б2).

A `lake build` pass is NOT a proof: a `sorry` term also builds. This runs the canonical
audit module (`AaveArith.AxiomAudit`, which `#print axioms` every discharged theorem) and
parses its output so a caller can gate a Lean leaf `proven` ONLY under a clean kernel axiom
set. Used by `tcg package` (production) and `verify_package --replay` (independent re-check)
— the SAME runner, so emission and re-check agree by construction.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

# A clean Mathlib proof may depend ONLY on these. `sorryAx` (a stub) or any contract/
# hypothesis axiom makes the term vacuous or unfaithful — NOT a proof.
ALLOWED_AXIOMS = {"propext", "Classical.choice", "Quot.sound"}

# Lean prints either `'Name' depends on axioms: [a, b]` or `'Name' does not depend on any axioms`.
_DEP = re.compile(r"'([^']+)' depends on axioms: \[([^\]]*)\]")
_NODEP = re.compile(r"'([^']+)' does not depend on any axioms")


def parse_axioms(text: str) -> dict[str, list[str]]:
    """Map theorem name -> axioms it depends on (empty list = none)."""
    out: dict[str, list[str]] = {}
    for m in _NODEP.finditer(text):
        out[m.group(1)] = []
    for m in _DEP.finditer(text):
        out[m.group(1)] = [a.strip() for a in m.group(2).split(",") if a.strip()]
    return out


def is_clean(axioms: list[str] | None) -> bool:
    return axioms is not None and all(a in ALLOWED_AXIOMS for a in axioms)


class AxiomAudit:
    """Result of building + parsing the audit module. `available` is False when the
    audit could not be run (lake absent, build error) — a caller MUST treat that as
    'not audited', never as clean."""

    def __init__(self, available: bool, reason: str, by_name: dict[str, list[str]]):
        self.available = available
        self.reason = reason
        self.by_name = by_name

    def axioms_for(self, theorem_name: str) -> list[str] | None:
        """Axioms for a theorem, matching full (`AaveArith.foo`) or short (`foo`) name;
        None if the audit did not cover it."""
        if theorem_name in self.by_name:
            return self.by_name[theorem_name]
        short = theorem_name.split(".")[-1]
        for name, ax in self.by_name.items():
            if name.split(".")[-1] == short:
                return ax
        return None


def _olean(project_dir: Path, module: str) -> Path:
    return project_dir / ".lake" / "build" / "lib" / (module.replace(".", "/") + ".olean")


def run(project_dir: Path, module: str = "AaveArith.AxiomAudit", timeout: int = 600) -> AxiomAudit:
    """Build the audit module and parse its `#print axioms` output. The module's
    `.olean` is removed first so lake re-elaborates and re-emits the print lines
    (a cached build is silent). Returns available=False with a reason on any failure."""
    project_dir = Path(project_dir)
    if not shutil.which("lake"):
        return AxiomAudit(False, "lake not on PATH", {})
    try:
        _olean(project_dir, module).unlink(missing_ok=True)
    except OSError:
        pass
    try:
        out = subprocess.run(["lake", "build", module], cwd=str(project_dir),
                             capture_output=True, text=True, timeout=timeout)
    except (subprocess.TimeoutExpired, OSError) as exc:
        return AxiomAudit(False, f"lake build failed to run: {exc}", {})
    by_name = parse_axioms(out.stdout + "\n" + out.stderr)
    if out.returncode != 0:
        return AxiomAudit(False, f"lake build rc={out.returncode}", by_name)
    if not by_name:
        return AxiomAudit(False, "no '#print axioms' output parsed", by_name)
    return AxiomAudit(True, "ok", by_name)
