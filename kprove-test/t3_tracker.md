# SPIKE-T3 Tracker

Source: [t3_task.md](t3_task.md) · Report: [t3_report.md](t3_report.md) · Inputs:
[t1_report.md](t1_report.md), [spike_t2_report.md](spike_t2_report.md), [TCG-006.md](TCG-006.md).
Env: `source scripts/env.sh`. Fork = T1 fork + `<inFunc>` (repro/t3-q0).

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked/stop-rule.

## Stop rules (both = immediate return, don't wait for full report)
- `[x]` **1. Q2 = «V and F match on #6/#8»** → **NOT triggered** (V FAIL / F PASS on both #6 and #8).
- `[x]` **2. Q3 = «an attack step is inadmissible by Guar_env»** → **NOT triggered** (all trace steps admissible; checker discriminates).
- `[x]` Non-stop (journal): monolithic provenance clause not expressible → expected (K3), decomposed form covered the trace.

## Q0 — `<inFunc>` implementation [precondition] `[x]` → path = #mkCall, JUMPDEST not needed
- `[x]` Recon: `#return.*` (evm.md:1826/1834/1844) fire BEFORE `#popCallStack`; `<callData>`∈`<callState>`
  (pop restores the whole callState) ⇒ finishing frame's selector readable pre-pop. **JUMPDEST fallback not needed.**
- `[x]` Fork extended: `<inFunc> Map` + `<monitoredAddr>` (next to `<callCounter>`); +1 @`#mkCall` (guard
  `callee==C` via total `#bump`, key `#selKey(ARGS)`); −1 @3 exit junctions (key `#selKey(<callData>)`).
  Diff = 44 additive lines (~22 semantic K), no stock LHS touched (A5 argument carries from T1).
- `[x]` Kompile exit=0 (`logs/t3-q0-kompile.log`).
- `[x]` PROVED (`logs/t3-q0-infunc.log`, `#Top`): entry-base (.Map→SEL↦1), entry-reenter (SEL↦1→SEL↦2,
  reentered@2), exit-before-pop (SEL↦2→SEL↦1, decrement reads selector pre-pop).
- `[x]` Non-vacuity (`logs/t3-q0-negctl.log`, FAILED as designed): neg-no-decrement (real post SEL↦1),
  neg-foreign-guard (real post .Map ⇒ callee==C guard gates).
- `[x]` Caveat (→ Q4 journal): phantom-return over-count on pre-frame-check failures; excluded by mini-instance Pre.

## Q1 — Encode & run the 11-obligation matrix [core] `[x]` → 17/17 = T2 expectation
- `[x]` Encoding: R/G-implication (compat #3–#8, subsumption à la T1-Q4) + execution (frame #1/#2, junction #9/#10),
  over abstract model `repro/t3-q1/withdraw.k` (operation-order faithful). Full-bytecode closure = T1-Q2a boundary.
- `[x]` Grounding: V leaves pending debit at suspension (bal[U]=B₀ ⟹ Rely_w^V pins it); F none (Rely_w^F over bal[U]=⊤).
  Both `#Top` — the V/F split is EARNED by operation order, not baked.
- `[x]` 11 obligations edge-typed (TCG-005) + #3 BOTH Rely editions (K1): V-strict FAILED / V-weak #Top / F #Top.
- `[x]` Matrix 17/17 per-claim (`scripts/t3-q1-matrix.sh`, all OK). FAILED rows: #6-V, #8-V, #3-V-strict — genuine
  counterexamples (`#Not(B_PRE = B_PRE −APRIME)`, `#Not(B_PRE = B_PRE +V)`).
- `[x]` Vacuity/spurious gate: V-FAIL non-spurious (concrete reentrant transition ∈Guar ∉Rely); F-PASS non-vacuous —
  counterfactual `q1-vacuity-spec.k` (F transition under V's strict Rely → FAILED) proves the pass is Rely-driven.
- `[x]` #11 root = meta (PAR-induction, not a single claim); V-FAIL derived from #6/#8, F-PASS from all-green.

## Q2 — V/F discrimination [exit criterion] `[x]` → outcome (a), stop-rule 1 NOT triggered
- `[x]` Robust #6/#8: V FAIL, F PASS independent of Rely edition ⟹ discipline discriminates. #3 secondary (edition-dep).
  5 divergence points on 11 rows (#3-strict, #6, #8 primary + #10-global, #11-root derived) — as T2 predicted.

## Q3 — Negative corpus: Guar_env vs real DAO attack [risk №2 by execution] `[x]` → all steps admissible
- `[x]` DAO attacker (receive re-calls target) vs V: forge PoC (`repro/t3-q3/`, solc 0.8.35) — `test_V_drains` PASS
  (bank→0, attacker profits victim's ether), `test_F_safe` PASS (reentry reverts, victim safe). Trace: depth 1, 2×1e18.
- `[x]` Ghosts: `<inFunc>[wV]` 0→1→2 (reentered fires @E4), `<callCounter>` cumulative; on-fork carrier = Q0 entry-reenter.
- `[x]` Mechanical checker `guarenv.k` (decomposed K3: `callIntoC` = C-claim rows 1,3 / `envCode` admissible iff none of
  rows A,B,C,E,F). `dao-trace-all-admissible` → #Top (all admissible); `fabricated-inadmissible-caught` → #Top
  (checker returns false on a direct-S[C]-write step ⇒ discriminates, not vacuous).
- `[x]` Verdict: **all admissible** → Guar_env not narrower than reality on this corpus. Provenance clause NOT needed.

## Q4 — Expressibility-gap journal [mandatory side] `[x]` → non-empty (4 gaps)
- `[x]` 1. provenance clause (K3) — monolithic temporal form inexpressible in K-requires; decomposition covered trace (result, non-stop).
- `[x]` 2. `Σ_{u∈Users}` / ∀ over Users — modeled as 2-element {U, other}; explicit universal quantifier lost.
- `[x]` 3. Rely-only-at-suspension (H8) — baked into encoding by construction, not a checkable K temporal predicate.
- `[x]` 4. withdraw_V `-=` (0.8-checked) underflow-reverts / self-defeats ⇒ R/G flag is conservative there; concrete
  drain uses canonical `bal=0` form (same operation-order defect). Honest instance caveat.
