"""Paths & run-directory workspace.

Two path roots, kept distinct so `tcg` works from ANY project:

  REPO        the tool's home (this checkout) — where the cycle/ substrate, the
              Lean project and axiom_registry live. Computed from this file's
              location; never depends on where the user invoked `tcg`.
  work_base() the DEVELOPER's workspace for run artifacts — `$TCG_HOME/runs` or
              `./.tcg/runs` in the current project. This is where phi/check/
              package land, so a developer verifying their own contract gets the
              artifacts in their own tree (gitignorable), not buried in REPO.

User-supplied paths (--contract, --run-dir, --spec-file, --family, --out) resolve
against the current working directory, like any normal CLI.
"""
from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]  # the tool's home (sheaf checkout)


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def resolve(p: str | Path) -> Path:
    """A user-supplied input path → absolute, relative to CWD (not REPO)."""
    p = Path(p)
    return p if p.is_absolute() else (Path.cwd() / p)


def work_base() -> Path:
    """Base dir for run artifacts in the developer's project: $TCG_HOME/runs or
    ./.tcg/runs. Created lazily by callers."""
    home = os.environ.get("TCG_HOME")
    base = Path(home) if home else (Path.cwd() / ".tcg")
    return base / "runs"


def disp(p: str | Path) -> str:
    """Display a path relative to CWD when it is under CWD, else absolute."""
    p = Path(p).resolve()
    try:
        return str(p.relative_to(Path.cwd().resolve()))
    except ValueError:
        return str(p)


def new_run_dir(contract: str, *, stamp: str | None = None) -> Path:
    d = work_base() / f"{contract}-{stamp or utc_stamp()}"
    d.mkdir(parents=True, exist_ok=True)
    return d


def latest_run_dir(contract: str | None = None) -> Path | None:
    base = work_base()
    if not base.exists():
        return None
    prefix = f"{contract}-" if contract else ""
    runs = sorted(p for p in base.iterdir()
                  if p.is_dir() and p.name.startswith(prefix) and "-" in p.name)
    return runs[-1] if runs else None


# Tool-internal artifact location (setup-check report, vacuity build scratch) — stays
# under REPO; these are diagnostics about the tool's own toolchain, not per-contract.
TCG_RUNS = REPO / "cycle" / "measurement" / "artifacts" / "tcg_runs"
