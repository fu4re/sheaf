"""Module [6b] — Vacuity gate (Task T1). The SOLVER is the judge; ZERO LLM.

A `proved` can be EMPTY. Vacuity (Beer/Ben-David/Eisner, IBM Haifa 2001;
Kupferman, CONCUR 2006) = the proof holds for a trivial reason: the asserted point
is unreachable (antecedent failure), or a component of the invariant carries no
verification load. Kupferman's unification — vacuity and coverage are the SAME check,
both = re-verify on a MUTATED input — is the algorithm: mutate a component, re-run the
solver; if the verdict is unchanged, the component is inert ⇒ the proof was (partly)
vacuous. Cheap, deterministic, no human.

Two probes, both solver-judged:

  Probe R — reachability / antecedent failure (CHC-ONLY). Substitute the invariant with
    `false`. `assert(false)` PROVED ⇒ the program point is UNREACHABLE ⇒ any property
    there is vacuous ⇒ FLAG. Refuted ⇒ reachable ⇒ PASS. CHC-ONLY by measurement: BMC
    reports SPURIOUS violations on unreachable points (it does not constrain the entry
    state to be constructor-reachable) — MiniERC20NoMintConservation is dead yet BMC
    "refutes" it, so a 'refuted if ANY engine' rule would falsely PASS a vacuous proof.

  Probe M — load-bearing / "how useless is the spec". Mutate each component of the
    invariant to a strictly-weaker form, re-discharge against the invariant's FAMILY (the
    honest harness + adversarial siblings that share its callee-side form). A component is
    LOAD-BEARING iff weakening it lets some adversary the original REFUTED slip through;
    INERT iff weakening changes no verdict. The discharge ENGINE must match the invariant's
    quantification (declared per family): a reachable-state invariant (conservation, in a
    view) → CHC only, because BMC yields spurious refutations from constructor-unreachable
    free states; a 2-state Hoare property (the delta, inline) → CHC+BMC, because CHC reports
    the under-credit as inconclusive and only BMC refutes it (Finding 0002 complementarity).
    A "blind spot" is a GENUINE proved (invariant holds on a bad callee), kept distinct from
    an undecided (solver-budget) adversary so incompleteness cannot masquerade as vacuity.

LAYER (answering "agent or trusted layer?"): this gate lives in the TRUSTED measurement
layer next to the solver, NOT the agent. A vacuity verdict is a judgement about proof
QUALITY; letting an LLM make it would be the model grading its own proof — the exact
anti-pattern this project forbids (judge = solver, never LLM). The mutation is a
deterministic syntactic transform (zero semantics, zero judgement); the verdict is the
solver's; PASS/FLAG is a deterministic comparison of solver verdicts. The agent's only
role is downstream and optional: PROPOSE a strengthening once a component is FLAGGED
inert — and that proposal is re-judged by the solver.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gateway.translator import build_from_harness, validate_compiles  # noqa: E402
from measurement.triage import _BUCKET, _safe_tag, discharge  # noqa: E402
from trusted.solver import run_solver  # noqa: E402

BUILD = ROOT / "measurement" / "artifacts" / "build"


def discharge_ev(harness_path, engines=("chc", "bmc")) -> dict:
    """Like triage.discharge (refuted if ANY engine refutes; proven if some proves & none
    refutes; else unknown) but RETAINS the per-engine evidence — verdict + witness + reason —
    so the report carries the refuting trace (and any spurious free-state counterexample),
    not just a bucket. For the claim ledger (T2): a refutation is only as good as its witness."""
    by, ev = {}, {}
    for e in engines:
        v = run_solver(Path(harness_path), engine=e)
        by[e] = _BUCKET.get(v.verdict, "unknown")
        if v.verdict in ("counterexample", "inconclusive"):  # decisive / informative verdicts
            ev[e] = {"verdict": v.verdict, "witness": v.witness, "reason": v.reason}
    bucket = "refuted" if "refuted" in by.values() else ("proven" if "proven" in by.values() else "unknown")
    return {"bucket": bucket, "by": by, "evidence": ev}


# =====================================================================================
# Probe R — reachability / antecedent failure (CHC-ONLY)
# =====================================================================================

def reachability_probe(template, contract, tag="") -> dict:
    """Substitute the invariant with `false` and ask CHC whether the asserted point is
    reachable. `proved` (assert(false) safe) ⇒ UNREACHABLE ⇒ the original proof is
    VACUOUS (FLAG). `counterexample` ⇒ reachable (PASS). Anything else (inconclusive /
    malformed) ⇒ cannot certify reachability ⇒ FLAG. CHC-ONLY: BMC is unsound for this
    direction (spurious violations on dead points — measured)."""
    h = build_from_harness(template, contract, "false", BUILD, tag=f"R_{_safe_tag(tag or contract)}")
    ok, errors, _ = validate_compiles(h)
    if not ok:
        return {"probe": "R", "solver_verdict": "compile_error", "result": "FLAG",
                "reachable": False, "vacuous": True, "reason": f"malformed: {errors[:1]}"}
    v = run_solver(h, engine="chc").verdict
    if v == "counterexample":
        return {"probe": "R", "solver_verdict": v, "result": "PASS",
                "reachable": True, "vacuous": False}
    if v == "proved":
        return {"probe": "R", "solver_verdict": v, "result": "FLAG", "reachable": False,
                "vacuous": True, "reason": "unreachable point — assert(false) PROVED ⇒ vacuous"}
    # inconclusive: CHC could neither witness a reaching trace nor prove unreachability in
    # budget. This is NOT a confident vacuity flag (that needs `proved`) and NOT a clean
    # pass — a distinct UNKNOWN. (A harness we expect to refute is anyway self-certifying
    # reachable via Probe M's refutation; Probe R matters for the ones we expect to prove.)
    return {"probe": "R", "solver_verdict": v, "result": "UNKNOWN", "reachable": None,
            "vacuous": None, "reason": f"reachability uncertified in budget (CHC={v})"}


# =====================================================================================
# Probe M — component mutation + family discrimination (engine matched per family)
# =====================================================================================

_REL_OPS = ("==", ">=", "<=", ">", "<")  # two-char ops first so '>=' is not read as '>'


def _split_rel(e: str):
    """Split an ATOMIC relational invariant at its top-level comparator."""
    for op in _REL_OPS:
        i = e.find(op)
        if i != -1:
            return op, e[:i].strip(), e[i + len(op):].strip()
    return None, None, None


def _drop_addends(rhs: str):
    """For an RHS that is a top-level sum `a + b (+ …)`, yield (label, kept_term) keeping
    exactly one addend (drop the rest) — the per-addend load-bearing probe."""
    if "+" not in rhs:
        return []
    parts = [p.strip() for p in rhs.split("+")]
    return [(f"keep_only_{_safe_tag(p)}", p) for p in parts]


def mutate_invariant(expr: str) -> list[dict]:
    """Deterministic, syntactic WEAKENING catalog for an atomic relational invariant
    (pure — no solver). Each entry weakens ONE component; re-discharging the mutant
    against the family reveals whether that component is load-bearing. Always includes
    the drop-to-`true` mutant (weakens the whole invariant). Atomic invariants only —
    conjunctions need a richer catalog (next iteration)."""
    e = expr.strip()
    out = [{"label": "drop_to_true", "expr": "true", "weakens": "whole invariant → ⊤"}]
    op, lhs, rhs = _split_rel(e)
    if op is None:
        return out
    if op == "==":
        out.append({"label": "eq_to_ge", "expr": f"{lhs} >= {rhs}", "weakens": "== → >= (drops the ≤ half)"})
        out.append({"label": "eq_to_le", "expr": f"{lhs} <= {rhs}", "weakens": "== → <= (drops the ≥ half)"})
    elif op in (">=", ">"):
        out.append({"label": "zero_rhs", "expr": f"{lhs} >= 0", "weakens": "RHS → 0 (tautology probe)"})
        out.append({"label": "relax_plus1", "expr": f"{lhs} + 1 {op} {rhs}", "weakens": "+1 slack on LHS"})
        for lbl, kept in _drop_addends(rhs):
            out.append({"label": lbl, "expr": f"{lhs} {op} {kept}", "weakens": f"keep only `{kept}` in RHS"})
    elif op in ("<=", "<"):
        out.append({"label": "relax_plus1_rhs", "expr": f"{lhs} {op} {rhs} + 1", "weakens": "+1 slack on RHS"})
        for lbl, kept in _drop_addends(rhs):
            out.append({"label": lbl, "expr": f"{lhs} {op} {kept}", "weakens": f"keep only `{kept}` in RHS"})
    return out


def family_discrimination(invariant_expr: str, family: dict, tag: str, engines=("chc", "bmc")) -> dict:
    """Discharge `invariant_expr` against every member of a FAMILY — the honest harness
    (label prefix 'honest') plus adversarial siblings (prefix 'adv') that share the same
    callee-side invariant form. An adversary the invariant does NOT refute is a BLIND
    SPOT: the invariant proves on a callee that is actually bad ⇒ vacuous proxy.
    `family` maps label → (template_path, contract_name).

    `engines` MUST match the invariant's quantification (caller declares it):
      * a REACHABLE-STATE invariant (e.g. conservation `ghostSum == totalSupply`, checked
        in a view over all reachable states) → ("chc",). BMC is UNSOUND here — it checks
        from a FREE entry state and yields spurious refutations from constructor-unreachable
        states (measured: BMC "refutes" honest conservation with ghostSum=1,totalSupply=0,
        empty trace). The dual of a vacuous proof: a spurious counterexample.
      * a 2-STATE / per-transition HOARE property (e.g. the delta `balanceOf[to] >= beforeTo
        + amount`, which must hold from ANY precondition-satisfying entry) → ("chc","bmc").
        BMC is sound AND necessary (CHC reports the burning-fee under-credit as inconclusive;
        BMC catches it — Finding 0002 complementarity)."""
    per = {}
    for label, (template, contract) in family.items():
        h = build_from_harness(template, contract, invariant_expr, BUILD,
                               tag=f"M_{_safe_tag(tag)}_{_safe_tag(label)}")
        ok, errors, _ = validate_compiles(h)
        per[label] = ({"bucket": "malformed", "detail": errors[:2]}
                      if not ok else discharge_ev(h, engines=engines))
    advers = {k: v for k, v in per.items() if k.startswith("adv")}
    refuted = sorted(k for k, v in advers.items() if v["bucket"] == "refuted")
    # A blind spot is GENUINE only when the invariant is PROVED on a bad callee (it holds
    # where it should not). An adversary the solver could not DECIDE (unknown/inconclusive)
    # is NOT a vacuity claim — separate it, else solver budget masquerades as vacuity.
    blind = sorted(k for k, v in advers.items() if v["bucket"] == "proven")
    undecided = sorted(k for k, v in advers.items() if v["bucket"] not in ("refuted", "proven"))
    honest = {k: v["bucket"] for k, v in per.items() if k.startswith("honest")}
    return {
        "invariant": invariant_expr,
        "per_member": per,
        "honest": honest,
        "refuted_adversaries": refuted,
        "blind_spots": blind,        # genuine: invariant PROVES on a bad callee
        "undecided": undecided,      # solver could not decide — NOT a vacuity claim
    }


def family_sanity(family: dict, tag: str, engines=("chc", "bmc")) -> dict:
    """Witness-tie guard: discharge the trivially-true invariant against each adversary.
    `assert(true)` must NOT refute; if it does, the harness is broken for an UNRELATED
    reason and any 'load-bearing' credit from it would be spurious. Returns the adversaries
    that fail the guard (should be empty for a well-formed family)."""
    broken = []
    for label, (template, contract) in family.items():
        if not label.startswith("adv"):
            continue
        h = build_from_harness(template, contract, "true", BUILD,
                               tag=f"sanity_{_safe_tag(tag)}_{_safe_tag(label)}")
        ok, _, _ = validate_compiles(h)
        if ok and discharge(h, engines=engines)["bucket"] == "refuted":
            broken.append(label)
    return {"tie_broken": broken}


def load_bearing_profile(invariant_expr: str, family: dict, tag: str, engines=("chc", "bmc")) -> dict:
    """Probe M2: mutate each component, re-discharge against the family, classify each
    mutation LOAD_BEARING (weakening loses a refutation the base had ⇒ that component was
    defending against that adversary) vs INERT (no verdict changes ⇒ the component carries
    no load). This is the "how useless is the spec" profiler — which component defends
    against which adversary. `engines` per family_discrimination (caller-declared)."""
    base = family_discrimination(invariant_expr, family, f"{tag}_base", engines=engines)
    base_ref = set(base["refuted_adversaries"])
    profile = []
    for m in mutate_invariant(invariant_expr):
        d = family_discrimination(m["expr"], family, f"{tag}_{m['label']}", engines=engines)
        lost = base_ref - set(d["refuted_adversaries"])
        # Of the refutations the weakening LOST: which became genuine blind spots (the
        # mutant PROVES on them ⇒ the dropped component was truly defending), vs merely
        # undecided (solver could not refute the weaker form in budget — solver-sensitive).
        lost_to_blind = sorted(lost & set(d["blind_spots"]))
        lost_to_undecided = sorted(lost & set(d["undecided"]))
        if lost_to_blind:
            cls = "load_bearing"
        elif lost_to_undecided:
            cls = "load_bearing?"  # weakening made it undecidable — solver-sensitive, not certain
        else:
            cls = "inert"
        profile.append({
            "mutation": m["label"],
            "weakens": m["weakens"],
            "expr": m["expr"],
            "refuted_adversaries": d["refuted_adversaries"],
            "lost_to_blind": lost_to_blind,
            "lost_to_undecided": lost_to_undecided,
            "classification": cls,
        })
    return {"invariant": invariant_expr, "base": base, "mutations": profile}


# =====================================================================================
# Top-level gate
# =====================================================================================

def vacuity_gate(reach_target, family: dict, invariant_expr: str, tag: str,
                 engines=("chc", "bmc")) -> dict:
    """T1 gate for one invariant. `reach_target` = (template, contract) of a single-assert
    harness for Probe R; `family` = honest + adversaries for Probe M; `engines` matches the
    invariant's quantification (see family_discrimination). THREE verdicts (a standing gate
    must not let "could not certify" read as green):
      • FLAG    — confident problem: point UNREACHABLE (Probe R proved), OR a genuine blind
                  spot (invariant PROVES on a bad callee), OR the base property is FALSE on
                  the honest member (invariant invalid, not merely vacuous).
      • BLOCKED — could not certify non-vacuity: Probe R UNKNOWN (reachability uncertified),
                  OR honest member unproven, OR an undecided adversary (a blind spot cannot
                  be ruled out), OR no adversaries at all (load-bearing unassessed).
      • PASS    — reachable AND base proves on honest AND every adversary refuted (no blind
                  spots, none undecided)."""
    r = reachability_probe(reach_target[0], reach_target[1], tag=tag)
    prof = load_bearing_profile(invariant_expr, family, tag, engines=engines)
    sanity = family_sanity(family, tag, engines=engines)
    blind = prof["base"]["blind_spots"]
    undecided = prof["base"]["undecided"]
    refuted = prof["base"]["refuted_adversaries"]
    honest = prof["base"]["honest"]

    flag, block = [], []

    # Probe R — reachability
    if r["result"] == "FLAG":
        flag.append(f"Probe R: {r.get('reason', r.get('solver_verdict'))}")
    elif r["result"] == "UNKNOWN":
        block.append(f"Probe R: {r.get('reason')} — reachability uncertified, cannot certify non-vacuity")

    # The base property MUST actually hold on the honest member — else it is plain WRONG,
    # not merely vacuous (mutating a false invariant is meaningless). refuted/malformed on
    # honest ⇒ invalid (FLAG); unknown on honest ⇒ cannot certify it even holds (BLOCKED).
    honest_invalid = sorted(k for k, b in honest.items() if b in ("refuted", "malformed"))
    honest_unproven = sorted(k for k, b in honest.items() if b == "unknown")
    if honest_invalid:
        flag.append(f"base property is FALSE/broken on honest member → {honest_invalid} (invalid, not just vacuous)")
    if honest_unproven:
        block.append(f"base property unproven on honest member → {honest_unproven} (cannot certify it holds)")

    # Probe M — genuine blind spots (FLAG) vs undecided adversaries (BLOCKED)
    if blind:
        flag.append(f"Probe M: blind spots (invariant PROVES on bad callee) → {blind}")
    if undecided:
        block.append(f"Probe M: undecided adversaries (a blind spot cannot be ruled out) → {undecided}")
    if not refuted and not blind and not undecided:
        block.append("Probe M: family has no adversaries — load-bearing unassessed")

    if sanity["tie_broken"]:
        flag.append(f"sanity: assert(true) refutes on {sanity['tie_broken']} (broken harness)")

    verdict = "FLAG" if flag else ("BLOCKED" if block else "PASS")
    return {
        "tag": tag,
        "invariant": invariant_expr,
        "engines": list(engines),
        "verdict": verdict,                  # PASS | FLAG | BLOCKED
        "flag_reasons": flag,
        "blocked_reasons": block,
        "honest": honest,
        "probe_R": r,
        "probe_M": prof,
        "sanity": sanity,
        "judge": "solver (SMTChecker — CHC for Probe R; per-family engines for Probe M, z3) — zero LLM judge",
    }
