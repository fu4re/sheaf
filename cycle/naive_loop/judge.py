"""Naive-loop judge (Task 0004). TRUSTED side — the only authority on `proved`.

Takes a finished run sandbox (the agent's `inv_*.sol` + `manifest.json`) and the
pre-registered canonical set for the level, then for EACH canonical invariant runs
the solver ITSELF (reusing trusted.solver.run_solver) and buckets the outcome:

  proved        — solver discharged it (success)
  refuted       — solver found a counterexample (the loop's code/invariant is wrong)
  inconclusive  — solver wall (nonlinear / over-approximation / k-bound / timeout)
  missing       — the loop never produced a harness for this canonical invariant
  compile_error — the loop's harness does not compile

The agent's own `agent_verdict` is recorded but NEVER trusted — judge = solver.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

NAIVE = Path(__file__).resolve().parent
CYCLE = NAIVE.parent
sys.path.insert(0, str(CYCLE))

from trusted.solver import run_solver  # noqa: E402

LEVELS = json.loads((NAIVE / "levels.json").read_text())

# Probe R (Finding 0005): substitute every asserted invariant with `false` and ask CHC
# whether the asserted point is reachable. `assert(false)` PROVED ⇒ point UNREACHABLE ⇒ the
# original `proved` is VACUOUS (antecedent failure / dead path). CHC-ONLY: BMC reports
# spurious violations on unreachable points. This is the loop-compatible half of the vacuity
# gate — the full Probe M needs adversarial families the free-form loop does not produce.
_ASSERT_RE = re.compile(r"assert\s*\([^;]*\)\s*;")


def reachability_probe(harness: Path, engine: str = "chc") -> dict:
    """Free-form Probe R on an agent-produced harness. Rewrites all single-line asserts to
    `assert(false)` and re-runs CHC. counterexample ⇒ reachable (PASS); proved ⇒ every
    asserted point dead ⇒ VACUOUS (FLAG); else UNKNOWN (reachability uncertified in budget)."""
    src = harness.read_text()
    if not _ASSERT_RE.search(src):
        return {"result": "UNKNOWN", "reason": "no single-line assert found to probe"}
    mutated = _ASSERT_RE.sub("assert(false);", src)
    probe_path = harness.with_name(f"_probeR_{harness.name}")
    probe_path.write_text(mutated)
    v = run_solver(probe_path, engine=engine)
    if v.verdict == "counterexample":
        return {"result": "PASS", "reachable": True, "vacuous": False}
    if v.verdict == "proved":
        return {"result": "FLAG", "reachable": False, "vacuous": True,
                "reason": "assert(false) PROVED ⇒ asserted point unreachable ⇒ vacuous proof"}
    return {"result": "UNKNOWN", "reachable": None, "vacuous": None,
            "reason": f"reachability uncertified (CHC={v.verdict})"}


def _load_manifest(sandbox: Path) -> dict[str, dict]:
    mf = sandbox / "manifest.json"
    if not mf.exists():
        return {}
    try:
        items = json.loads(mf.read_text())
    except json.JSONDecodeError:
        return {}
    return {it.get("name", it.get("file", f"_{i}")): it for i, it in enumerate(items)}


def _strip_comments(text: str) -> str:
    text = re.sub(r"/\*.*?\*/", "", text, flags=re.S)
    text = re.sub(r"//[^\n]*", "", text)
    return text


def _references_sut(harness_text: str, sut_contract: str) -> bool:
    """Does a given-code harness actually prove ABOUT the SUT (import/inherit/instantiate),
    rather than a standalone reimplementation? A proof about a reimplementation says nothing
    about the real contract unless a refinement is separately established. Comments are
    stripped first — a harness mentioning the SUT in prose ("verbatim from Vat") is still a
    reimplementation, not a reference."""
    code = _strip_comments(harness_text)
    pats = [r"\bimport\b", rf"\bis\s+{sut_contract}\b", rf"\bnew\s+{sut_contract}\b",
            rf"\b{sut_contract}\s*\("]
    return any(re.search(p, code) for p in pats)


def faithfulness_gate(harness: Path, inv: dict, level_mode: str, sut_contract: str) -> dict:
    """Three-status gate (PASS/FLAG/BLOCKED) for the soundness of a `proved`, beyond Probe R.
    Targets the false-proven kinds the naive loop produces on real code:

      * given-code refinement: in `invariant_on_given_code` mode a harness that never references
        the SUT proves about a REIMPLEMENTATION ⇒ fidelity to the SUT unverified ⇒ BLOCKED.
      * nonlinearity present: a `Σ(a·b)` law (requires_product) whose harness contains no `*`
        has abstracted the product away ⇒ FLAG (the nonlinear wall was assumed, not crossed).
      * decorative real-state (requires_mapping_sum): strip every write to the named mapping
        and re-verify; if the verdict is unchanged the mapping is decorative ⇒ the ghost is not
        coupled to the real aggregate. Kept as EVIDENCE with a caveat: a legitimately-constructed
        tracked-sum harness also asserts on the ghost, so this over-flags — it is a mechanical
        witness, not the sole basis for the verdict (full faithfulness needs the curated family
        / Lean anchor — exactly the moat)."""
    text = harness.read_text()
    code = _strip_comments(text)
    flags, blocks, evidence = [], [], {}

    if level_mode == "invariant_on_given_code" and not _references_sut(text, sut_contract):
        blocks.append(f"harness never references SUT `{sut_contract}` (import/inherit/instantiate) "
                      f"— proof is about a reimplementation; refinement to the SUT unverified")

    if inv.get("requires_product") and "*" not in code:
        flags.append("law contains a product (Σ a·b) but harness has no `*` — nonlinear term "
                     "abstracted to an opaque delta; the faithfulness link to the real product is absent")

    mp = inv.get("requires_mapping_sum")
    if mp:
        stripped = re.sub(rf"^\s*{re.escape(mp)}\[[^\]]*\]\s*[+\-]?=.*$", "", text, flags=re.M)
        if stripped != text:
            probe = harness.with_name(f"_faith_{harness.name}")
            probe.write_text(stripped)
            v = run_solver(probe, engine="chc").verdict
            evidence["decorative_state_probe"] = {
                "mapping": mp, "verdict_after_stripping_writes": v,
                "decorative": v == "proved",
                "caveat": "over-flags legitimate tracked-sum harnesses; mechanical witness only",
            }

    status = "FLAG" if flags else ("BLOCKED" if blocks else "PASS")
    return {"status": status, "flags": flags, "blocks": blocks, "evidence": evidence}


def judge_run(sandbox: str | Path, level: str, engine: str = "chc") -> dict:
    sandbox = Path(sandbox)
    level_spec = LEVELS[level]
    canon = level_spec["canonical"]
    level_mode = level_spec.get("mode", "synthesis")
    sut_contract = Path(level_spec["given_code"]).stem if level_spec.get("given_code") else ""
    manifest = _load_manifest(sandbox)

    results = []
    for inv in canon:
        name = inv["name"]
        entry = manifest.get(name)
        harness = sandbox / f"inv_{name}.sol"
        if not harness.exists():
            # fall back to whatever file the manifest named, if any
            if entry and (sandbox / entry["file"]).exists():
                harness = sandbox / entry["file"]
            else:
                results.append({
                    "name": name, "class": inv["class"], "bucket": "missing",
                    "agent_verdict": entry.get("agent_verdict") if entry else None,
                    "harness": None, "witness": None, "reason": "no harness produced",
                })
                continue
        v = run_solver(harness, engine=engine)
        bucket = {
            "proved": "proved", "counterexample": "refuted",
            "inconclusive": "inconclusive", "compile_error": "compile_error",
        }[v.verdict]
        # Every `proved` is independently checked for vacuity (Probe R) — judge=solver,
        # never the agent's self-report. A proved-but-vacuous invariant is the worst case
        # (the loop converges but lies — primary false-proven mode of 0004).
        vacuity = reachability_probe(harness, engine="chc") if bucket == "proved" else None
        gate = faithfulness_gate(harness, inv, level_mode, sut_contract) if bucket == "proved" else None
        probe_r_ok = vacuity is not None and vacuity.get("result") == "PASS"
        gate_ok = gate is not None and gate.get("status") == "PASS"
        clean = bucket == "proved" and probe_r_ok and gate_ok
        # honest status: a `proved` is only a real win if it is reachable AND survives the gate
        honest = ("clean" if clean
                  else ("vacuous" if (vacuity and vacuity.get("vacuous"))
                        else (gate.get("status").lower() if gate and gate.get("status") != "PASS"
                              else bucket)))
        results.append({
            "name": name, "class": inv["class"],
            "linearizable_by_synthesis": inv.get("linearizable_by_synthesis"),
            "bucket": bucket,
            "honest_status": honest,
            "clean": clean,
            "vacuity_probe_R": vacuity,
            "faithfulness_gate": gate,
            "false_proven": bool(bucket == "proved" and not clean),
            "agent_verdict": entry.get("agent_verdict") if entry else None,
            "used_ghost": entry.get("used_ghost") if entry else None,
            "used_snapshot": entry.get("used_snapshot") if entry else None,
            "used_assume_abstraction": entry.get("used_assume_abstraction") if entry else None,
            "harness": str(harness.relative_to(sandbox)),
            "engine": v.engine, "witness": v.witness, "reason": v.reason,
            "duration_s": v.duration_s,
        })

    n = len(canon)
    proved = [r for r in results if r["bucket"] == "proved"]
    false_proven = [r for r in results if r.get("false_proven")]
    proved_clean = [r for r in results if r.get("clean")]
    by_class: dict[str, dict] = {}
    for r in results:
        c = r["class"]
        by_class.setdefault(c, {"total": 0, "proved": 0})
        by_class[c]["total"] += 1
        if r["bucket"] == "proved":
            by_class[c]["proved"] += 1

    return {
        "level": level,
        "n_canonical": n,
        "proved_count": len(proved),
        "proved_rate": round(len(proved) / n, 3) if n else 0.0,
        "proved_clean_count": len(proved_clean),
        "proved_clean_rate": round(len(proved_clean) / n, 3) if n else 0.0,
        "false_proven_count": len(false_proven),
        "false_proven_names": [r["name"] for r in false_proven],
        "proved_names": [r["name"] for r in proved],
        "self_harness_used": sum(
            1 for r in results
            if r["bucket"] == "proved" and (r.get("used_ghost") or r.get("used_snapshot") or r.get("used_assume_abstraction"))
        ),
        "by_class": by_class,
        "results": results,
    }


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("sandbox")
    ap.add_argument("--level", required=True)
    ap.add_argument("--engine", default="chc")
    args = ap.parse_args()
    print(json.dumps(judge_run(args.sandbox, args.level, args.engine), indent=2, ensure_ascii=False))
