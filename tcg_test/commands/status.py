"""tcg status — read-only view of a run's gate states and terminal.

Reads the artifacts each stage left (phi.frozen.yaml, check.json, vacuity.json,
outcome.json, package/) and renders gate-by-gate progress plus the terminal. It
DECIDES nothing — it reflects what the gates wrote. The top line is rendered by the
render-rule (the weakest leaf): never green over an open dischargeable leaf.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from tcg import runs

CYCLE = runs.REPO / "cycle"
if str(CYCLE) not in sys.path:
    sys.path.insert(0, str(CYCLE))


def _load(p: Path) -> dict | None:
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError:
        import yaml
        return yaml.safe_load(p.read_text())


def run(args) -> int:
    run_dir = runs.resolve(args.run_dir)
    if not run_dir.exists():
        print(f"error: run dir not found: {run_dir}", file=sys.stderr)
        return 1

    frozen = _load(run_dir / "phi.frozen.yaml")
    draft = _load(run_dir / "phi.draft.yaml")
    check = _load(run_dir / "check.json")
    vac = _load(run_dir / "vacuity.json")
    outcome = _load(run_dir / "outcome.json")
    pkg = run_dir / "package"

    def line(gate: str, state: str, detail: str = "") -> None:
        icons = {"green": "✅", "blocked": "🚫", "flag": "❌", "pending": "·", "done": "✓"}
        print(f"   {icons.get(state, '·')} {gate:<10} {detail}")

    print(f"\n  tcg status — {runs.disp(run_dir)}\n")
    # F
    line("formalize", "done" if draft else "pending",
         "φ drafted (all four dimensions)" if draft else "no φ draft")
    # H
    if frozen and frozen.get("freeze"):
        line("validate", "green", f"φ FROZEN ({frozen['freeze']['content_hash'][:12]}…) by "
             f"{frozen['freeze'].get('approved_by')}")
    else:
        line("validate", "pending", "φ not frozen")
    # K
    if check:
        kr = check.get("k_result")
        st = {"accept": "green", "refute": "flag", "unknown": "blocked"}.get(kr, "pending")
        wit = check.get("witness")
        line("check", st, f"K={kr}" + (f"  witness={wit.get('assignments')}" if wit else ""))
    else:
        line("check", "pending", "not run")
    # vacuity
    if vac:
        v = vac.get("verdict")
        st = {"PASS": "green", "FLAG": "flag", "BLOCKED": "blocked", "M_UNASSESSED": "blocked"}.get(v, "pending")
        line("vacuity", st, f"{v}"
             + (f"  (Probe R={vac['probe_R']['result']})" if vac.get("probe_R") else ""))
    else:
        line("vacuity", "pending", "not run")
    # package
    if pkg.exists():
        from assurance.verify_package import lint
        rep = lint(pkg, replay=False)
        st = {"WELL-FORMED": "done", "INVALID": "flag", "BLOCKED": "blocked"}.get(rep.verdict, "pending")
        line("package", st, f"lint {rep.verdict}")
    else:
        line("package", "pending", "not built")

    # terminal (render-rule: top is never green over an open dischargeable leaf)
    print()
    if outcome:
        term = outcome.get("terminal", "?")
        green = outcome.get("verified") is True
        print(f"  terminal : {term}  {'(GREEN)' if green else '(NOT green)'}")
        if outcome.get("open_dischargeable"):
            print(f"  capped by open DISCHARGEABLE leaves: {outcome['open_dischargeable']}")
        print(f"  claim    : {outcome.get('claim_scope')}")
        print(f"  exit     : {outcome.get('terminal_exit')}")
    else:
        print("  terminal : (no outcome.json yet)")
    print()
    return 0
