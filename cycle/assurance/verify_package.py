"""verify_package.py — the assurance-package linter.

Mechanically checks the package invariant (FORMAT.md). Works ONLY on the files in
a package directory; it has no idea what produced them. That is the point: a third
party re-checks the package backwards with this one tool.

Two layers of checking:

  static (default)   structure + cross-file invariants, PyYAML the only dependency.
                     closure · acyclicity · evidence-present · edge-honesty ·
                     ledger-consistency. This is what an auditor runs first.
  --replay           additionally RE-RUNS the evidence: re-invoke solc on the saved
                     SMT harness, `lake build` the Lean proof, and check the recorded
                     verdict/build_status did not lie. Needs the toolchain present.

Three statuses (gate-integrity, ADR/AGENTS):

  PASS      check held.
  FLAG      the package invariant is violated — a real defect.
  BLOCKED   the check could not be completed (missing tool, unreadable file). NOT
            a pass. "Couldn't verify" is never green.

Package verdict rolls up:

  any FLAG     -> INVALID       (exit 1)
  else BLOCKED -> BLOCKED       (exit 2)
  else         -> WELL-FORMED   (exit 0)

The hidden-assumption demo (acceptance #4): delete a leaf from ledger.yaml that an
edge depends on -> closure FLAGs -> INVALID -> exit 1.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # cycle/ on path

from assurance import axiom_audit  # noqa: E402
from assurance.schema import (  # noqa: E402
    AssuranceGraph,
    Edge,
    Ledger,
    SchemaError,
)

# --- finding model ----------------------------------------------------------

PASS, FLAG, BLOCKED = "PASS", "FLAG", "BLOCKED"


@dataclass
class Finding:
    check: str
    status: str
    message: str
    ref: str | None = None


@dataclass
class Report:
    findings: list[Finding] = field(default_factory=list)

    def add(self, check: str, status: str, message: str, ref: str | None = None) -> None:
        self.findings.append(Finding(check, status, message, ref))

    @property
    def verdict(self) -> str:
        if any(f.status == FLAG for f in self.findings):
            return "INVALID"
        if any(f.status == BLOCKED for f in self.findings):
            return "BLOCKED"
        return "WELL-FORMED"

    @property
    def exit_code(self) -> int:
        return {"WELL-FORMED": 0, "INVALID": 1, "BLOCKED": 2}[self.verdict]


# --- ledger leaf typing -----------------------------------------------------

# which ledger group an edge kind must resolve into.
_KIND_GROUP = {
    "lean_theorem": "lean_theorems",
    "assumption": "assumptions",
    "harness_faithfulness": "harness_faithfulness",
}


def _ledger_group_of(ledger: Ledger, ref: str) -> str | None:
    if any(x.id == ref for x in ledger.lean_theorems):
        return "lean_theorems"
    if any(x.id == ref for x in ledger.assumptions):
        return "assumptions"
    if any(x.id == ref for x in ledger.harness_faithfulness):
        return "harness_faithfulness"
    return None


# --- static checks ----------------------------------------------------------


def check_closure(graph: AssuranceGraph, ledger: Ledger, rep: Report) -> None:
    """Every edge ref resolves, into the graph (kind=claim) or the ledger (else).
    A leaf an edge depends on but that is absent from the ledger is a HIDDEN
    ASSUMPTION -> FLAG. This is the check the acceptance demo trips."""
    by_id = graph.by_id
    for claim in graph.claims:
        for e in claim.depends_on:
            tag = f"{claim.id} -> {e.ref}"
            if e.kind == "claim":
                if e.ref not in by_id:
                    rep.add("closure", FLAG, f"edge to claim '{e.ref}' that does not exist", tag)
                continue
            group = _ledger_group_of(ledger, e.ref)
            if group is None:
                rep.add(
                    "closure", FLAG,
                    f"depends on leaf '{e.ref}' absent from ledger.yaml "
                    f"(hidden assumption / dangling leaf)", tag,
                )
            elif group != _KIND_GROUP[e.kind]:
                rep.add(
                    "closure", FLAG,
                    f"edge kind '{e.kind}' but '{e.ref}' is a {group} entry", tag,
                )
            else:
                rep.add("closure", PASS, f"{e.kind} '{e.ref}' present in ledger", tag)


def check_acyclicity(graph: AssuranceGraph, rep: Report) -> None:
    """The claim graph (kind=claim edges) must be a DAG."""
    by_id = graph.by_id
    adj: dict[str, list[str]] = {
        c.id: [e.ref for e in c.depends_on if e.kind == "claim" and e.ref in by_id]
        for c in graph.claims
    }
    WHITE, GREY, BLACK = 0, 1, 2
    color = {cid: WHITE for cid in by_id}
    cycle: list[str] = []

    def visit(u: str, stack: list[str]) -> bool:
        color[u] = GREY
        for v in adj[u]:
            if color[v] == GREY:
                cycle.extend(stack[stack.index(v):] + [v])
                return True
            if color[v] == WHITE and visit(v, stack + [v]):
                return True
        color[u] = BLACK
        return False

    for cid in by_id:
        if color[cid] == WHITE and visit(cid, [cid]):
            rep.add("acyclicity", FLAG, f"cycle in claim graph: {' -> '.join(cycle)}")
            return
    rep.add("acyclicity", PASS, f"claim graph is a DAG ({len(by_id)} claims)")


def check_edge_honesty(graph: AssuranceGraph, ledger: Ledger, rep: Report) -> None:
    """An edge labelled `proven` may not resolve to something only `assumed`. You
    cannot relabel a thing taken on faith as a thing you proved."""
    by_id = graph.by_id
    for claim in graph.claims:
        for e in claim.depends_on:
            if e.status != "proven":
                continue  # `assumed` edges are always honest (they stop, under-claiming)
            tag = f"{claim.id} -> {e.ref}"
            if e.kind == "claim":
                target = by_id.get(e.ref)
                if target is None:
                    continue  # already FLAGged by closure
                if target.verdict != "proven":
                    rep.add("edge-honesty", FLAG,
                            f"proven edge into claim '{e.ref}' whose verdict is "
                            f"'{target.verdict}'", tag)
                else:
                    rep.add("edge-honesty", PASS, f"proven edge into proven claim '{e.ref}'", tag)
            elif e.kind == "lean_theorem":
                th = ledger.resolve(e.ref)
                if th is None:
                    continue
                if getattr(th, "build_status", None) != "ok" or th.status != "proven":
                    rep.add("edge-honesty", FLAG,
                            f"proven edge to Lean theorem '{e.ref}' with "
                            f"build_status={getattr(th,'build_status',None)!r} "
                            f"status={th.status!r}", tag)
                else:
                    rep.add("edge-honesty", PASS, f"proven edge to built Lean theorem '{e.ref}'", tag)
            elif e.kind == "assumption":
                rep.add("edge-honesty", FLAG,
                        f"edge labelled 'proven' resolves to an ASSUMED leaf '{e.ref}' "
                        f"(an assumption dressed as a proof)", tag)
            elif e.kind == "harness_faithfulness":
                hf = ledger.resolve(e.ref)
                if hf is None:
                    continue
                if hf.status != "lean_proven":
                    rep.add("edge-honesty", FLAG,
                            f"proven edge to harness_faithfulness '{e.ref}' with "
                            f"status '{hf.status}' (only 'lean_proven' counts as proven)", tag)
                else:
                    rep.add("edge-honesty", PASS, f"proven edge to lean_proven faithfulness '{e.ref}'", tag)


def check_evidence_present(graph: AssuranceGraph, pkg: Path, rep: Report) -> None:
    """A package must be self-contained: every file the evidence cites exists under
    the package root. A proven claim whose evidence file is missing is not
    re-checkable -> FLAG."""
    for claim in graph.claims:
        ev = claim.evidence
        if claim.verdict == "refuted":
            if not ev.witness:
                rep.add("evidence", FLAG, "refuted claim carries no witness", claim.id)
            else:
                rep.add("evidence", PASS, "refuted claim carries witness", claim.id)
            continue
        if claim.verdict == "inconclusive":
            rep.add("evidence", PASS, "inconclusive claim (no evidence required, honest)", claim.id)
            continue
        # proven: each cited file must exist.
        cited = [("smt_query", ev.smt_query), ("lean_proof", ev.lean_proof)]
        any_present = False
        for fieldname, val in cited:
            if not val:
                continue
            any_present = True
            target = pkg / val
            if target.exists():
                rep.add("evidence", PASS, f"{fieldname} file present: {val}", claim.id)
            else:
                rep.add("evidence", FLAG, f"{fieldname} file missing from package: {val}", claim.id)
        if not any_present:
            rep.add("evidence", FLAG, "proven claim cites no smt_query/lean_proof file", claim.id)


# A clean Mathlib proof may depend ONLY on these (mirrors emit._ALLOWED_AXIOMS /
# axiom_audit.ALLOWED_AXIOMS). sorryAx or any contract axiom => NOT a proof (Task 0014 Б2).
_ALLOWED_AXIOMS = axiom_audit.ALLOWED_AXIOMS
# a lean_theorem's `theorem_name` may name >1 theorem — pull the dotted identifiers out.
_THEOREM_TOKEN = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z0-9_']+)+")


def check_ledger_consistency(ledger: Ledger, rep: Report) -> None:
    """Internal honesty of the ledger: a Lean leaf marked proven must report a
    successful build AND a clean kernel axiom audit — a build pass is NOT a proof
    (a `sorry` also builds; Task 0014 Б2). A proven leaf carrying dirty `axioms`
    (⊄ allowed, or `sorryAx`) is flagged here; a proven leaf with no axioms field
    is re-derived by `--replay` (backward-compatible with pre-audit packages)."""
    for th in ledger.lean_theorems:
        if th.status == "proven" and th.build_status != "ok":
            rep.add("ledger", FLAG,
                    f"lean_theorem '{th.id}' status=proven but build_status={th.build_status!r}",
                    th.id)
        elif th.status == "proven" and th.axioms is not None and \
                not all(a in _ALLOWED_AXIOMS for a in th.axioms):
            rep.add("ledger", FLAG,
                    f"lean_theorem '{th.id}' status=proven but axiom audit is DIRTY: {th.axioms} "
                    f"⊄ {sorted(_ALLOWED_AXIOMS)} — build-pass ≠ proof (sorryAx / contract axiom)",
                    th.id)
        else:
            note = "clean-audit" if th.axioms is not None else "build-only (axioms re-derived on --replay)"
            rep.add("ledger", PASS, f"lean_theorem '{th.id}' status/build consistent ({note})", th.id)
    for hf in ledger.harness_faithfulness:
        # a 'lean_proven' faithfulness leaf had better point at a Lean theorem id.
        if hf.status == "lean_proven" and ledger.resolve(hf.evidence_ref) is None and \
                not any(t.id == hf.evidence_ref for t in ledger.lean_theorems):
            rep.add("ledger", FLAG,
                    f"harness_faithfulness '{hf.id}' is lean_proven but evidence_ref "
                    f"'{hf.evidence_ref}' resolves to no lean_theorem", hf.id)
        else:
            rep.add("ledger", PASS, f"harness_faithfulness '{hf.id}' recorded ({hf.status})", hf.id)


# --- replay plugins (opt-in, engine-aware but registered, not hard-wired) ----

EVIDENCE_REPLAYERS: dict[str, "callable"] = {}


def register_replayer(engine: str):
    def deco(fn):
        EVIDENCE_REPLAYERS[engine] = fn
        return fn
    return deco


@register_replayer("smt")
def _replay_smt(claim, pkg: Path, rep: Report) -> None:
    """Re-run the SMT harness through solc and check the recorded verdict holds.
    solc absent -> BLOCKED (precondition), not a pass."""
    harness = claim.evidence.smt_query
    if not harness:
        return
    sol = pkg / harness
    if not sol.exists():
        rep.add("replay:smt", BLOCKED, f"harness not found: {harness}", claim.id)
        return
    import shutil
    solc = shutil.which("solc") or "/opt/homebrew/bin/solc"
    if not Path(solc).exists() and not shutil.which("solc"):
        rep.add("replay:smt", BLOCKED, "solc not on PATH", claim.id)
        return
    cmd = [solc, "--model-checker-engine", "chc", "--model-checker-targets", "assert",
           "--model-checker-solvers", "z3", "--model-checker-timeout", "20000", str(sol)]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, OSError) as exc:
        rep.add("replay:smt", BLOCKED, f"solc invocation failed: {exc}", claim.id)
        return
    blob = out.stdout + out.stderr
    proved = "proved safe" in blob
    refuted = "CHC: " in blob and ("Counterexample" in blob or "violation" in blob.lower())
    if claim.verdict == "proven" and proved:
        rep.add("replay:smt", PASS, "solc re-proved the harness safe", claim.id)
    elif claim.verdict == "refuted" and refuted:
        rep.add("replay:smt", PASS, "solc re-found the counterexample", claim.id)
    else:
        rep.add("replay:smt", FLAG,
                f"recorded verdict '{claim.verdict}' not reproduced "
                f"(proved={proved} refuted={refuted})", claim.id)


def run_replay(graph: AssuranceGraph, ledger: Ledger, pkg: Path, rep: Report) -> None:
    for claim in graph.claims:
        # dispatch by a coarse engine tag mined from the claim's `engine` string.
        eng = (claim.engine or "").lower()
        if "chc" in eng or "bmc" in eng or "smt" in eng or "z3" in eng or "cvc" in eng:
            _replay_smt(claim, pkg, rep)
        # lean replay (lake build) is dispatched off ledger lean_theorems below.
    # Lean: build each proven lean_theorem the graph leans on, then re-derive its axioms.
    _replay_lean(graph, ledger, pkg, rep)


def _replay_lean(graph: AssuranceGraph, ledger: Ledger, pkg: Path, rep: Report) -> None:
    """`lake build` the Lean project backing proven lean_theorem leaves AND re-derive
    each proven leaf's `#print axioms` from the kernel — a build pass is not a proof
    (a `sorry` builds too; Task 0014 Б2). Project / lake absent -> BLOCKED."""
    import shutil
    # collect lean theorem ids the graph actually depends on
    refs = {e.ref for c in graph.claims for e in c.depends_on if e.kind == "lean_theorem"}
    if not refs:
        return
    if not shutil.which("lake"):
        rep.add("replay:lean", BLOCKED, "lake not on PATH (Lean toolchain absent)")
        return
    # the build log packaged under evidence/lean/ records the canonical project path
    manifest = pkg / "evidence" / "lean" / "lean_project.json"
    if not manifest.exists():
        rep.add("replay:lean", BLOCKED,
                "no evidence/lean/lean_project.json pointing at the lake project")
        return
    info = json.loads(manifest.read_text())
    proj = Path(info["project"])
    if not proj.is_absolute():
        proj = (pkg / proj).resolve()
    if not (proj / "lakefile.toml").exists() and not (proj / "lakefile.lean").exists():
        rep.add("replay:lean", BLOCKED, f"lake project not found at {proj}")
        return
    try:
        out = subprocess.run(["lake", "build"], cwd=str(proj), capture_output=True,
                             text=True, timeout=600)
    except (subprocess.TimeoutExpired, OSError) as exc:
        rep.add("replay:lean", BLOCKED, f"lake build failed to run: {exc}")
        return
    if out.returncode != 0:
        rep.add("replay:lean", FLAG,
                f"lake build FAILED (rc={out.returncode}) — ledger build_status lies")
        return
    rep.add("replay:lean", PASS, f"lake build green ({proj.name}) for {sorted(refs)}")

    # Б2: re-derive #print axioms from the kernel and cross-check every PROVEN leaf.
    audit = axiom_audit.run(proj, module=info.get("audit_module", "AaveArith.AxiomAudit"))
    if not audit.available:
        rep.add("replay:lean-axioms", BLOCKED,
                f"axiom re-derivation unavailable ({audit.reason}) — proven leaves not re-audited")
        return
    for th in ledger.lean_theorems:
        if th.status != "proven" or th.id not in refs:
            continue
        names = _THEOREM_TOKEN.findall(th.theorem_name or "")
        per = [audit.axioms_for(n) for n in names]
        covered = [a for a in per if a is not None]
        if not names or len(covered) != len(names):
            rep.add("replay:lean-axioms", BLOCKED,
                    f"'{th.id}': audit did not cover {names} — cannot re-derive", th.id)
            continue
        rederived = sorted({a for lst in covered for a in lst})
        if not all(a in _ALLOWED_AXIOMS for a in rederived):
            rep.add("replay:lean-axioms", FLAG,
                    f"'{th.id}' status=proven but KERNEL re-derivation is DIRTY: {rederived} "
                    f"(build-pass ≠ proof)", th.id)
        else:
            rep.add("replay:lean-axioms", PASS,
                    f"'{th.id}' kernel-re-audited clean: {rederived}", th.id)


# --- render-rule (Finding 0007): cap the top status by the weakest leaf --------
# A top claim's SMT verdict may be `proven`, yet if a path to it ends in an OPEN
# DISCHARGEABLE leaf (bytecode-identity unverified, or a deferred φ dimension), the
# package must NOT be rendered/declared green over it — that is the exact false-green
# Finding 0007:55 caught. This is a machine-checked invariant, not cosmetics: the
# package's self-declared `meta.assurance_level` must agree with the leaf-derived cap.

_GREEN_LEVELS = {"verified", "green", "verified(b,φ)"}


def _leaf_class_map(ledger_path: Path) -> dict[str, str]:
    """Raw leaf_class per ledger leaf. assumptions/faithfulness may carry an explicit
    `leaf_class: irreducible|dischargeable`; a built lean_theorem leaf is `discharged`.
    Conservative default for an unlabelled assumption is `dischargeable` (cannot silently
    count as irreducible)."""
    import yaml as _yaml
    raw = _yaml.safe_load(Path(ledger_path).read_text()) or {}
    classes: dict[str, str] = {}
    for a in raw.get("assumptions", []) or []:
        classes[a["id"]] = a.get("leaf_class", "dischargeable")
    for h in raw.get("harness_faithfulness", []) or []:
        classes[h["id"]] = h.get("leaf_class", "dischargeable")
    for lt in raw.get("lean_theorems", []) or []:
        classes[lt["id"]] = "discharged"
    return classes


def _top_claims(graph: AssuranceGraph) -> list:
    depended = {e.ref for c in graph.claims for e in c.depends_on if e.kind == "claim"}
    return [c for c in graph.claims if c.id not in depended]


def _open_dischargeable_on_path(graph: AssuranceGraph, ledger: Ledger, claim,
                                classes: dict[str, str], seen: set | None = None) -> list[str]:
    seen = seen if seen is not None else set()
    if claim.id in seen:
        return []
    seen.add(claim.id)
    out: list[str] = []
    for e in claim.depends_on:
        if e.kind == "claim":
            t = graph.by_id.get(e.ref)
            if t:
                out += _open_dischargeable_on_path(graph, ledger, t, classes, seen)
        elif e.kind == "harness_faithfulness":
            hf = ledger.resolve(e.ref)
            if hf is not None and hf.status != "lean_proven":  # an unverified/diff_fuzz leaf is open
                out.append(e.ref)
        elif e.kind == "assumption":
            if classes.get(e.ref, "dischargeable") == "dischargeable":
                out.append(e.ref)
        # lean_theorem (proven, built) → discharged, not open
    return out


def check_render_cap(graph: AssuranceGraph, ledger: Ledger, ledger_path: Path, rep: Report) -> None:
    classes = _leaf_class_map(ledger_path)
    declared = str(graph.meta.get("assurance_level", "")).strip().lower()
    for claim in _top_claims(graph):
        if claim.verdict != "proven":
            rep.add("render-cap", PASS,
                    f"top claim '{claim.id}' verdict={claim.verdict} — not a green candidate", claim.id)
            continue
        open_leaves = sorted(set(_open_dischargeable_on_path(graph, ledger, claim, classes)))
        effective = "⊥_assumptions_open" if open_leaves else "verified_under_irreducible_assumptions"
        if open_leaves and declared in _GREEN_LEVELS:
            rep.add("render-cap", FLAG,
                    f"top claim '{claim.id}' declared green ('{graph.meta.get('assurance_level')}') "
                    f"but open DISCHARGEABLE leaves {open_leaves} cap it below green — false green",
                    claim.id)
        else:
            rep.add("render-cap", PASS,
                    f"top claim '{claim.id}' effective render: {effective}"
                    + (f" (open dischargeable: {open_leaves})" if open_leaves else ""), claim.id)


# --- driver -----------------------------------------------------------------


def lint(pkg: Path, replay: bool = False) -> Report:
    rep = Report()
    graph_path = pkg / "assurance_graph.yaml"
    ledger_path = pkg / "trusted" / "ledger.yaml"
    if not graph_path.exists():
        rep.add("load", BLOCKED, f"missing {graph_path.name}")
        return rep
    if not ledger_path.exists():
        rep.add("load", BLOCKED, f"missing trusted/ledger.yaml")
        return rep
    try:
        graph = AssuranceGraph.load(graph_path)
        ledger = Ledger.load(ledger_path)
    except SchemaError as e:
        rep.add("load", FLAG, f"structural: {e}")
        return rep
    except Exception as e:  # malformed YAML, etc.
        rep.add("load", BLOCKED, f"could not parse package: {e}")
        return rep

    check_closure(graph, ledger, rep)
    check_acyclicity(graph, rep)
    check_edge_honesty(graph, ledger, rep)
    check_evidence_present(graph, pkg, rep)
    check_ledger_consistency(ledger, rep)
    check_render_cap(graph, ledger, ledger_path, rep)
    if replay:
        run_replay(graph, ledger, pkg, rep)
    return rep


def _print_report(rep: Report, pkg: Path, verbose: bool) -> None:
    icon = {PASS: "  ok ", FLAG: " FLAG", BLOCKED: "BLOCK"}
    print(f"assurance package: {pkg}")
    print("-" * 72)
    for f in rep.findings:
        if f.status == PASS and not verbose:
            continue
        ref = f" [{f.ref}]" if f.ref else ""
        print(f"  [{icon[f.status]}] {f.check}{ref}: {f.message}")
    n_pass = sum(1 for f in rep.findings if f.status == PASS)
    n_flag = sum(1 for f in rep.findings if f.status == FLAG)
    n_block = sum(1 for f in rep.findings if f.status == BLOCKED)
    print("-" * 72)
    print(f"  {n_pass} pass · {n_flag} flag · {n_block} blocked")
    print(f"  VERDICT: {rep.verdict}  (exit {rep.exit_code})")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Assurance package linter (Task 0003 / T2).")
    ap.add_argument("package", help="path to the package directory")
    ap.add_argument("--replay", action="store_true",
                    help="re-run evidence (solc / lake build); needs the toolchain")
    ap.add_argument("--json", action="store_true", help="emit findings as JSON")
    ap.add_argument("-v", "--verbose", action="store_true", help="show PASS findings too")
    args = ap.parse_args(argv)

    pkg = Path(args.package).resolve()
    rep = lint(pkg, replay=args.replay)

    if args.json:
        print(json.dumps({
            "package": str(pkg),
            "verdict": rep.verdict,
            "exit_code": rep.exit_code,
            "findings": [f.__dict__ for f in rep.findings],
        }, indent=2))
    else:
        _print_report(rep, pkg, args.verbose)
    return rep.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
