"""Task 0006 — setup-verification spike (probes P0–P8).

Before building a gate, verify the toolchain EMPIRICALLY rather than assume it.
For a verification product a false green is worse than no tool, so the first
thing the CLI does is poke solc / SMTChecker (CHC + BMC) / the bundled z3 / lake
on KNOWN-GOOD and KNOWN-BAD fixtures and report works-vs-wall. The exit code is
the load-bearing signal:

    * any probe WRONG (ran but gave an UNEXPECTED verdict — the setup is lying)
      → Exit.DEFECT (3). This is the worst case and must never be masked.
    * else any probe WALL (a needed tool is absent) → Exit.UNKNOWN (2).
    * else all OK → Exit.GREEN (0).

Each probe reports one of:
    OK       ran and produced the expected verdict
    WRONG    ran and produced an UNEXPECTED verdict (setup lies — fail)
    WALL     a tool needed for this probe is unavailable (honest "can't assess")
    SKIPPED  deliberately not run (e.g. --skip-lean); informational, no exit weight

The matrix also resolves the verify-level question empirically (P1–P6 + P8):
is source-level SMTChecker sound enough for the MVP gate, and where does Trace
(reasoning THROUGH external calls) hit the havoc wall? That verdict is printed
and written to the report — it is measured here, not assumed in the plan.

This module is READ-ONLY over the repo sources: it only writes a JSON report
and harnesses into a temporary build dir.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import time
from pathlib import Path

from tcg.outcome import Exit

# --- repo geography ----------------------------------------------------------
REPO = Path(__file__).resolve().parents[2]
CYCLE = REPO / "cycle"
# Make cycle/ importable the same way orchestrator.py / vacuity.py do.
if str(CYCLE) not in sys.path:
    sys.path.insert(0, str(CYCLE))

from gateway.translator import (  # noqa: E402
    GatewayError,
    _strip_header,
    build_from_harness,
    build_harness,
    validate_compiles,
)
from measurement.vacuity import reachability_probe  # noqa: E402
from trusted.solver import SOLC, run_solver, solc_version  # noqa: E402

# --- fixtures (all verified to exist before coding — Task 0006 first step) ----
SMOKE = CYCLE / "trusted" / "smt_smoke"
CONTRACTS = CYCLE / "contracts"
XHARNESS = CYCLE / "trusted" / "harness" / "cross"
AAVE = CYCLE / "trusted" / "proofs" / "aave_arith"
AXIOM_REGISTRY = CYCLE / "trusted" / "proofs" / "axiom_registry.json"

# --- workspace ---------------------------------------------------------------
TCG_RUNS = CYCLE / "measurement" / "artifacts" / "tcg_runs"
SETUP_BUILD = TCG_RUNS / "setup_build"
REPORT = TCG_RUNS / "setup_report.json"

# --- pinned toolchain (AGENTS.md) --------------------------------------------
PIN_SOLC = "0.8.35"
PIN_Z3 = "4.16.0"
PIN_LEAN = "4.31.0"

# The seed invariant for the MiniVault family (measurement/artifacts/*.seed.json).
MINIVAULT_INVARIANT = "totalShares == totalAssets"


def _log(msg: str) -> None:
    print(msg, file=sys.stderr)


def _probe(pid: str, name: str, status: str, *, expected: str = "", got: str = "",
           detail: object = None, **extra) -> dict:
    r = {"probe": pid, "name": name, "status": status,
         "expected": expected, "got": got}
    if detail is not None:
        r["detail"] = detail
    r.update(extra)
    return r


def _run(cmd: list[str], *, cwd: Path | None = None, timeout: int = 60) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, cwd=cwd, timeout=timeout)
        return p.returncode, ((p.stdout or "") + (p.stderr or "")).strip()
    except FileNotFoundError:
        return 127, "tool-not-found"
    except subprocess.TimeoutExpired:
        return 124, f"timeout after {timeout}s"


# =====================================================================================
# P0 — versions (records the bundled z3 the SMTChecker actually judges with)
# =====================================================================================

def probe_p0() -> dict:
    versions: dict[str, object] = {}
    notes: list[str] = []

    sv = solc_version()
    versions["solc"] = sv
    versions["solc_pin"] = PIN_SOLC

    # z3: the SKEW finding. The standalone z3 on PATH is NOT what SMTChecker uses —
    # solc statically links its own z3, whose version is not exposed by any solc
    # CLI. Record both honestly (Inv.9: the params that actually judged must be on
    # record); never let the standalone version stand in for the judging one.
    rc, out = _run(["z3", "--version"])
    standalone_z3 = "absent"
    if rc == 0:
        m = re.search(r"(\d+\.\d+\.\d+)", out)
        standalone_z3 = m.group(1) if m else out.strip()
    rc_l, link = _run(["otool", "-L", SOLC])
    dyn_z3 = bool(re.search(r"libz3", link)) if rc_l == 0 else None
    versions["z3_standalone"] = standalone_z3
    versions["z3_pin"] = PIN_Z3
    versions["z3_bundled"] = {
        "linkage": ("dynamic" if dyn_z3 else "static") if dyn_z3 is not None else "unknown",
        "version": (standalone_z3 if dyn_z3 else "not exposed by solc CLI"),
        "note": (
            "solc statically links its own z3; the judging version is opaque and is "
            "NOT the standalone z3 on PATH"
            if dyn_z3 is False else
            "solc dynamically links libz3; the judging version equals the linked lib"
        ),
    }
    if standalone_z3 != PIN_Z3:
        notes.append(
            f"z3 skew: standalone={standalone_z3} vs pin={PIN_Z3}; the bundled judging "
            f"z3 is statically linked and not the standalone — recorded, not green-affecting"
        )

    rc, out = _run(["lake", "--version"])
    if rc == 0:
        m = re.search(r"Lean version (\d+\.\d+\.\d+)", out)
        versions["lean"] = m.group(1) if m else out.strip()
    else:
        versions["lean"] = "absent"
    versions["lean_pin"] = PIN_LEAN
    versions["python"] = sys.version.split()[0]

    # WALL only if the core compiler is missing; version skew is RECORDED, not WRONG
    # (the downstream probes P1–P8 catch real misbehavior — this probe just pins
    # what judged). A solc whose version differs from the pin is flagged but not
    # failed here; P1/P3 would surface any actual semantic regression.
    if sv == "unknown":
        return _probe("P0", "versions", "WALL", expected=f"solc {PIN_SOLC}",
                      got="solc absent", detail=versions, notes=notes)
    # solc_version() returns the full "0.8.35+commit.<hash>.<platform>" string; the pin
    # is the semver prefix. A genuine skew is a different semver, not the commit/platform tail.
    if not sv.startswith(PIN_SOLC):
        notes.append(f"solc skew: {sv} vs pin {PIN_SOLC} — downstream probes still authoritative")
    return _probe("P0", "versions", "OK",
                  expected=f"solc {PIN_SOLC}, lean {PIN_LEAN}; record bundled z3",
                  got=f"solc {sv}, lean {versions['lean']}, z3(standalone) {standalone_z3}",
                  detail=versions, notes=notes)


# =====================================================================================
# P1 — CHC proves a true assertion
# =====================================================================================

def probe_p1() -> dict:
    v = run_solver(SMOKE / "ProvablePass.sol", engine="chc")
    if v.verdict == "compile_error":
        return _probe("P1", "prove (CHC)", "WALL", expected="proved",
                      got="compile_error", detail=v.reason)
    status = "OK" if v.verdict == "proved" else "WRONG"
    return _probe("P1", "prove (CHC)", status, expected="proved", got=v.verdict,
                  detail={"reason": v.reason})


# =====================================================================================
# P2 — CHC refutes a false assertion with a concrete witness
# =====================================================================================

def probe_p2() -> dict:
    v = run_solver(SMOKE / "ProvableFail.sol", engine="chc")
    if v.verdict == "compile_error":
        return _probe("P2", "refute+witness (CHC)", "WALL", expected="counterexample",
                      got="compile_error", detail=v.reason)
    has_witness = bool(v.witness and v.witness.get("assignments"))
    status = "OK" if v.verdict == "counterexample" else "WRONG"
    note = None if has_witness else "verdict refuted but no witness assignments parsed"
    return _probe("P2", "refute+witness (CHC)", status, expected="counterexample (witness a=1)",
                  got=v.verdict, detail={"witness": v.witness, "note": note})


# =====================================================================================
# P3 / P4 — end-to-end gate on a known-good / known-bad contract (subclass mode)
# =====================================================================================

def _e2e(pid: str, sol: Path, name: str, expect: str) -> dict:
    try:
        h = build_harness(sol, name, MINIVAULT_INVARIANT, SETUP_BUILD)
    except (GatewayError, OSError) as e:
        return _probe(pid, f"e2e {name}", "WALL", expected=expect, got="harness-build-failed",
                      detail=str(e))
    ok, errors, _ = validate_compiles(h)
    if not ok:
        return _probe(pid, f"e2e {name}", "WALL", expected=expect, got="compile_error",
                      detail=errors[:2])
    v = run_solver(h, engine="chc")
    if expect == "proved":
        status = "OK" if v.verdict == "proved" else "WRONG"
    else:  # expect refute
        status = "OK" if v.verdict == "counterexample" else "WRONG"
    return _probe(pid, f"e2e {name}", status, expected=expect, got=v.verdict,
                  detail={"invariant": MINIVAULT_INVARIANT, "witness": v.witness,
                          "reason": v.reason})


def probe_p3() -> dict:
    return _e2e("P3", CONTRACTS / "MiniVault.sol", "MiniVault", "proved")


def probe_p4() -> dict:
    return _e2e("P4", CONTRACTS / "MiniVaultBuggy.sol", "MiniVaultBuggy", "counterexample")


# =====================================================================================
# P5 — vacuity gate FLAGs an intentionally-vacuous (dead) proof
# =====================================================================================

def probe_p5() -> dict:
    sub = {}
    for tmpl, name in (
        (XHARNESS / "VaultAssetAGDead.sol", "VaultAssetAGDead"),
        (XHARNESS / "MiniERC20NoMintConservation.sol", "MiniERC20NoMintConservation"),
    ):
        r = reachability_probe(tmpl, name, tag=name)
        sub[name] = {"result": r["result"], "solver_verdict": r["solver_verdict"],
                     "reason": r.get("reason")}
    all_flag = all(s["result"] == "FLAG" for s in sub.values())
    # A dead point NOT flagged is the vacuity gate failing open — that is WRONG, the
    # exact false-green the gate exists to stop. Anything other than FLAG on a known
    # dead fixture fails.
    status = "OK" if all_flag else "WRONG"
    got = ", ".join(f"{k}={v['result']}" for k, v in sub.items())
    return _probe("P5", "vacuity FLAG (dead)", status, expected="FLAG (both)", got=got,
                  detail=sub)


# =====================================================================================
# P6 — engine ⟂ quantifier policy holds (both soundness directions)
# =====================================================================================
# The gate's engine selection is a SOUNDNESS policy, not a tuning knob:
#   (a) a 2-state Hoare property (the delta) needs BMC — it must catch a real
#       under-credit that CHC may over-approximate past;
#   (b) a reachable-state invariant (conservation) must be CHC-ONLY, because BMC
#       reasons from a FREE entry state and yields SPURIOUS counterexamples on
#       constructor-unreachable states. A naive "refute if ANY engine refutes"
#       rule would FALSELY fail an honest invariant — a false REFUTE, the dual of
#       a false green. (CLAUDE.md soundness trap; Finding 0002 / vacuity.py.)
# P6 verifies BOTH directions empirically and records, honestly, that on this
# toolchain CHC also refutes the delta directly (Finding 0002 had CHC inconclusive
# there) — a candidate toolchain-drift observation that does NOT affect soundness.

def probe_p6() -> dict:
    # --- P6a: delta (2-state) — BMC catches the under-credit; CHC must not prove it
    delta_tmpl, delta_name = XHARNESS / "BurnFeeERC20Delta.sol", "BurnFeeERC20Delta"
    delta_inv = "balanceOf[to] >= beforeTo + amount"
    try:
        hd = build_from_harness(delta_tmpl, delta_name, delta_inv, SETUP_BUILD, tag="p6_delta")
    except (GatewayError, OSError) as e:
        return _probe("P6", "engine⟂quantifier policy", "WALL",
                      expected="delta refuted by BMC; conservation CHC-only", got="harness-build-failed",
                      detail=str(e))
    ok, errors, _ = validate_compiles(hd)
    if not ok:
        return _probe("P6", "engine⟂quantifier policy", "WALL",
                      expected="delta refuted by BMC; conservation CHC-only", got="compile_error",
                      detail=errors[:2])
    d_chc = run_solver(hd, engine="chc")
    d_bmc = run_solver(hd, engine="bmc")

    # --- P6b: conservation (reachable-state) — CHC proves; any BMC CE is spurious
    cons_tmpl, cons_name = XHARNESS / "MiniERC20Conservation.sol", "MiniERC20Conservation"
    cons_inv = "ghostSum == totalSupply"
    hc = build_from_harness(cons_tmpl, cons_name, cons_inv, SETUP_BUILD, tag="p6_cons")
    ok_c, errors_c, _ = validate_compiles(hc)
    if not ok_c:
        return _probe("P6", "engine⟂quantifier policy", "WALL",
                      expected="conservation CHC-proves", got="compile_error (conservation)",
                      detail=errors_c[:2])
    c_chc = run_solver(hc, engine="chc")
    c_bmc = run_solver(hc, engine="bmc")

    # --- soundness criteria -------------------------------------------------------
    # (a) the FALSE delta must be refuted by BMC, and CHC must NOT prove it (a false
    #     green). Both refuting on this toolchain is sound.
    delta_sound = (d_bmc.verdict == "counterexample") and (d_chc.verdict != "proved")
    # (b) the HONEST conservation must be PROVED by the sound (CHC) engine. Because
    #     CHC proves it true over all reachable states, ANY BMC counterexample is, by
    #     construction, from an unreachable free state — provably spurious.
    cons_chc_proves = c_chc.verdict == "proved"
    bmc_spurious = cons_chc_proves and c_bmc.verdict == "counterexample"
    cons_chc_refutes_honest = c_chc.verdict == "counterexample"  # would be alarming

    if d_chc.verdict == "proved" or cons_chc_refutes_honest:
        status = "WRONG"  # false green (false delta proved) or false refute (honest CHC-refuted)
    elif delta_sound and cons_chc_proves:
        status = "OK"
    elif c_chc.verdict == "inconclusive":
        status = "WALL"  # couldn't establish the honest invariant in budget
    else:
        status = "WRONG"

    return _probe(
        "P6", "engine⟂quantifier policy", status,
        expected="BMC refutes false delta; CHC proves honest conservation (BMC-CE there is spurious)",
        got=f"delta[chc={d_chc.verdict},bmc={d_bmc.verdict}] cons[chc={c_chc.verdict},bmc={c_bmc.verdict}]",
        detail={
            "p6a_delta": {
                "invariant": delta_inv, "chc": d_chc.verdict, "bmc": d_bmc.verdict,
                "bmc_witness": d_bmc.witness,
                "soundness": "BMC refutes the under-credit; CHC does not falsely prove it",
            },
            "p6b_conservation": {
                "invariant": cons_inv, "chc": c_chc.verdict, "bmc": c_bmc.verdict,
                "bmc_witness": c_bmc.witness,
                "bmc_counterexample_is_spurious": bmc_spurious,
                "soundness": "CHC proves honest conservation over all reachable states; "
                             "the BMC counterexample (free entry state, empty/short trace) is "
                             "provably spurious ⇒ engine policy is CHC-only for reachable-state "
                             "invariants (guards against a false REFUTE)",
            },
            "finding_0002_note": (
                f"Finding 0002 recorded CHC as INCONCLUSIVE on the burning-fee delta; on this "
                f"toolchain CHC refutes it directly (chc={d_chc.verdict}). Candidate toolchain "
                f"drift (newer solc/bundled-z3 strengthened CHC). Soundness unaffected — both "
                f"engines refute the false property; no false green."
            ),
        },
    )


# =====================================================================================
# P7 — the Lean trusted base actually builds (lake build, pinned toolchain)
# =====================================================================================

def probe_p7(skip: bool) -> dict:
    if skip:
        return _probe("P7", "lean trusted base builds", "SKIPPED",
                      expected="lake build rc=0", got="skipped (--skip-lean)")
    if not (AAVE / "lakefile.toml").exists():
        return _probe("P7", "lean trusted base builds", "WALL",
                      expected="lake build rc=0", got="no lake project", detail=str(AAVE))
    t0 = time.time()
    rc, out = _run(["lake", "build"], cwd=AAVE, timeout=600)
    dur = round(time.time() - t0, 1)
    if rc == 127:
        return _probe("P7", "lean trusted base builds", "WALL",
                      expected="lake build rc=0", got="lake absent", detail=out[:300])
    if rc == 124:
        return _probe("P7", "lean trusted base builds", "WALL",
                      expected="lake build rc=0", got="build timeout", detail=out[:300])
    status = "OK" if rc == 0 else "WRONG"
    return _probe("P7", "lean trusted base builds", status, expected="lake build rc=0",
                  got=f"rc={rc} ({dur}s)", detail={"tail": out.splitlines()[-6:] if out else []})


# =====================================================================================
# P8 — ext-calls ceiling: the source-level Trace wall (untrusted havoc vs trusted)
# =====================================================================================

# Mirrors the verdict branches of trusted/solver.py for a direct (ext-calls) solc run.
def _classify_solc(text: str) -> str:
    if any(l.strip().startswith("Error:") for l in text.splitlines()):
        return "compile_error"
    if re.search(r"Assertion violation happens here", text):
        return "counterexample"
    if re.search(r"Assertion violation might happen here", text):
        return "inconclusive"
    if re.search(r"could not be proved", text):
        return "inconclusive"
    if re.search(r"proved safe", text):
        return "proved"
    return "no-result"


def _solc_extcalls(harness: Path, mode: str) -> str:
    rc, text = _run([
        SOLC, "--model-checker-engine", "chc", "--model-checker-targets", "assert",
        "--model-checker-solvers", "z3", "--model-checker-timeout", "20000",
        "--model-checker-ext-calls", mode, str(harness),
    ], timeout=180)
    return _classify_solc(text)


def probe_p8() -> dict:
    # Build a REAL external-call solvency harness around VaultAsset (no havoc
    # abstraction — that is the whole point: measure the wall, not the workaround).
    # build_harness's subclass cannot forward VaultAsset's constructor arg, so we
    # assemble the harness inline here.
    src = _strip_header((CONTRACTS / "cross" / "VaultAsset.sol").read_text())
    harness_src = f"""// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

{src}

contract __Harness is VaultAsset {{
    constructor(IERC20 a) VaultAsset(a) {{}}
    // Cross-contract solvency — provable ONLY by reasoning THROUGH the external
    // ERC20 call, which `untrusted` ext-calls havoc as a reentrant callback.
    function __check_solvency() public view {{
        assert(asset.balanceOf(address(this)) >= totalAssets);
    }}
}}
"""
    SETUP_BUILD.mkdir(parents=True, exist_ok=True)
    h = SETUP_BUILD / "VaultAsset__p8_solvency__harness.sol"
    h.write_text(harness_src)
    ok, errors, _ = validate_compiles(h)
    if not ok:
        return _probe("P8", "ext-calls Trace ceiling", "WALL",
                      expected="untrusted does NOT prove (wall)", got="compile_error",
                      detail=errors[:2])

    untrusted = _solc_extcalls(h, "untrusted")
    trusted = _solc_extcalls(h, "trusted")
    # SOUNDNESS check: under the sound (untrusted) mode the havoc wall must block
    # the proof — the external call may reenter and break solvency. If `untrusted`
    # PROVES through a real external call, that is a false green (WRONG). `trusted`
    # mode proving is EXPECTED and is exactly why trusted-interface is a vacuity
    # risk — recorded, informational.
    if untrusted == "compile_error" or untrusted == "no-result":
        status, got = "WALL", f"untrusted={untrusted}"
    elif untrusted == "proved":
        status, got = "WRONG", f"untrusted=proved (proved THROUGH havoc'd ext-call — unsound)"
    else:
        status, got = "OK", f"untrusted={untrusted} (wall), trusted={trusted}"
    return _probe("P8", "ext-calls Trace ceiling", status,
                  expected="untrusted does NOT prove (havoc wall)", got=got,
                  detail={"untrusted_mode": untrusted, "trusted_mode": trusted,
                          "meaning": "untrusted = sound havoc wall; trusted = assumes no "
                          "reentrancy (vacuous-interface risk). The gap is the source-level "
                          "Trace ceiling."})


# =====================================================================================
# neural_lean_seam — pure-data handoff to Task 0013 (no execution)
# =====================================================================================

def neural_lean_seam() -> dict:
    if not AXIOM_REGISTRY.exists():
        return {"status": "WALL", "reason": f"axiom_registry.json not found at {AXIOM_REGISTRY}"}
    reg = json.loads(AXIOM_REGISTRY.read_text())
    prover = reg.get("prover", {})
    project = {
        "path": prover.get("project", str(AAVE.relative_to(REPO))),
        "file": prover.get("file", "AaveArith/Basic.lean"),
        "lean": prover.get("lean", PIN_LEAN),
        "mathlib": prover.get("mathlib", "v4.31.0"),
    }
    # Difficulty anchors named by Task 0013 (L1 easy / L2 trivial / L3 hard).
    difficulty = {
        "mulDiv_le_when_y_le_denom": "L1-easy",
        "mulDiv_round_down": "L1-easy",
        "product_delta_distributivity": "L2-trivial",
        "erc20_transfer_sum_preserved": "L3-hard",
    }
    repro = []
    for d in reg.get("discharged", []):
        if d.get("status") != "proven" or "lean_statement" not in d:
            continue
        repro.append({
            "id": d["id"],
            "lean_theorem": d.get("lean_theorem"),
            "lean_statement": d.get("lean_statement"),
            "difficulty": difficulty.get(d["id"], "unrated"),
            "role": "reproduction — kernel already accepts a manual proof; a prover "
                    "reproducing it validates the seam end-to-end (kernel is the judge)",
        })
    frontier = [
        {"informal_statement": s,
         "role": "open frontier — NOT yet formalized; needs a Lean statement before a "
                 "prover can attempt it"}
        for s in reg.get("not_yet_discharged", [])
    ]
    return {
        "status": "OK",
        "project": project,
        "trust_model": "the prover is an UNTRUSTED generator; a proof counts ONLY if the "
                       "Lean kernel accepts it via `lake build` against the pinned toolchain "
                       "(zero added trust). A prover that emits only a verdict is disqualified.",
        "reproduction_targets": repro,
        "open_frontier": frontier,
        "handoff_note": "data-only handoff; Task 0013 runs the prover and `lake build`. "
                        "Start with L1-easy, stress-test on L3-hard (transfer_sum_preserved "
                        "over Finset).",
    }


# =====================================================================================
# verify-level verdict — measured, not assumed
# =====================================================================================

def verify_level(probes: dict[str, dict]) -> dict:
    def st(pid: str) -> str:
        return probes.get(pid, {}).get("status", "MISSING")

    core = ["P1", "P2", "P3", "P4", "P5", "P6"]
    core_ok = all(st(p) == "OK" for p in core)
    p8 = probes.get("P8", {})
    untrusted = p8.get("detail", {}).get("untrusted_mode") if isinstance(p8.get("detail"), dict) else None
    wall_present = st("P8") == "OK" and untrusted in ("counterexample", "inconclusive")

    if core_ok:
        source_verdict = (
            "source-level SMTChecker is SOUND for the MVP gate: it proves true "
            "invariants (P1/P3), refutes false ones with witnesses (P2/P4), FLAGs "
            "vacuous proofs (P5), and the engine⟂quantifier policy holds (P6: BMC "
            "refutes the false delta; CHC-only for reachable-state conservation, "
            "where BMC's free-state counterexample is spurious)."
        )
    else:
        failed = [p for p in core if st(p) != "OK"]
        source_verdict = (
            f"source-level soundness NOT established: probes {failed} did not pass — "
            f"resolve before trusting the gate."
        )

    if wall_present:
        trace_verdict = (
            "Trace-deep (reasoning THROUGH external calls) hits the havoc wall under "
            "the sound (untrusted) ext-calls mode → Trace-deep is DEFERRED to "
            "KEVM/Halmos. Source-level covers Pre / Post / Exit-safety + the "
            "non-reentrant Trace subset only — recorded honestly, not silently dropped."
        )
    elif st("P8") in ("WALL", "SKIPPED", "MISSING"):
        trace_verdict = "ext-calls ceiling not measured (P8 unavailable)."
    else:
        trace_verdict = f"ext-calls probe inconclusive (P8={st('P8')}); inspect P8 detail."

    return {
        "source_level_sufficient_for_mvp_gate": core_ok,
        "source_level": source_verdict,
        "trace_deep": trace_verdict,
        "decision": (
            "MVP gate = source-level SMTChecker (Pre/Post/Exit-safety + non-reentrant "
            "Trace subset). Trace-deep + bytecode-identity remain DISCHARGEABLE leaves "
            "→ a clean source-level run is ⊥_assumptions_open, not green."
        ),
    }


# =====================================================================================
# driver
# =====================================================================================

def run(args) -> int:
    TCG_RUNS.mkdir(parents=True, exist_ok=True)
    SETUP_BUILD.mkdir(parents=True, exist_ok=True)

    _log("tcg setup-check — probing the toolchain (works-vs-wall)…")
    probes_list = [
        probe_p0(),
        probe_p1(),
        probe_p2(),
        probe_p3(),
        probe_p4(),
        probe_p5(),
        probe_p6(),
        probe_p7(getattr(args, "skip_lean", False)),
        probe_p8(),
    ]
    probes = {p["probe"]: p for p in probes_list}

    report: dict[str, object] = {
        "schema": "tcg/setup_report/v1",
        "toolchain_pins": {"solc": PIN_SOLC, "z3": PIN_Z3, "lean": PIN_LEAN},
        "probes": probes_list,
        "verify_level": verify_level(probes),
    }
    if getattr(args, "probe_neural_lean", False):
        report["neural_lean_seam"] = neural_lean_seam()

    # exit policy: WRONG dominates (setup lies → DEFECT 3); else WALL → UNKNOWN 2;
    # else GREEN 0. SKIPPED carries no exit weight.
    statuses = [p["status"] for p in probes_list]
    any_wrong = "WRONG" in statuses
    any_wall = "WALL" in statuses
    if any_wrong:
        code = Exit.DEFECT
    elif any_wall:
        code = Exit.UNKNOWN
    else:
        code = Exit.GREEN
    report["exit_code"] = int(code)

    REPORT.write_text(json.dumps(report, indent=2, ensure_ascii=False))

    # --- human-facing matrix --------------------------------------------------
    icon = {"OK": "✅", "WRONG": "❌", "WALL": "🧱", "SKIPPED": "⏭️"}
    print("\n  tcg setup-check — probe matrix")
    print("  " + "-" * 70)
    for p in probes_list:
        print(f"  {icon.get(p['status'], '?')} {p['probe']:>3}  {p['name']:<32} "
              f"{p['status']:<8} got: {p['got']}")
    print("  " + "-" * 70)
    vl = report["verify_level"]
    print(f"  verify-level: {'SOURCE-LEVEL OK' if vl['source_level_sufficient_for_mvp_gate'] else 'NOT ESTABLISHED'}")
    print(f"    · {vl['source_level']}")
    print(f"    · {vl['trace_deep']}")
    if "neural_lean_seam" in report:
        seam = report["neural_lean_seam"]
        n_repro = len(seam.get("reproduction_targets", [])) if seam.get("status") == "OK" else 0
        n_open = len(seam.get("open_frontier", [])) if seam.get("status") == "OK" else 0
        print(f"  neural_lean_seam: {seam.get('status')} "
              f"({n_repro} reproduction targets, {n_open} open frontier) → Task 0013")
    print(f"\n  report: {REPORT.relative_to(REPO)}")
    print(f"  exit {int(code)} — {('all probes OK' if code == Exit.GREEN else ('a tool is absent (WALL)' if code == Exit.UNKNOWN else 'a probe is WRONG — setup lies'))}\n")

    if getattr(args, "json", False):
        print(json.dumps(report, indent=2, ensure_ascii=False))

    return int(code)
