"""render_audit.py — auto-generate view/AUDIT.md from the package core.

A human-navigable projection of assurance_graph.yaml + trusted/ledger.yaml. It is
generated, never hand-kept: the single source of truth stays the core, so the audit
view cannot drift from what the linter checks. This is the document a blind reviewer
walks top-down (acceptance #7) — it must let them decide each leaf without asking the
session author.

Includes a GSN-style projection as a Mermaid diagram (renders in any markdown viewer;
no graphviz dependency).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))  # cycle/ on path

from assurance.schema import AssuranceGraph, Claim, Ledger  # noqa: E402

_V = {"proven": "✅ proven", "refuted": "❌ refuted (witness)", "inconclusive": "⚠️ inconclusive"}


def _topo(graph: AssuranceGraph) -> list[Claim]:
    """Roots (claims nothing depends on) first, then dependencies — the walk order."""
    by_id = graph.by_id
    depended_on = {e.ref for c in graph.claims for e in c.depends_on if e.kind == "claim"}
    roots = [c for c in graph.claims if c.id not in depended_on]
    seen: list[str] = []
    order: list[Claim] = []

    def visit(c: Claim) -> None:
        if c.id in seen:
            return
        seen.append(c.id)
        order.append(c)
        for e in c.depends_on:
            if e.kind == "claim" and e.ref in by_id:
                visit(by_id[e.ref])

    for r in roots:
        visit(r)
    for c in graph.claims:  # any not reached (shouldn't happen in a DAG)
        visit(c)
    return order


def _mermaid(graph: AssuranceGraph, ledger: Ledger) -> str:
    lines = ["```mermaid", "flowchart TD"]
    shape = {
        "claim_proven": ('["', '"]'),
        "claim_refuted": ('{{"', '"}}'),
        "claim_inconclusive": ('["', '"]'),
        "lean_theorem": ('[/"', '"/]'),
        "assumption": ('(["', '"])'),
        "harness_faithfulness": ('>"', '"]'),
    }
    seen_leaf: set[str] = set()
    for c in graph.claims:
        key = f"claim_{c.verdict}"
        o, cl = shape.get(key, ('["', '"]'))
        lines.append(f'  {c.id}{o}{c.id}: {c.human.strip().splitlines()[0][:60]}{cl}')
    for c in graph.claims:
        for e in c.depends_on:
            if e.kind == "claim":
                lines.append(f'  {c.id} -- {e.status} --> {e.ref}')
            else:
                if e.ref not in seen_leaf:
                    o, cl = shape.get(e.kind, ('["', '"]'))
                    label = e.ref
                    entry = ledger.resolve(e.ref)
                    if entry is not None:
                        h = getattr(entry, "statement_human", None) or getattr(entry, "claim", "")
                        label = f"{e.ref}: {h[:48]}"
                    lines.append(f'  {e.ref}{o}{label}{cl}')
                    seen_leaf.add(e.ref)
                lines.append(f'  {c.id} -. {e.status} .-> {e.ref}')
    lines += [
        "  classDef proven fill:#d4f7d4,stroke:#2a2;",
        "  classDef refuted fill:#f7d4d4,stroke:#a22;",
        "  classDef assumed fill:#fff3cd,stroke:#a80;",
    ]
    proven_ids = [c.id for c in graph.claims if c.verdict == "proven"]
    refuted_ids = [c.id for c in graph.claims if c.verdict == "refuted"]
    assumed_ids = [a.id for a in ledger.assumptions] + [h.id for h in ledger.harness_faithfulness]
    if proven_ids:
        lines.append(f"  class {','.join(proven_ids)} proven;")
    if refuted_ids:
        lines.append(f"  class {','.join(refuted_ids)} refuted;")
    if assumed_ids:
        lines.append(f"  class {','.join(assumed_ids)} assumed;")
    lines.append("```")
    return "\n".join(lines)


def render(pkg: Path) -> str:
    graph = AssuranceGraph.load(pkg / "assurance_graph.yaml")
    ledger = Ledger.load(pkg / "trusted" / "ledger.yaml")
    meta = graph.meta
    out: list[str] = []
    A = out.append

    A(f"# Assurance audit — {meta.get('contract', '(unnamed)')}")
    A("")
    A("> **AUTO-GENERATED** from `assurance_graph.yaml` + `trusted/ledger.yaml`. "
      "Do not edit; regenerate with `python -m assurance.render_audit <pkg>`.")
    A("")
    if meta.get("note"):
        A("> " + meta["note"].strip().replace("\n", "\n> "))
        A("")

    # TL;DR
    depended = {e.ref for c in graph.claims for e in c.depends_on if e.kind == "claim"}
    tops = [c for c in graph.claims if c.id not in depended]
    A("## TL;DR for the auditor")
    A("")
    for c in tops:
        A(f"- **Top claim {c.id}** — {c.human.strip().splitlines()[0]} — **{_V.get(c.verdict, c.verdict)}**")
        A(f"  - exact formula: `{c.formal}`")
    n_assume = len(ledger.assumptions) + sum(1 for h in ledger.harness_faithfulness if h.status != 'lean_proven')
    A(f"- You are trusting **{n_assume} leaf assumption(s)** + "
      f"**{len(ledger.lean_theorems)} Lean theorem(s)** (kernel-checked). Decide each below.")
    A("- Re-check everything, backwards, without the session:")
    A(f"  ```\n  python -m assurance.verify_package {pkg.name} --replay\n  ```")
    A("")

    # GSN
    A("## Claim graph (GSN projection)")
    A("")
    A(_mermaid(graph, ledger))
    A("")
    A("Legend: `[ ]` claim · `[/ /]` Lean theorem (kernel) · `([ ])` assumption · "
      "`> ]` harness-faithfulness. Solid arrow = claim→claim; dotted = claim→leaf.")
    A("")

    # Claims walk
    A("## Claims (walk top-down)")
    A("")
    for c in _topo(graph):
        A(f"### {c.id} — {_V.get(c.verdict, c.verdict)}")
        A("")
        A(f"{c.human.strip()}")
        A("")
        A(f"- **formal:** `{c.formal}`")
        A(f"- **shape:** {c.shape} · **engine:** {c.engine}")
        ev = c.evidence
        if c.verdict == "refuted" and ev.witness:
            A(f"- **witness:** `{ev.witness}`")
        if ev.smt_query:
            A(f"- **evidence (SMT):** `{ev.smt_query}`")
        if ev.lean_proof:
            A(f"- **evidence (Lean):** `{ev.lean_proof}`")
        if ev.reproduce:
            A(f"- **reproduce:** `{ev.reproduce}`")
        if c.depends_on:
            A("- **depends on:**")
            for e in c.depends_on:
                A(f"    - `[{e.status}]` → **{e.ref}** ({e.kind}): {e.human}")
        A("")

    # Trusted base
    A("## Trusted base — the leaves you must accept")
    A("")
    A("### Lean theorems (discharged by the Lean kernel)")
    A("")
    if ledger.lean_theorems:
        for t in ledger.lean_theorems:
            A(f"- **{t.id}** — {t.statement_human}")
            A(f"  - `{t.statement_formal}`")
            A(f"  - theorem `{t.theorem_name}` in `{t.file}` — build: **{t.build_status}** ({t.status})")
    else:
        A("- (none)")
    A("")
    A("### Assumptions (taken on faith — decide each)")
    A("")
    if ledger.assumptions:
        for a in ledger.assumptions:
            A(f"- **{a.id}** — {a.statement_human}")
            A(f"  - formal: `{a.statement_formal}`")
            A(f"  - **why assumed:** {a.why_assumed.strip()}")
            A(f"  - **risk if false:** {a.risk_if_false.strip()}")
    else:
        A("- (none)")
    A("")
    A("### Harness faithfulness (model ↔ deployed bytecode — the moat)")
    A("")
    if ledger.harness_faithfulness:
        for h in ledger.harness_faithfulness:
            A(f"- **{h.id}** — target `{h.target}` — status: **{h.status}**")
            A(f"  - claim: {h.claim}")
            A(f"  - evidence: {h.evidence} (`{h.evidence_ref}`)")
    else:
        A("- (none)")
    A("")
    A("---")
    A("*The product is the epistemic claim above plus this bounded, re-checkable list "
      "of assumptions. Accept the leaves, or reject one — that is the whole audit.*")
    A("")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Auto-generate view/AUDIT.md from a package.")
    ap.add_argument("package")
    ap.add_argument("-o", "--out", default=None, help="default: <package>/view/AUDIT.md")
    args = ap.parse_args(argv)
    pkg = Path(args.package).resolve()
    md = render(pkg)
    out = Path(args.out) if args.out else pkg / "view" / "AUDIT.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(md)
    print(f"wrote {out} ({len(md)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
