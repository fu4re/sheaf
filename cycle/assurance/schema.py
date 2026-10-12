"""Normative shape of an assurance package — Task 0003 (T2).

This module knows ONE thing: the *format* of the three normative files an
assurance package carries. It has zero knowledge of how those files were
produced (orchestrator / solver / LLM). Engine-aware translation lives in
`adapters/`; cross-file invariants (closure, acyclicity, evidence presence,
edge↔node status agreement) live in `verify_package.py`.

Three structures (FORMAT.md is the prose spec):

  assurance_graph.yaml   -> AssuranceGraph { claims: [Claim] }
  trusted/ledger.yaml    -> Ledger { lean_theorems, assumptions, harness_faithfulness }

A `Claim.depends_on` edge is the only link out of a claim. Its `status` is the
epistemic verb of the edge:

  proven   -> traverse further: the ref is itself discharged (another claim, or a
              Lean theorem that builds). The proof continues down the edge.
  assumed  -> stop: the ref is a *leaf of the trusted base*. We do not prove it
              here; we name it in the ledger so a reader sees exactly what is
              taken on faith.

The package's whole epistemic content is: claims, closed onto leaves, every leaf
either `proven` (and re-checkable) or `assumed` (and named in the ledger).

Structural validation here is deliberately shallow — required fields, enum
membership, evidence-shape-matches-verdict. Anything that needs to look across
files or across claims is a package invariant, not a file invariant, and is the
linter's job. Keeping that line sharp is what makes this module reusable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# --- controlled vocabularies (taxonomy from Finding 0001 + task 0003) -------

SHAPES = {"stateless", "quantified-over-mapping", "temporal-2state"}
VERDICTS = {"proven", "refuted", "inconclusive"}
EDGE_STATUSES = {"proven", "assumed"}
# what a depends_on edge can point at. `claim` recurses inside the graph; the
# others resolve into the ledger.
EDGE_KINDS = {"claim", "lean_theorem", "assumption", "harness_faithfulness"}
LEAN_BUILD_STATUSES = {"ok", "failed", "not_built"}
LEDGER_STATUSES = {"proven", "assumed"}
FAITHFULNESS_STATUSES = {"lean_proven", "diff_fuzz", "unverified"}


class SchemaError(ValueError):
    """A single file is structurally malformed (independent of other files)."""

    def __init__(self, where: str, msg: str):
        self.where = where
        super().__init__(f"{where}: {msg}")


def _req(d: dict, key: str, where: str) -> Any:
    if key not in d or d[key] is None:
        raise SchemaError(where, f"missing required field '{key}'")
    return d[key]


def _enum(val: Any, allowed: set[str], key: str, where: str) -> str:
    if val not in allowed:
        raise SchemaError(where, f"'{key}'={val!r} not in {sorted(allowed)}")
    return val


# --- assurance_graph.yaml ---------------------------------------------------


@dataclass
class Edge:
    """One outgoing dependency of a claim: {kind, ref, status, human}."""

    kind: str
    ref: str
    status: str
    human: str

    @staticmethod
    def parse(d: dict, where: str) -> "Edge":
        return Edge(
            kind=_enum(_req(d, "kind", where), EDGE_KINDS, "kind", where),
            ref=str(_req(d, "ref", where)),
            status=_enum(_req(d, "status", where), EDGE_STATUSES, "status", where),
            human=str(_req(d, "human", where)),
        )


@dataclass
class Evidence:
    """Re-checkable pointers. `{smt_query, lean_proof, reproduce}` for a verdict
    that holds; `{witness}` for refuted. Stored verbatim; the linter's evidence
    plugins decide how to replay each field."""

    raw: dict = field(default_factory=dict)

    @property
    def witness(self) -> Any:
        return self.raw.get("witness")

    @property
    def smt_query(self) -> Any:
        return self.raw.get("smt_query")

    @property
    def lean_proof(self) -> Any:
        return self.raw.get("lean_proof")

    @property
    def reproduce(self) -> Any:
        return self.raw.get("reproduce")


@dataclass
class Claim:
    id: str
    human: str
    formal: str
    shape: str
    verdict: str
    engine: str
    evidence: Evidence
    depends_on: list[Edge] = field(default_factory=list)

    @staticmethod
    def parse(d: dict) -> "Claim":
        cid = _req(d, "id", "claim")
        where = f"claim[{cid}]"
        evidence = Evidence(raw=dict(d.get("evidence") or {}))
        claim = Claim(
            id=str(cid),
            human=str(_req(d, "human", where)),
            formal=str(_req(d, "formal", where)),
            shape=_enum(_req(d, "shape", where), SHAPES, "shape", where),
            verdict=_enum(_req(d, "verdict", where), VERDICTS, "verdict", where),
            engine=str(_req(d, "engine", where)),
            evidence=evidence,
            depends_on=[
                Edge.parse(e, f"{where}.depends_on[{i}]")
                for i, e in enumerate(d.get("depends_on") or [])
            ],
        )
        claim._check_evidence_shape(where)
        return claim

    def _check_evidence_shape(self, where: str) -> None:
        """Evidence shape must match the verdict — a refuted claim without a
        witness, or a proven claim with nothing to replay, is malformed. The
        *content* (does the witness reproduce? does the query re-prove?) is a
        package invariant, checked by the linter's plugins, not here."""
        e = self.evidence
        if self.verdict == "refuted":
            if e.witness is None:
                raise SchemaError(where, "refuted claim must carry evidence.witness")
        elif self.verdict == "proven":
            if not (e.smt_query or e.lean_proof):
                raise SchemaError(
                    where,
                    "proven claim must carry evidence.smt_query or evidence.lean_proof",
                )
        # inconclusive: no evidence shape required (we are honest about not knowing)


@dataclass
class AssuranceGraph:
    claims: list[Claim]
    meta: dict = field(default_factory=dict)

    @property
    def by_id(self) -> dict[str, Claim]:
        return {c.id: c for c in self.claims}

    @staticmethod
    def parse(doc: dict) -> "AssuranceGraph":
        if not isinstance(doc, dict):
            raise SchemaError("assurance_graph", "top level must be a mapping")
        raw_claims = doc.get("claims")
        if not isinstance(raw_claims, list) or not raw_claims:
            raise SchemaError("assurance_graph", "must list at least one claim under 'claims'")
        claims = [Claim.parse(c) for c in raw_claims]
        ids = [c.id for c in claims]
        dup = {i for i in ids if ids.count(i) > 1}
        if dup:
            raise SchemaError("assurance_graph", f"duplicate claim id(s): {sorted(dup)}")
        return AssuranceGraph(claims=claims, meta=dict(doc.get("meta") or {}))

    @staticmethod
    def load(path: Path) -> "AssuranceGraph":
        return AssuranceGraph.parse(yaml.safe_load(Path(path).read_text()))


# --- trusted/ledger.yaml ----------------------------------------------------


@dataclass
class LeanTheorem:
    id: str
    statement_human: str
    statement_formal: str
    file: str
    theorem_name: str
    build_status: str
    status: str
    axioms: list[str] | None = None   # kernel #print axioms (Task 0014 Б2); None = not audited

    @staticmethod
    def parse(d: dict) -> "LeanTheorem":
        tid = _req(d, "id", "lean_theorem")
        where = f"lean_theorems[{tid}]"
        ax = d.get("axioms")
        return LeanTheorem(
            id=str(tid),
            statement_human=str(_req(d, "statement_human", where)),
            statement_formal=str(_req(d, "statement_formal", where)),
            file=str(_req(d, "file", where)),
            theorem_name=str(_req(d, "theorem_name", where)),
            build_status=_enum(_req(d, "build_status", where), LEAN_BUILD_STATUSES, "build_status", where),
            status=_enum(_req(d, "status", where), LEDGER_STATUSES, "status", where),
            axioms=list(ax) if ax is not None else None,
        )


@dataclass
class Assumption:
    id: str
    statement_human: str
    statement_formal: str
    why_assumed: str
    risk_if_false: str
    status: str

    @staticmethod
    def parse(d: dict) -> "Assumption":
        aid = _req(d, "id", "assumption")
        where = f"assumptions[{aid}]"
        return Assumption(
            id=str(aid),
            statement_human=str(_req(d, "statement_human", where)),
            statement_formal=str(_req(d, "statement_formal", where)),
            why_assumed=str(_req(d, "why_assumed", where)),
            risk_if_false=str(_req(d, "risk_if_false", where)),
            status=_enum(_req(d, "status", where), LEDGER_STATUSES, "status", where),
        )


@dataclass
class HarnessFaithfulness:
    id: str
    target: str
    claim: str
    evidence: str
    evidence_ref: str
    status: str

    @staticmethod
    def parse(d: dict) -> "HarnessFaithfulness":
        # `target` is the natural key; allow an explicit id, else fall back to target.
        target = str(_req(d, "target", "harness_faithfulness"))
        hid = str(d.get("id") or target)
        where = f"harness_faithfulness[{hid}]"
        return HarnessFaithfulness(
            id=hid,
            target=target,
            claim=str(_req(d, "claim", where)),
            evidence=str(_req(d, "evidence", where)),
            evidence_ref=str(_req(d, "evidence_ref", where)),
            status=_enum(_req(d, "status", where), FAITHFULNESS_STATUSES, "status", where),
        )


@dataclass
class Ledger:
    lean_theorems: list[LeanTheorem] = field(default_factory=list)
    assumptions: list[Assumption] = field(default_factory=list)
    harness_faithfulness: list[HarnessFaithfulness] = field(default_factory=list)
    meta: dict = field(default_factory=dict)

    @property
    def ids(self) -> set[str]:
        """Every leaf id the graph is allowed to reference."""
        out: set[str] = set()
        for group in (self.lean_theorems, self.assumptions, self.harness_faithfulness):
            out.update(x.id for x in group)
        return out

    def resolve(self, ref: str) -> Any:
        for group in (self.lean_theorems, self.assumptions, self.harness_faithfulness):
            for x in group:
                if x.id == ref:
                    return x
        return None

    @staticmethod
    def parse(doc: dict) -> "Ledger":
        if not isinstance(doc, dict):
            raise SchemaError("ledger", "top level must be a mapping")
        ledger = Ledger(
            lean_theorems=[LeanTheorem.parse(x) for x in (doc.get("lean_theorems") or [])],
            assumptions=[Assumption.parse(x) for x in (doc.get("assumptions") or [])],
            harness_faithfulness=[
                HarnessFaithfulness.parse(x) for x in (doc.get("harness_faithfulness") or [])
            ],
            meta=dict(doc.get("meta") or {}),
        )
        all_ids = [x.id for group in (ledger.lean_theorems, ledger.assumptions,
                                      ledger.harness_faithfulness) for x in group]
        dup = {i for i in all_ids if all_ids.count(i) > 1}
        if dup:
            raise SchemaError("ledger", f"duplicate leaf id(s) across ledger: {sorted(dup)}")
        return ledger

    @staticmethod
    def load(path: Path) -> "Ledger":
        return Ledger.parse(yaml.safe_load(Path(path).read_text()))
