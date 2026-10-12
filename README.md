# sheaf — research record: formal verification of agent-written smart contracts

This repository is the **research record** behind the proposal *Checkable Agreements*:
the June 2026 source-level pilots (Solidity harnesses, solc 0.8.35 SMTChecker, Lean 4),
the July 2026 theory drafts, and the task/decision history. The August 2026
bytecode-level line (KEVM, proof-carrying bundles) is a separate repository,
[`tcg`](https://github.com/fu4re/tcg), with its own Findings.

The record is written to be checked, not believed. Every "proved" or "refuted" in
`docs/findings/` is a solver or kernel verdict with the command that produced it,
every Finding has an "honest caveats" section, and negative results are numbered
like positive ones. Most documents are in Russian; this README, the code comments
and the Lean sources are in English.

## Findings (June 2026, each a single run)

| # | Finding | Result | Judge |
|---|---|---|---|
| 0001 | [Agentic spec generation vs Certora](docs/findings/0001_agentic_spec_gen_realism.md) | On Aave's `ATokenVault.deposit`, a one-shot agent recovers 4 of 7 expert-proven invariants and half of a 5th (≈64%) for $0.16; misses are structural (quantified, two-state) | **LLM coverage judge** (the only pilot not judged by a solver) |
| 0002 | [Solver as judge on MakerDAO Vat](docs/findings/0002_solver_as_judge_makerdao_vat.md) | Two Maker conservation laws proved on focused harnesses (raw Vat inconclusive); an agent over-claim refuted with witness `Line=0, debt=1`; port equivalence-audited by diff + 4,800 differential fuzz ops | SMTChecker CHC/BMC, Lean (`ar_delta`) |
| 0003 | [Modular stack vs monolithic formal](docs/findings/0003_modular_stack_vs_monolithic_formal.md) | Architectural comparison with evm-smith, not an experiment; one evm-smith axiom shown false by a machine-checked `example : False` | Lean |
| 0004 | [Assume-guarantee across contracts](docs/findings/0004_assume_guarantee_cross_contract.md) | Both SMTChecker ext-call modes fail (default refutes a true invariant; `trusted` + interface proves `assert(false)`); the weakest sufficient callee guarantee is mined by ablation; three adversarial tokens refuted; no-reentrancy stays a named assumption | SMTChecker, Lean |
| 0005 | [Vacuity gate by mutation](docs/findings/0005_vacuity_gate_mutation.md) | Two solver-judged probes (reachability, load-bearing) flag both deliberately vacuous fixtures and rediscover the conservation≠delta gap automatically; BMC spurious counterexample documented | SMTChecker |
| 0006 | [Naive agent loop ceiling](docs/findings/0006_naive_loop_ceiling.md) | An autonomous Opus loop reports `proved` on 100% of goals; honest scoring: L1 3/3, L2 3/3, L3 2/3, L4 0/4 (every L4 proof is about a reimplementation, not Vat) | SMTChecker + faithfulness gate (+ one manual catch at L3) |
| 0007 | [Assurance package format](docs/findings/0007_assurance_package_format.md) | A cross-contract solvency claim packaged for third-party replay: 19 pass / 0 flag / 0 blocked under live replay; a blind reviewer (an AI agent) surfaced two real gaps (Lean leaf not self-contained; faithfulness leaf `unverified`) | linter + SMTChecker + `lake build` |
| 0008 | [Neural Lean prover](docs/findings/0008_neural_lean_prover_ghost_axioms.md) | 8/8 theorems kernel-accepted, 5 new discharges from the open lemma registry; a wrong theorem rejected, a planted `sorry` caught by `#print axioms` | Lean 4 kernel |

Dates: 2026-06-22 … 2026-06-29. Everything is N=1. What each result does *not*
show is stated inside the Finding.

## Layout

```
IDENTITY.md, AGENTS.md      what the project is / how to work in it (AGENTS = CLAUDE.md)
docs/findings/              numbered, immutable empirical results (+ artifacts/)
docs/adr/                   decisions 0001–0003 (neurosymbolic loop, trust ladder, TCG)
docs/backlog/               task framing 0001–0015; docs/plans/ the tcg productisation plan
docs/mvp_roadmap.md         the T1–T7 gates; docs/insights/ the lab narrative
docs/whitepapers/           Trusted Code Generation framework paper (v2, 2026-06-27)
cycle/                      the pilots: untrusted/ (agent) → gateway/ → trusted/ (solver, harnesses, Lean) → measurement/
cycle/naive_loop/           Finding 0006 loop, judge, aggregator, runs/
cycle/assurance/            Finding 0007 package format, linter, emitters; cycle/artifact_format/ the pilot package
cycle/ground_truth/         vendored references with provenance (see THIRD_PARTY.md)
kprove-test/                July 2026: theory drafts TCG-003…007 (composition certificate, theorems A3a/A3b —
                            postulated, NOT proved), KEVM/Kontrol spikes T1–T3 with pinned reports and reproducers
tcg_test/                   the superseded June SMTChecker gate CLI (ADR-0003 MVP, backlog 0006–0011); kept for the record
task.md                     July spike brief (SPIKE-A, bytecode closure)
```

## Toolchain (pinned)

| Component | Version |
|---|---|
| solc | 0.8.35+commit.47b9dedd (native arm64, `brew install solidity`; SMTChecker built in) |
| z3 | 4.16.0 |
| Lean | 4.31.0 + Mathlib v4.31.0 (`cycle/trusted/proofs/aave_arith/lean-toolchain`) |
| foundry | 1.2.3 |
| python | 3.12 (`PyYAML==6.0.2` for the assurance linter; everything else is stdlib) |
| agent | `claude -p` headless (model pinned per run and recorded in each artifact) |
| K / KEVM (kprove-test only) | kontrol 1.0.255, K v7.1.337, kore-exec 0.1.155, KEVM 1.0.678 |

`cycle/foundry.toml` points at `/opt/homebrew/bin/solc`; on another machine set it
to `"0.8.35"` or your `which solc`.

## Reproduce

Run from the repository root unless stated. Live agent calls need the `claude`
CLI; every pilot also has a deterministic replay from the committed artifacts.

```bash
# toolchain smoke (Finding 0002's engine): proved + counterexample a=1
solc --model-checker-engine chc --model-checker-targets assert --model-checker-solvers z3 cycle/trusted/smt_smoke/ProvablePass.sol
solc --model-checker-engine chc --model-checker-targets assert --model-checker-solvers z3 cycle/trusted/smt_smoke/ProvableFail.sol

# 0001 — spec generation vs Certora (needs cycle/ground_truth/aave_vault/fetch.sh first)
cd cycle && python3 measurement/aave_spec_gen.py --replay        # from cache; drop --replay for a live run

# 0002 — Vat port equivalence (300 × 16 fuzzed ops) and the focused harnesses
cd cycle/ground_truth/dss_vat && forge install foundry-rs/forge-std@257559546b763ec5fa7371fb77fef9102db86446 && forge test
#   harnesses: cycle/trusted/harness/Vat{DaiConservation,Solvency}{,Buggy}.sol; verdict runner: cycle/measurement/triage.py

# 0004 — assume-guarantee: mined interface, callee discharge, adversarial tokens
python3 -m cycle.measurement.cross_triage_demo                     # → cycle/measurement/artifacts/cross_ag__triage.json

# 0005 — vacuity gate (Probe R + Probe M) on the honest and the vacuous fixtures
python3 -m cycle.measurement.vacuity_demo                          # → cycle/measurement/artifacts/vacuity_report.json

# 0006 — naive loop (live Opus run per level) and the solver-judged aggregate
cd cycle/naive_loop && python3 loop.py --level L1 --model opus && python3 aggregate.py
#   re-judge a committed run without a model: python3 judge.py runs/L1__<id> --level L1

# 0007 — assurance package: lint with live replay (solc + lake build)
python3 cycle/assurance/verify_package.py cycle/artifact_format/pilot-vaultasset-2026-06-26 --replay

# 0002/0004/0008 — Lean: kernel-checks every discharged lemma, prints the axiom audit
cd cycle/trusted/proofs/aave_arith && lake exe cache get && lake build && lake build AaveArith.NeuralProbe AaveArith.NeuralProbeCheck

# kprove-test — pinned K/KEVM spikes (see kprove-test/report.md and t*_report.md for commands and versions)
```

The replay seeds (`cycle/measurement/artifacts/*__spec.seed.json`), run transcripts
(`cycle/naive_loop/runs/`), verdict JSON and prover logs are committed as evidence.
They were produced on the author's machine and contain its absolute paths.

## Not committed, by design

- Aave-Vault sources and Certora specs (All Rights Reserved © Aave Labs): `cycle/ground_truth/aave_vault/fetch.sh` restores them at the pinned commit.
- `forge-std`, Mathlib (`.lake/`), Foundry `out/`/`cache/`, kompiled K definitions (`*-kompiled/`, `*.kore`): rebuilt by the commands above.
- The August bytecode-level line: [`tcg`](https://github.com/fu4re/tcg).

## Licence

MIT (see `LICENSE`), except the third-party and derived files listed in
`THIRD_PARTY.md` (MakerDAO `Vat` and the harnesses that inherit it are AGPL-3.0-or-later).
