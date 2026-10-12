# C9 Experimental Tracker

Source: [task.md](task.md) · Report: [report.md](report.md) · Env:
`source scripts/env.sh` (native K/Kontrol on PATH).

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked/stop-rule.

## Stop rules
- `[x]` **Q1 = circularity-guarded → HIT.** Reported immediately. A3a induction
  step needs a step-guard-compatible lemma.
- `[x]` Q3 = (iii) silent summary application → **NOT hit** (precondition kept as
  a `requires` guard on the summary; outcome is (ii) sound).

## Milestone 0 — environment `[x]`
Native arm64 toolchain via kup/Nix. kontrol 1.0.255 / K v7.1.337 / kore-exec
0.1.155 / kevm 1.0.678. Pinned in report.md + `logs/versions.log`.

## Q1 — trusted mechanics `[x]` → `circularity-guarded`
Clean D1 (no step before lemma) FAILS; discriminator D2 (one real step then
lemma) PROVES; false trusted lemma accepted (not re-proved); negative + untrusted
controls FAIL. Backend = kore-exec (haskell). `repro/q1`, `repro/q1d`,
`scripts/run-q1.sh`.

## Q2 — claim quantifier `[x]` → `all-path по умолчанию`
`--default-claim-type` default = `SentenceType.ALL_PATH`
(HaskellKRunOptions.java:34). 0/189 KEVM/Kontrol specs carry a quantifier attr.
Kontrol = pyk APRProof (all-path only; no one-path proof type). one-path not
provable by standalone kore-exec. `repro/q2-claimtype`.

## Q3 — CSE coverage miss `[x]` → (ii) sound
Baseline (no cse) FAILS with counterexample x≤10. CSE summary of B.f carries
`requires 10 <Int KV0_x` (the precondition) → guarded rewrite → uncovered case
falls back → sound; (iii) ruled out by construction. Mapping-access precondition
→ explicit `WARNING Array/mapping access not supported yet`, dropped. Caveat:
end-to-end --cse setUp crashed on an SMT sort error (KEVM/booster fragility),
so fallback not observed executing. `repro/q3-cse`, `repro/q3-mapping`.

## Q4 — ghost cell `[x]` → только-форк-семантики (≈1 line)
K extends a config from an external module only when the base has an
auto-`<generatedTop>` (≥2 top cells). KEVM has a single `<kevm>` top cell →
external add fails (`Too many top cells`), sibling and nested alike. 1-line fork
of evm.md (`<callCounter>` inside `<kevm>`) builds. Ghost cell constrainable in
claims (proved on toy). `repro/q4-ghost`.

## Report checklist
- `[x]` Environment pinned.
- `[x]` Q1/Q2/Q3/Q4 verdicts in required format.
- `[x]` Stop-rules honored (Q1 reported immediately; Q3 not triggered).
- `[x]` Commands copy-paste runnable; logs under `logs/`; reproducers under `repro/`.
