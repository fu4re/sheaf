"""tcg outcomes — the single exit-code table for the trusted gate.

This module is the ONE place that maps a gate's epistemic state to a process
exit code. Keeping it in one file is a soundness measure, not tidiness: every
command imports `Exit` from here, so "could not verify" (code 2) and "found a
real defect" (code 3) can never silently collide, and "green" (code 0) has
exactly one definition. ADR-0003 Inv.1 (K is the sole gate) and Inv.4/5
(Unknown ≠ Refute) are enforced downstream by *routing through this table*.

Exit table (plan § Command surface):

    0  GREEN                 Verified(b, φ) — FULL ADR-conformance (Task 0008)
    1  USAGE                 usage / internal error (argparse, bad inputs)
    2  UNKNOWN               Unknown / BLOCKED / abstain — "could not verify"
    3  DEFECT                Refute / FLAG / INVALID — a real defect was found
    4  BOT_SPEC              ⊥_spec   — F abstained / H rejected
    5  BOT_GEN               ⊥_gen    — Refute / Unknown / budget in the loop
    6  BOT_ASSUMPTIONS_OPEN  ⊥_assumptions_open — Accept ∧ PASS but a
                             DISCHARGEABLE leaf (bytecode-identity, φ_context,
                             annotation-discharge) is still open. NOT green.

Why 2 and 3 are distinct (Inv.4 vs Inv.5): a verifier that lets "I couldn't
decide" share a code with "I found a counterexample" can be read as a clean
pass-or-fail when it is neither — the exact false-green this project forbids.
Unknown is rejection (exit 2), not acceptance; only a Refute carries a witness
(exit 3).

Why 6 is a ⊥, not a fourth shipped path: Accept ∧ vacuity=PASS at source level
is NECESSARY but not SUFFICIENT for green. When a dischargeable leaf stays open
(e.g. runtime bytecode is not yet shown bit-identical to the verified source —
Inv.7), the honest outcome is a reason-code *inside* not-verified. An evidence
package may still be emitted, but its claim is only about φ_checked and the open
assumptions are named in its header — nothing is shipped as "verified".

The two-tier acceptance predicate itself (classify(verdict) → KResult and the
Verified-vs-⊥_assumptions_open decision) lands in Task 0008; this module fixes
the exit vocabulary those decisions resolve to.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class Exit(IntEnum):
    """Process exit codes for every tcg command. Single source of truth."""

    GREEN = 0
    USAGE = 1
    UNKNOWN = 2
    DEFECT = 3
    BOT_SPEC = 4
    BOT_GEN = 5
    BOT_ASSUMPTIONS_OPEN = 6


# Human-facing gloss for each code — printed by `status`/`run` so an exit code is
# never opaque. Kept beside the enum so the two cannot drift.
EXIT_MEANING: dict[int, str] = {
    Exit.GREEN: "green — Verified(b, φ) under full ADR-conformance",
    Exit.USAGE: "usage / internal error",
    Exit.UNKNOWN: "Unknown / BLOCKED / abstain — could not verify",
    Exit.DEFECT: "Refute / FLAG / INVALID — a real defect was found",
    Exit.BOT_SPEC: "⊥_spec — F abstained or H rejected",
    Exit.BOT_GEN: "⊥_gen — Refute / Unknown / budget in the loop",
    Exit.BOT_ASSUMPTIONS_OPEN: (
        "⊥_assumptions_open — source-level accept with a dischargeable leaf "
        "open (NOT green)"
    ),
}


# =====================================================================================
# K result — the structured acceptance verdict (ADR §2.4)
# =====================================================================================
# classify() is the ONE translation from a raw solver verdict to a K decision.
# Unknown ≠ Refute BY CONSTRUCTION: they take different branches, only Refute carries
# a witness (Inv.5), and they map to different gate exit codes — Unknown is rejection
# (exit 2, Inv.4), Refute is a found defect (exit 3). Accept is NECESSARY but not
# sufficient for green; the two-tier predicate decides green vs ⊥_assumptions_open.

@dataclass
class KResult:
    kind: str  # accept | refute | unknown | gateway_reject
    reason: str | None = None
    witness: dict | None = None       # ONLY for refute (Inv.5)
    certificate: dict | None = None   # ONLY for accept (harness + command + raw)

    @property
    def is_accept(self) -> bool:
        return self.kind == "accept"

    @property
    def gate_exit(self) -> int:
        """The check GATE's process exit for a non-accept K result. Unknown and
        Refute MUST differ (Inv.4/5): a 'could not verify' must never share a code
        with a 'found a defect'."""
        return {
            "refute": int(Exit.DEFECT),          # 3 — a concrete counterexample
            "gateway_reject": int(Exit.DEFECT),  # 3 — INVALID (did not compile)
            "unknown": int(Exit.UNKNOWN),        # 2 — could not decide (rejection)
        }.get(self.kind, int(Exit.UNKNOWN))


def classify(verdict: dict) -> KResult:
    """solver.Verdict (as a dict) → KResult. The only place this mapping lives."""
    v = verdict.get("verdict")
    if v == "proved":
        return KResult("accept", certificate={
            "harness": verdict.get("_harness"),
            "command": verdict.get("command"),
            "engine": verdict.get("engine"),
            "targets": verdict.get("targets"),
            "solc_version": verdict.get("solc_version"),
        })
    if v == "counterexample":
        return KResult("refute", witness=verdict.get("witness"),
                       reason=verdict.get("reason") or "solver found a concrete counterexample")
    if v == "inconclusive":
        return KResult("unknown",
                       reason=verdict.get("reason") or "solver could not decide within budget")
    if v == "compile_error":
        return KResult("gateway_reject",
                       reason=verdict.get("reason") or "harness did not compile (gateway reject)")
    return KResult("unknown", reason=f"unrecognized solver verdict: {v!r}")


# =====================================================================================
# Assumed-leaf taxonomy (round-2 soundness fix) — IRREDUCIBLE vs DISCHARGEABLE
# =====================================================================================
# Recording an assumption in the ledger does NOT grant the right to call a run green.
# IRREDUCIBLE leaves are the ADR's irreducible trust assumptions (1/3/7); they may
# legitimately remain assumed under a green verdict. DISCHARGEABLE leaves MUST be
# closed for green — any one open ⇒ ⊥_assumptions_open. This is exactly the
# false-green class Finding 0007:55 caught.

IRREDUCIBLE_LEAVES: dict[str, str] = {
    "A_machine_semantics": "ADR Assumption 1 — SMTChecker's EVM model is faithful to the real EVM/KEVM",
    "A_solver": "ADR Assumption 3 — the solver (z3) is sound; a 'proved' is a real proof",
    "A_human_intent": "ADR Assumption 7 — H attests φ captures the economic intent",
}
DISCHARGEABLE_LEAVES: dict[str, str] = {
    "H_bytecode": "Inv.7 — deployed runtime bytecode is bit-identical to the verified source",
    "phi_context": "ADR §2.2 — every frozen φ dimension is mechanically discharged (φ_context = ∅)",
    "annotation_discharge": "Inv.8 — ghost annotations are checked or declared, none silently assumed",
}


# =====================================================================================
# Two-tier acceptance — the ONE place a terminal outcome is decided
# =====================================================================================

@dataclass
class Outcome:
    label: str                 # Verified | ⊥_gen | ⊥_assumptions_open | vacuous_proof | blocked
    exit_code: int             # the TERMINAL exit code for this outcome
    verified: bool             # True ONLY for full-conformance green
    reasons: list = field(default_factory=list)
    open_dischargeable: list = field(default_factory=list)
    assumed_irreducible: list = field(default_factory=list)
    pending_gates: list = field(default_factory=list)
    claim_scope: str = ""      # what a verified claim covers — ALWAYS only φ_checked

    def to_dict(self) -> dict:
        return {
            "label": self.label,
            "exit_code": self.exit_code,
            "verified": self.verified,
            "reasons": self.reasons,
            "open_dischargeable": self.open_dischargeable,
            "assumed_irreducible": self.assumed_irreducible,
            "pending_gates": self.pending_gates,
            "claim_scope": self.claim_scope,
        }


def two_tier_outcome(*, k: KResult, vacuity: str = "not_run",
                     phi_checked: list | None = None, phi_context: list | None = None,
                     bytecode_identity: str = "unverified", lint: str = "not_run",
                     annotations_ok: bool = True) -> Outcome:
    """The two-tier acceptance predicate (round-2 Strict).

        Verified[green] ⟺ Accept ∧ vacuity==PASS ∧ φ_context==∅
                        ∧ bytecode_identity==discharged ∧ assumed⊆IRREDUCIBLE
                        ∧ lint==WELL-FORMED
        Accept ∧ PASS but NOT all the above ⟹ ⊥_assumptions_open (NOT green)
        Refute / Unknown / gateway-reject ⟹ ⊥_gen

    Accept ≠ green. A verified claim is ALWAYS only about φ_checked."""
    phi_checked = phi_checked or []
    phi_context = phi_context or []

    # --- non-accept K results are terminal ⊥_gen (loop would terminate on gen failure)
    if k.kind == "refute":
        return Outcome("⊥_gen", int(Exit.BOT_GEN), False,
                       reasons=[f"K refuted φ_post with a witness — {k.reason}"],
                       claim_scope="none (refuted)")
    if k.kind == "unknown":
        return Outcome("⊥_gen", int(Exit.BOT_GEN), False,
                       reasons=[f"K Unknown (rejection, Inv.4) — {k.reason}"],
                       claim_scope="none (unknown)")
    if k.kind == "gateway_reject":
        return Outcome("⊥_gen", int(Exit.BOT_GEN), False,
                       reasons=[f"gateway rejected the harness — {k.reason}"],
                       claim_scope="none (gateway reject)")

    # --- Accept: vacuity dominates (a FLAG is a real defect; hard-BLOCKED is uncertified)
    if vacuity == "FLAG":
        return Outcome("vacuous_proof", int(Exit.DEFECT), False,
                       reasons=["vacuity gate FLAG — the 'proved' is (partly) vacuous"],
                       claim_scope="none (vacuous)")
    if vacuity == "BLOCKED":
        # Hard block: reachability itself uncertified (Probe R UNKNOWN). We cannot even
        # rule out antecedent-failure vacuity → exit 2, stop.
        return Outcome("blocked", int(Exit.UNKNOWN), False,
                       reasons=["vacuity gate BLOCKED — reachability (Probe R) uncertified; "
                                "non-vacuity could not be established"],
                       claim_scope="none (non-vacuity uncertified)")

    # --- Accept ∧ vacuity ∈ {PASS, M_UNASSESSED, not_run}: green vs ⊥_assumptions_open.
    # M_UNASSESSED (reachability PASS but load-bearing Probe M skipped for lack of an
    # adversary family) BLOCKS green but does NOT stop the run — it is recorded as a
    # non-green reason and the terminal is ⊥_assumptions_open, not a hard block.
    open_disch: list[str] = []
    reasons: list[str] = []
    if bytecode_identity != "discharged":
        open_disch.append("H_bytecode")
        reasons.append(f"open DISCHARGEABLE: H_bytecode — {DISCHARGEABLE_LEAVES['H_bytecode']} "
                       f"(is '{bytecode_identity}')")
    if phi_context:
        open_disch.append("phi_context")
        reasons.append(f"open DISCHARGEABLE: phi_context — deferred φ dimensions {phi_context} "
                       f"not mechanically discharged")
    if not annotations_ok:
        open_disch.append("annotation_discharge")
        reasons.append(f"open DISCHARGEABLE: annotation_discharge — {DISCHARGEABLE_LEAVES['annotation_discharge']}")

    if vacuity == "M_UNASSESSED":
        reasons.append("vacuity: reachability (Probe R) PASS but load-bearing (Probe M) NOT "
                       "assessed — no adversary family. Blocks green; run still proceeds.")

    pending = [g for g, val in (("vacuity", vacuity), ("lint", lint)) if val == "not_run"]

    green = (vacuity == "PASS" and lint == "WELL-FORMED" and not open_disch)
    if green:
        return Outcome("Verified", int(Exit.GREEN), True,
                       assumed_irreducible=list(IRREDUCIBLE_LEAVES),
                       claim_scope=f"φ_checked={phi_checked}")

    # Accept but not fully conformant → honest ⊥_assumptions_open (NOT green).
    for g in pending:
        reasons.append(f"pending gate: {g} not yet run — can only constrain further, never relax")
    if lint not in ("WELL-FORMED", "not_run"):
        reasons.append(f"assurance lint not WELL-FORMED ({lint})")
    return Outcome("⊥_assumptions_open", int(Exit.BOT_ASSUMPTIONS_OPEN), False,
                   reasons=reasons, open_dischargeable=open_disch,
                   assumed_irreducible=list(IRREDUCIBLE_LEAVES), pending_gates=pending,
                   claim_scope=f"φ_checked={phi_checked} (open assumptions named; NOT a verified claim)")
