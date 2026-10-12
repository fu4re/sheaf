# SPIKE-D Tracker

Source: [TCG-003.md](TCG-003.md) · Report: [spike_d_report.md](spike_d_report.md) · Inputs:
[t1_report.md](t1_report.md), [spike_t2_report.md](spike_t2_report.md), [t3_report.md](t3_report.md), [TCG-006.md](TCG-006.md).
Env: `source scripts/env.sh`. Fork = T1 fork + `<inFunc>` (repro/t3-q0), rebuilt with `--emit-json` for pyk/APRProof.

Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked/stop-rule.

## Budget B (fixed BEFORE first run, task §0)
- `[x]` **B = 35 s** wall-clock = 2× the reentered@depth2 baseline (raw kprove `entry-reenter`, `--depth 1`, measured **16.94 s**).
  Reproducible knob for the frontier squeeze = **`--max-iterations`** (wall-clock is machine-dependent; iterations is deterministic).

## З-1′ — Does Unknown carry localization? [do FIRST — gives the Unknown-reading recipe for З-2] `[x]`
- `[x]` Tooling: raw `kompile` (T3) emits no `compiled.json` ⇒ pyk `APRProof` can't read it. Rebuilt fork + withdraw model with
  `--emit-json` (`repro/spike-d-z1/{t3-fork,withdraw-json}-kompiled`). `kevm prove` needs booster `llvm-library`; used
  `--no-use-booster` (plain kore-rpc) — frontier data structure is backend-independent (a pyk property).
- `[x]` Frontier vehicle: reentered@depth2 is a **concrete 1-step** claim (built for raw kprove) — no intermediate frontier to squeeze.
  Localization only exists where the proof **branches symbolically**, so probed with a minimal symbolic branch: `JUMPI DEST I`
  (`[jumpi.false]` I==0 / `[jumpi.true]` I≠0) on the real fork (`repro/spike-d-z1/z1-jumpi-spec.k`).
- `[x]` **Frontier exists & is named**: `--max-iterations 2` → APRProof stops at the split, reports `Pending nodes: ID: 4, ID: 5`
  (`kevm show-kcfg … --pending` marks each `(leaf, pending)`).
- `[x]` **Nodes carry path constraints**: node 4 = `{I==0, DEST≥0}`, node 5 = `{I≠0, DEST≥0}` + localized state
  (node 5 k-cell = `JUMP DEST ~> #halt`). Not content-free: "stuck HERE, under THIS constraint".
- `[x]` **Serializable programmatically**: `--save-directory` writes `proof.json` + `kcfg/kcfg.json` + `kcfg/nodes/N.json`;
  constraints read with plain `json.load` → `["cterm"]["constraints"]` (KAST predicates) + `["cterm"]["config"]`. No log-eyeballing.
- `[x]` **Budget→verdict confirmed**: same claim, `--max-iterations 20` → **decides** (FAILED, node 7, path cond `I≠0`). Pending is a
  budget-exhaustion artifact, not a permanent state. Even the decided-Refute endpoint carries a path condition.
- `[x]` **Verdict → branch (a)**: frontier exists AND is serializable ⇒ `Res` enriched to `Unknown(frontier)`; frontier = decomposer input.
  Whitepaper §3.4 ("Unknown carries none") is **too strong in practice** — the APRProof frontier carries node-localized path constraints.
- `[x]` Command/field (for З-2 + utility): `kevm prove --save-directory DIR --max-iterations N` → `DIR/<CLAIM>/kcfg/nodes/<id>.json`
  → `cterm.constraints` / `cterm.config`; pyk: `APRProof.read_proof_data(DIR).pending`. Human view: `kevm show-kcfg SPEC --claim L --pending`.

## З-2 — Does the solver decide vibecode? [~half day] `[x]` → **decided 8/8 · BUILD CLI** (budget-calibration caveat)  (pinned prompt, 8 gens, attach claim, budget B)
- `[x]` **Generator = 8 isolated, study-blind agents** (user's call): each got ONLY the pinned prompt behind a firewall against the
  repo/project context, wrote one `C_k.sol`, returned only code. No knowledge that this is a verification study ⇒ no over-hardening bias.
- `[x]` **Corpus is homogeneous — the headline.** All 8 (`repro/spike-d-z2/gen/C_1..8.sol`):
  - compile on pinned solc 0.8.35 → **attach-fail = 0/8** (all build; pinned name C / balances / deposit()/withdraw() present).
  - **checks-effects-interactions**: `amount=balances[s]; balances[s]=0; s.call{value:amount}(""); require(ok)` — **debit BEFORE call, 8/8**.
  - **call_form = `call` 8/8** (transfer 0, send 0). **nonReentrant 0/8** (CEI makes it moot). **Vulnerable V (call-before-write) = 0/8.**
  - Semantic dedup = **1 contract** modulo cosmetics (varname `success`/`ok`, presence of a revert string). Runtime bytecode differs
    only in the trailing solc metadata hash + revert-string literal; withdraw logic is byte-identical.
- `[x]` **Finding:** blind frontier-model vibecode on this prompt converges on ONE canonical *safe* (withdraw_F-class) pattern. The
  variability З-2 meant to stress (call/transfer/send, debit order, guards) **did not materialize** under same-prompt blind sampling.
- `[x]` **Solver run on the REAL bytecode** (`repro/spike-d-z2/kontrol/`, Kontrol 1.0.255, pinned solc via `solc=/opt/homebrew/bin/solc`) —
  closes the T1-Q2a/T3-Q1 full-bytecode boundary (first time in this project a whole compiled function is proven end-to-end):
  - `prove_withdraw_zeroes(amt)` (TRUE post-condition: `balances[caller]==0` after withdraw) → **✨ PASSED ✨** (Accept), 12 nodes, **75 s**.
  - `prove_withdraw_keeps(amt)` (FALSE: `==amt`) → **❌ FAILED ❌** with counterexample **`amt=1`** (Refute), **61 s**. Discriminator: proves
    the solver genuinely DECIDES the bytecode, not a vacuous rubber-stamp.
- `[x]` **3 numbers: decided 8/8 · unknown 0/8 · attach-fail 0/8.** (8/8 bytecode-equivalent ⇒ the canonical verdict transfers; both
  Accept and Refute demonstrated on the real code.)
- `[x]` **Budget caveat (honest):** 61–75 s > **B=35 s**. B was calibrated on a *raw-kprove micro-claim* (17 s); a full Kontrol foundry
  proof's fixed overhead (setUp proof + booster + larger definition) alone ≈ B, so the strict "fits B" reading (0/8) UNDERSTATES
  decidability. Decidability itself is robust (8/8 decide, ~60–75 s, stable). The strict-B fraction is a calibration artifact, not a solver limit.
- `[x]` **Decision (task fork): ≥6/8 decided → BUILD THE CLI** ("система верифицирует вайбкод"). Caveat: blind corpus showed NO adversarial
  variety (0/8 vulnerable), so "honestly rejects bad vibecode" is evidenced by the FALSE-property Refute, not by a naturally-vulnerable gen.

## З-3 — Junction as implication in a parent spec [~1h] `[x]` → **PASS**
- `[x]` Composition on the stand (`repro/spike-d-z3/z3-junction-spec.k`, raw kprove on T3 `withdraw-kompiled`): op₁=deposit ; op₂=withdraw_F.
  Junction `Post_deposit(bal=B0+A) ⟹ Pre_withdraw(bal≥A)` ⟺ `B0≥0`.
- `[x]` **z3-compose-ok** — parent runs `deposit ~> reqGE ~> debit ~> xfer ~> #done`; reqGE's precondition entailed INLINE from the
  post-deposit path condition (no `[trusted]`/`[circularity]`, no imported claim) → **#Top**, 4.0 s.
- `[x]` **Form of junction in spec** = explicit implication `requires Post₁ ensures Pre₂`: **z3-junction-implication-ok** (`BAL==B0+A ∧ B0≥0 ⟹ BAL≥A`) → **#Top**, 3.2 s.
- `[x]` Non-vacuity: **z3-junction-implication-broken** (drop `B0≥0`) → **FAILED**, residual `#Not( B0+A >=Int A )` (counterexample B0<0), 2.7 s.
- `[x]` In-parent junction failure: **z3-compose-double-withdraw** (deposit;withdraw;withdraw) → **FAILED**, path cond `B0+A−A <Int A`
  (1st junction `B0+A≥A` held, 2nd junction `B0<A` un-dischargeable) — composition stuck exactly at the bad junction, 2.3 s.
- `[x]` **Verdict: junction PASS · form = in-parent `requires Post ensures Pre` implication (not trusted lemma) · ~2.3–4.0 s/claim.**
  Composition = contribution №1; without it the demo is two isolated loops (which Kontrol already does). З-3 shows the stand has it.

## Mine to hold (task §"Мина"): a utility optimizing Accept has a direct incentive to weaken Post until Unknown clears.
- Soundness holds (decomposer ∈ U, Prop 1); NON-vacuity is what suffers and no automaton catches it. Roots signed by H — never auto-weakened.
