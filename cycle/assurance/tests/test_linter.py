"""Phase 1 witness — cross-file invariants of the linter.

Starts from fixtures/good (a WELL-FORMED package), mutates a copy to violate each
package invariant, and asserts the linter catches it. The hidden-assumption case is
acceptance #4 of Task 0003.

Run: `python -m assurance.tests.test_linter` from `cycle/` (exit 0 = all pass).
"""
from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # cycle/ on path

from assurance.verify_package import lint  # noqa: E402

GOOD = Path(__file__).resolve().parent / "fixtures" / "good"


def _copy() -> Path:
    d = Path(tempfile.mkdtemp(prefix="assur_"))
    shutil.copytree(GOOD, d / "pkg")
    return d / "pkg"


def _graph(pkg: Path) -> dict:
    return yaml.safe_load((pkg / "assurance_graph.yaml").read_text())


def _write_graph(pkg: Path, doc: dict) -> None:
    (pkg / "assurance_graph.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


def _ledger(pkg: Path) -> dict:
    return yaml.safe_load((pkg / "trusted" / "ledger.yaml").read_text())


def _write_ledger(pkg: Path, doc: dict) -> None:
    (pkg / "trusted" / "ledger.yaml").write_text(yaml.safe_dump(doc, sort_keys=False))


CASES: list[tuple[str, str, str]] = []  # (name, expected_verdict, expected_check)


def case(name: str, expected: str, check: str):
    def deco(fn):
        CASES.append((name, expected, check, fn))
        return fn
    return deco


@case("good", "WELL-FORMED", "")
def _good(pkg: Path) -> None:
    pass


@case("hidden-assumption (acceptance #4)", "INVALID", "closure")
def _hidden_assumption(pkg: Path) -> None:
    # delete the leaf an edge depends on -> the assumption is now hidden.
    led = _ledger(pkg)
    led["assumptions"] = [a for a in led["assumptions"] if a["id"] != "A_noreentry"]
    _write_ledger(pkg, led)


@case("assumption-dressed-as-proof", "INVALID", "edge-honesty")
def _dishonest_edge(pkg: Path) -> None:
    g = _graph(pkg)
    for e in g["claims"][0]["depends_on"]:
        if e["ref"] == "A_noreentry":
            e["status"] = "proven"  # relabel an assumed leaf as proven
    _write_graph(pkg, g)


@case("cycle", "INVALID", "acyclicity")
def _cycle(pkg: Path) -> None:
    g = _graph(pkg)
    # make C1 -> C2 and C2 -> C1 (both kind=claim)
    g["claims"][0]["depends_on"].append(
        {"kind": "claim", "ref": "C2", "status": "proven", "human": "depends on C2"})
    g["claims"][1]["verdict"] = "proven"
    g["claims"][1]["evidence"] = {"smt_query": "evidence/smt/C1__harness.sol"}
    g["claims"][1]["depends_on"] = [
        {"kind": "claim", "ref": "C1", "status": "proven", "human": "depends on C1"}]
    _write_graph(pkg, g)


@case("missing-evidence-file", "INVALID", "evidence")
def _missing_evidence(pkg: Path) -> None:
    (pkg / "evidence" / "smt" / "C1__harness.sol").unlink()


@case("lean-build-lies", "INVALID", "ledger")
def _lean_lies(pkg: Path) -> None:
    led = _ledger(pkg)
    led["lean_theorems"][0]["build_status"] = "failed"  # but status still 'proven'
    _write_ledger(pkg, led)


@case("dangling-claim-ref", "INVALID", "closure")
def _dangling_claim(pkg: Path) -> None:
    g = _graph(pkg)
    g["claims"][0]["depends_on"].append(
        {"kind": "claim", "ref": "C_ghost", "status": "proven", "human": "nonexistent"})
    _write_graph(pkg, g)


@case("missing-package", "BLOCKED", "load")
def _missing_pkg(pkg: Path) -> None:
    (pkg / "assurance_graph.yaml").unlink()


def main() -> int:
    fails: list[str] = []
    for name, expected, check, mutate in CASES:
        pkg = _copy()
        mutate(pkg)
        rep = lint(pkg)
        got = rep.verdict
        flagged_checks = {f.check for f in rep.findings if f.status in ("FLAG", "BLOCKED")}
        ok_verdict = got == expected
        ok_check = (check == "") or (check in flagged_checks)
        mark = "OK " if (ok_verdict and ok_check) else "XX "
        detail = f"{got}"
        if check:
            detail += f" via {sorted(flagged_checks)}"
        print(f"{mark} {name:38s} -> {detail} (exit {rep.exit_code})")
        if not ok_verdict:
            fails.append(f"{name}: expected {expected}, got {got}")
        if not ok_check:
            fails.append(f"{name}: expected check '{check}' to flag, flagged {sorted(flagged_checks)}")
        shutil.rmtree(pkg.parent, ignore_errors=True)

    if fails:
        print(f"\nFAILED ({len(fails)}):")
        for f in fails:
            print("  -", f)
        return 1
    print(f"\nALL PASS ({len(CASES)} cases)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
