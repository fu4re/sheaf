"""Module [5] — Solver Core (SMTChecker). TRUSTED side ("solver verifies").

Runs solc's SMTChecker on a harness .sol and parses the result into a structured
verdict: proved | counterexample(+witness) | inconclusive | compile_error.
This is the deterministic runner+parser (T-06) — the foundation of every
research measurement. It is the source of truth; not part of the "intelligence".
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

SOLC = shutil.which("solc") or "/opt/homebrew/bin/solc"


def solc_version() -> str:
    out = subprocess.run([SOLC, "--version"], capture_output=True, text=True).stdout
    m = re.search(r"Version:\s*(\S+)", out)
    return m.group(1) if m else "unknown"


@dataclass
class Verdict:
    verdict: str  # proved | counterexample | inconclusive | compile_error
    witness: dict | None = None
    reason: str | None = None
    engine: str = "chc"
    solvers: list = field(default_factory=lambda: ["z3"])
    targets: list = field(default_factory=lambda: ["assert"])
    solc_version: str = ""
    command: list = field(default_factory=list)
    duration_s: float = 0.0
    raw: str = ""


def _parse_witness(text: str) -> dict | None:
    assignments: dict[str, str] = {}
    m = re.search(r"Counterexample:\s*\n(.*?)(?:\nTransaction trace:|\Z)", text, re.S)
    if m:
        for pair in re.split(r"[\n,]", m.group(1).strip()):
            mm = re.match(r"\s*([\w.\[\]]+)\s*=\s*(.+?)\s*$", pair)
            if mm:
                assignments[mm.group(1)] = mm.group(2)
    trace: list[str] = []
    tm = re.search(r"Transaction trace:\s*\n(.*)", text, re.S)
    if tm:
        for line in tm.group(1).splitlines():
            s = line.strip()
            if not s or s.startswith("-->") or s.startswith("|") or s.startswith("^"):
                continue
            trace.append(s)
    if not assignments and not trace:
        return None
    return {"assignments": assignments, "transaction_trace": trace[:12]}


def run_solver(
    harness: str | Path,
    engine: str = "chc",
    solvers: tuple[str, ...] = ("z3",),
    targets: tuple[str, ...] = ("assert",),
    model_checker_timeout_ms: int = 20000,
    proc_timeout_s: int = 180,
    ext_calls: str | None = None,
) -> Verdict:
    # `ext_calls` pins SMTChecker's external-call model (untrusted havoc-wall vs
    # trusted vacuous-interface). It maps the φ.trace dimension to a solver flag
    # (tcg check, Task 0008). Default None keeps the historical behavior; when set,
    # the flag is recorded in `command` for the run record (Inv.9).
    cmd = [
        SOLC,
        "--model-checker-engine", engine,
        "--model-checker-targets", ",".join(targets),
        "--model-checker-solvers", ",".join(solvers),
        "--model-checker-timeout", str(model_checker_timeout_ms),
    ]
    if ext_calls:
        cmd += ["--model-checker-ext-calls", ext_calls]
    cmd.append(str(harness))
    t0 = time.time()
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=proc_timeout_s)
    except subprocess.TimeoutExpired:
        return Verdict(
            verdict="inconclusive",
            reason=f"solver wall-timeout ({proc_timeout_s}s) — contract too complex in budget",
            engine=engine, solvers=list(solvers), targets=list(targets),
            solc_version=solc_version(), command=cmd,
            duration_s=round(time.time() - t0, 3), raw="",
        )
    dur = round(time.time() - t0, 3)
    text = ((proc.stderr or "") + "\n" + (proc.stdout or "")).strip()

    v = Verdict(
        verdict="inconclusive",
        engine=engine,
        solvers=list(solvers),
        targets=list(targets),
        solc_version=solc_version(),
        command=cmd,
        duration_s=dur,
        raw=text,
    )

    errors = [l for l in text.splitlines() if l.strip().startswith("Error:")]
    if errors:
        v.verdict = "compile_error"
        v.reason = "; ".join(errors)[:500]
        return v

    if re.search(r"Assertion violation happens here", text):
        v.verdict = "counterexample"
        v.witness = _parse_witness(text)
    elif re.search(r"Assertion violation might happen here", text):
        v.verdict = "inconclusive"
        v.reason = "could not prove safe and found no concrete counterexample (over-approximation / k-bound)"
    elif re.search(r"could not be proved", text):
        v.verdict = "inconclusive"
        v.reason = "verification condition could not be proved (nonlinear arithmetic / over-approximation / timeout — the SMTChecker wall)"
    elif re.search(r"proved safe", text):
        v.verdict = "proved"
    else:
        v.reason = "no SMTChecker assertion result in output (check engine/targets/solver)"
    return v


if __name__ == "__main__":
    import sys

    print(json.dumps(asdict(run_solver(sys.argv[1])), indent=2, ensure_ascii=False))
