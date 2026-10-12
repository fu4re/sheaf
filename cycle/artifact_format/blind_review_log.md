# Blind reverse-check log — pilot-vaultasset-2026-06-26 (Task 0003, acceptance #7)

- **Date:** 2026-06-26
- **Reviewer:** independent agent, NO access to the verification session, the assembly
  inputs (`*.src/`), `docs/findings`, or this repo's intent. Given ONLY the package
  directory + the linter that ships with the format.
- **Question:** can a third party reach every leaf and render a defensible verdict,
  from the package alone, in ≤30 min?
- **Outcome:** **YES** — all leaves reached in ~9 steps, < 30 min, with a per-leaf
  verdict. The review also surfaced **two real catches** (below), which is the point
  of a blind check.

## Acceptance result

| Acceptance #7 criterion | Met? |
|---|---|
| Reviewer reaches the leaves from the package alone | ✅ |
| Renders a verdict on each leaf without asking the author | ✅ |
| ≤ 30 min for a competent auditor with the toolchain | ✅ (reviewer estimate) |
| Log attached | ✅ (this file) |

## Two real catches (honest — these become caveats / next-task items)

1. **The Lean leaf is NOT kernel-checkable from the package alone.**
   `evidence/lean/L_cons__Basic.lean` does `import Mathlib` and will not elaborate
   standalone; `lean_project.json` redirects the actual build to
   `trusted/proofs/aave_arith`, a directory *outside* the package. So the linter's
   `replay:lean` PASS certifies an artifact the blind reviewer cannot inspect. The
   reviewer accepted the theorem *statement* by eye but downgraded the leaf to
   **CANT-TELL** for the "kernel-checked" claim. → The package is self-contained for
   SMT (harnesses re-run) but **not** for Lean (Mathlib/project not vendored).

2. **`H_model` (harness ↔ bytecode) is empty, yet C1 renders as "✅ proven".**
   Honestly labelled `unverified` / `evidence: n/a` ("the moat"), but a casual reader
   sees a green check. The reviewer's blunt summary: *as a logic exercise, accepted
   under the stated leaves; as a safety guarantee about a real deployed vault,
   REJECTED — the faithfulness leaf is exactly the one that would matter and it is
   empty.* This is the known moat (roadmap T3/faithfulness), not a defect of the format.

## What reproduced (reviewer re-ran the tools)

- Linter `--replay`: WELL-FORMED, 19 pass / 0 flag / 0 blocked, exit 0.
- C1 harness: `CHC: 2 verification condition(s) proved safe` — reproduced.
- C2 harness: `CHC: 1 verification condition(s) proved safe` — reproduced.
- C3 harness: `deposit(0)` counterexample at line 31 — exact witness reproduced.
- Provenance: all 8 subject digests match (tamper-consistent); **unsigned** (`signatures: []`).

## Reviewer's bounded assumption set (verbatim intent)

C1 is only as true as ALL of these simultaneously:
1. **A_solver** — z3 + SMTChecker sound, no kernel re-check of C1/C2.
2. **A_ag_rule** — A/G composition valid (single external call, non-reentrant frame only).
3. **L_cons builds in the external `aave_arith` project** — trusted by eye + linter's word.
4. **H_model** — *unverified*; the dealbreaker for any real-world reading of C1.

---

## Full reviewer report

> TOP CLAIM. Two roots: **C1** (load-bearing) — "the vault stays solvent,
> `vaultBal >= totalAssets`, when composed with an ERC20 that honours the callee
> guarantee" — claimed **proven**; **C3** — naive over-claim on the BUGGY vault,
> `totalShares == totalAssets`, claimed **refuted (witness)**. C1 is *conditional*
> on the callee guarantee G_B, discharged via C2.
>
> LEAF VERDICTS. C2: **ACCEPT** (re-ran, 1 VC safe, non-vacuous). C3: **ACCEPT**
> (counterexample reproduced exactly, bug visible in inlined SUT). L_cons:
> **CANT-TELL** (statement readable & believable, but cannot build the embedded copy
> — `import Mathlib`, project redirected outside package). A_ag_rule: **ACCEPT as a
> stated assumption** (disclosed, scoped, but an unproven meta-rule the whole A∘B
> rests on). A_solver: **ACCEPT as a stated assumption** (honest, standard). H_model:
> **REJECT as evidence / accept only as a flagged hole** (`unverified`, `n/a`; the
> leaf that breaks any real-world reading of C1).
>
> RE-CHECK. Linter WELL-FORMED exit 0. SMT C1/C2 safe, C3 witnessed — all reproduced
> by the reviewer directly. Lean: embedded file fails standalone (`unknown module
> prefix 'Mathlib'`); green build comes from an out-of-package project. Provenance: 8
> digests match, unsigned.
>
> STUMBLES. (1) `lean_project.json` points outside the package — the proof isn't
> shipped, only the source text. (2) embedded `.lean` won't elaborate standalone.
> (3) ~60% of the Lean file is unrelated Aave `mulDiv` axiom-discharge; the cited
> `transfer_pair_sum_preserved` is a thin 2-account ℕ identity, connected to
> "ghostSum faithful" by comment + a self-declared *level-1 text-match bridge*, not
> end-to-end proof. (4) `H_model` empty yet C1 shows "✅ proven" — a casual reader is
> misled. (5) C1's harness is a havoc-summary (`vaultBal_post` is a free parameter
> pinned by `require`), so C1's strength is in the leaves (A_ag_rule + C2 + H_model),
> not the SMT result itself. (6) provenance unsigned.
>
> OVERALL. **Conditionally ACCEPT as a well-formed, honest assurance artifact — but
> REJECT any reading of C1 as "this deployed vault is solvent."** Relative to the
> trusted base the formal claims reproduce; the artifact is unusually honest in
> foregrounding its own holes. Trusting C1 means trusting A_solver ∧ A_ag_rule ∧
> (L_cons external build) ∧ H_model — and H_model is empty. "As a logic exercise,
> accepted under leaves 1–4; as a safety guarantee about a real vault, rejected —
> the harness-faithfulness leaf is exactly the leaf that would matter." Honest pilot,
> not a deceptive one.
>
> TIME/EFFORT. ~9 distinct steps; every leaf reached and a defensible verdict formed
> well under 30 minutes. The only budget-blower would be actually kernel-checking
> L_cons, which the package does not permit.
