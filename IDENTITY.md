# IDENTITY — what this project is

**sheaf** is a research lab embedding **formal verification** into **agentic development** of Solidity contracts. Narrow domain: DeFi primitives (vaults, lending, swaps, bridges).

## Thesis
Agentic development becomes trustworthy only if it is **neurosymbolic**: the LLM *generates*, a symbolic core *proves*. We reason about **specifications**, not language / EVM / business logic — and for a contract a spec *is* its economics: value-conservation laws.

**Epistemic spine (non-negotiable):** the **judge is the solver, never the LLM.** The agent over-generates candidate specs; SMTChecker / Lean returns proven / refuted / unknown. A model never grades its own proof.

## What we build toward
Standardized, reusable **spec libraries** per domain, and a loop where agentic output ships with a machine-checked proof **plus an honest, reproducible ledger of assumptions**. Current frontier: **cross-contract** verification — compose `A ⊨ spec_A` and `B ⊨ spec_B` into a guarantee on `A∘B`. "The most valuable and the hardest coincide."

## State (2026-06)
A **validated research prototype on curated slices**, not a product. The e2e loop runs; six numbered Findings (0001–0006) record what proved and what hit a wall:
- 0004 — cross-contract assume-guarantee (caller proven under a mined guarantee; callee discharged).
- 0005 — an automatic, human-free **vacuity gate** (catches empty proofs; auto-rediscovered the conservation≠delta gap).
- 0006 — a naive vibe-loop baseline self-reports **100% proved** yet is **0/4** on the real Vat — exactly why the solver judges.

`docs/mvp_roadmap.md` lists the **T1–T7 gates** that must clear before product engineering.

## What is NOT the core
- `evm-smith/` — scouting an external project (EVM-bytecode + Lean, Leonardo Alt). Observe; don't contribute-for-impact. Production energy stays in SMTChecker.
- `landing/`, `site/` — product surface, separate concern.
