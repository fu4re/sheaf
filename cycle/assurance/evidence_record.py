"""evidence_record.py — the stable contract a component emits per checked fact.

One record = one atomic result of one tool run: an SMT solve, a Lean build, one
mined-guarantee verdict. It carries NO graph topology and NO trusted-base judgment
— it does not know whether it is a top claim, a proven edge, or an assumed leaf.
That composition is the assembler's job (assemble.py), driven by a human-authored
spine. Keeping records judgment-free is what lets any backend emit them.

A record is the format's vocabulary already: `verdict`, `engine`, `evidence`,
`shape`. A component fills these from its own native output via emit.py — there is
no translation step, which is the whole point of the hybrid (see FORMAT.md).

The envelope is uniform across kinds so the assembler treats SMT, Lean and mining
results the same way:

  record_id     stable id, referenced from the spine
  kind          smt_solve | lean_theorem | guarantee_mining | <your component's>
  produced_by   provenance of THIS record (component, version, backend)
  subject       what was checked: {human, formal, shape}
  result        {verdict, witness, engine, reproduce, raw_ref}
  artifacts     files this record points at (harness .sol, Lean file) — package-relative
                once assembled, absolute/repo-relative when freshly emitted
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

# verdicts a record may carry. Broader than the claim vocabulary on purpose: a
# component may report `unknown` (solver budget) or `unreachable` (vacuous); the
# assembler/spine decides how those map onto a claim verdict, honestly.
RECORD_VERDICTS = {"proven", "refuted", "inconclusive", "unknown", "unreachable", "not_built"}


class RecordError(ValueError):
    pass


def _req(d: dict, key: str, where: str) -> Any:
    if key not in d or d[key] is None:
        raise RecordError(f"{where}: missing required field '{key}'")
    return d[key]


@dataclass
class Subject:
    human: str
    formal: str
    shape: str | None = None


@dataclass
class Result:
    verdict: str
    engine: str
    witness: Any = None
    reproduce: str | None = None
    raw_ref: str | None = None


@dataclass
class EvidenceRecord:
    record_id: str
    kind: str
    subject: Subject
    result: Result
    produced_by: dict = field(default_factory=dict)
    artifacts: list[str] = field(default_factory=list)
    extra: dict = field(default_factory=dict)  # component-specific, never inspected by core

    @staticmethod
    def parse(d: dict) -> "EvidenceRecord":
        rid = _req(d, "record_id", "record")
        where = f"record[{rid}]"
        subj = _req(d, "subject", where)
        res = _req(d, "result", where)
        verdict = _req(res, "verdict", f"{where}.result")
        if verdict not in RECORD_VERDICTS:
            raise RecordError(f"{where}.result: verdict {verdict!r} not in {sorted(RECORD_VERDICTS)}")
        return EvidenceRecord(
            record_id=str(rid),
            kind=str(_req(d, "kind", where)),
            subject=Subject(
                human=str(_req(subj, "human", f"{where}.subject")),
                formal=str(_req(subj, "formal", f"{where}.subject")),
                shape=subj.get("shape"),
            ),
            result=Result(
                verdict=str(verdict),
                engine=str(_req(res, "engine", f"{where}.result")),
                witness=res.get("witness"),
                reproduce=res.get("reproduce"),
                raw_ref=res.get("raw_ref"),
            ),
            produced_by=dict(d.get("produced_by") or {}),
            artifacts=list(d.get("artifacts") or []),
            extra=dict(d.get("extra") or {}),
        )

    def to_dict(self) -> dict:
        out: dict[str, Any] = {
            "record_id": self.record_id,
            "kind": self.kind,
            "produced_by": self.produced_by,
            "subject": {"human": self.subject.human, "formal": self.subject.formal},
            "result": {"verdict": self.result.verdict, "engine": self.result.engine},
            "artifacts": self.artifacts,
        }
        if self.subject.shape:
            out["subject"]["shape"] = self.subject.shape
        for k in ("witness", "reproduce", "raw_ref"):
            v = getattr(self.result, k)
            if v is not None:
                out["result"][k] = v
        if self.extra:
            out["extra"] = self.extra
        return out

    @staticmethod
    def load(path: Path) -> "EvidenceRecord":
        return EvidenceRecord.parse(yaml.safe_load(Path(path).read_text()))

    def dump(self, path: Path) -> None:
        Path(path).write_text(yaml.safe_dump(self.to_dict(), sort_keys=False, allow_unicode=True))


def load_records(directory: Path) -> dict[str, EvidenceRecord]:
    """Load every *.record.yaml (or *.record.json) under a directory, keyed by id."""
    out: dict[str, EvidenceRecord] = {}
    for p in sorted(Path(directory).glob("*.record.*")):
        rec = EvidenceRecord.load(p)
        if rec.record_id in out:
            raise RecordError(f"duplicate record_id '{rec.record_id}' ({p})")
        out[rec.record_id] = rec
    return out
