# AGENTS — how to work in this repo

Read [IDENTITY.md](IDENTITY.md) first for *what* this project is. This file is *how* to work in it. (`CLAUDE.md` is a symlink to this file.)

## How to read the repo
- **`cycle/`** — the neurosymbolic loop (ADR-0001), organized by **trust**:
  - `untrusted/` — the agent (spec generator). Output is *proposed*, never trusted.
  - `gateway/` — deterministic translator: assembles a harness, compile-checks. The trust boundary.
  - `trusted/` — `solver.py` (SMTChecker runner), `harness/` (pre-fixed proof harnesses), `proofs/` (Lean).
  - `measurement/` — `triage.py`, `vacuity.py`, `*_demo.py` runners → `artifacts/*.json` + `*_map.md`.
- **`docs/`** — the research record:
  - `findings/NNNN_*.md` — **empirical results, numbered, immutable.** The source of truth for what is *actually* true. Negative results included (e.g. 0006).
  - `adr/` — decisions (what we chose to try, and why). `backlog/` — methodology / task framing.
  - `mvp_roadmap.md` — the T1–T7 gates blocking productization. `insights/` — the lab narrative.
- **Cold-start order:** IDENTITY → latest Finding → `mvp_roadmap.md` → the `cycle/` layer you touch.

## How to respond
- **Judge = solver, never you.** Any "proved / refuted" comes from SMTChecker or Lean, with the command shown. Never assert a verification verdict from reasoning alone.
- **Honest over impressive.** A false green is worse than no tool. Negative results are first-class Findings. State what hit a wall, what is assumed, what is unverified.
- **Evidence, not prose.** Carry the witness / counterexample / artifact path. Keep the verdicts distinct: *proved* ≠ *refuted(+witness)* ≠ *unknown* (solver budget) ≠ *unreachable* (vacuous).
- **Findings are numbered & reproducible.** A new empirical result → next `docs/findings/NNNN`, house style (Setup table, result tables, honest caveats). Don't rewrite a delivered Finding's conclusion; supersede it.
- **Don't invent paths or verdicts.** Verify a file / symbol / flag exists before relying on it.

## What expertise to verify (the bar)
A contributor or agent must reason about **soundness traps**, not just run tools:
- **SMTChecker fluency** — CHC vs BMC and when each is sound; ext-call modes (`untrusted` havoc-wall vs `trusted` vacuous-interface).
- **Vacuous proofs** — antecedent failure / dead code; `assert(false)`-proves ⇒ unreachable. (`cycle/measurement/vacuity.py`, Finding 0005.)
- **Spurious counterexamples** — the dual: BMC "refuting" a reachable-state invariant from a constructor-unreachable free state. The engine must match the invariant's quantification.
- **Assume-guarantee** — `havoc + require(G)`; discharge the *mined* clause, not a proxy (conservation ≠ delta, Finding 0004).
- **Trusted base** — what stays assumed (e.g. the no-reentrancy frame), what is discharged in Lean, named in the ledger. The trust ladder (ADR-0002).
- **Gate integrity** — three-status PASS / FLAG / BLOCKED ("couldn't verify" ≠ green); acceptance checks with non-zero exit; retain witnesses.

A genuine answer reasons about **where the proof could be empty**. A shallow one runs the tool and reports the green.

## Toolchain (pinned, for reproducible measurement)
solc 0.8.35+commit.47b9dedd · z3 4.16.0 · Lean 4.31.0 + Mathlib · python 3.12 · foundry. Canonical core: `/opt/homebrew/bin/solc`.
