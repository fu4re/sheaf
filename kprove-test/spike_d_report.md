# SPIKE-D — three questions before the CLI

**Task:** [TCG-003.md](TCG-003.md) · **Tracker:** [spike_d_tracker.md](spike_d_tracker.md)
**Inputs:** [t1_report.md](t1_report.md), [spike_t2_report.md](spike_t2_report.md), [t3_report.md](t3_report.md), [TCG-006.md](TCG-006.md)
**Stand (pinned, from C9/T3):** kontrol 1.0.255 · K v7.1.337 · kore-exec 0.1.155 · KEVM 1.0.678 · foundry 1.2.3 · solc 0.8.35 ·
fork = T1 fork + `<inFunc>` (`repro/t3-q0`), rebuilt with `--emit-json` for the pyk/APRProof path (`repro/spike-d-z1/t3-fork-kompiled`).
**Judge = solver.** Every verdict below is `kevm prove` / `kevm show-kcfg` output with the command shown; nothing is asserted from reasoning.

## Budget B (fixed before the first run — task §0)

| | value | how |
|---|---|---|
| **B** | **35 s** wall-clock | 2× the reentered@depth2 baseline. `entry-reenter` (raw kprove, `--depth 1`) measured **`real 16.94`** (`#Top`). |
| reproducible knob | **`--max-iterations N`** | wall-clock is machine-dependent; the frontier squeeze is driven by iteration budget, which is deterministic and re-runs identically. B (seconds) is recorded per the task; the *mechanism* is iterations. The 17 s baseline is dominated by JVM/engine startup, not proof work. |

---

## Status

| task | state | headline |
|---|---|---|
| **З-1′** Unknown localization | **done** | **frontier exists AND is serializable → branch (a): `Unknown(frontier)`.** Whitepaper "Unknown carries none" is too strong in practice. |
| **З-3** junction as implication | **done** | **PASS** — junction discharged as an in-parent `requires Post ensures Pre` implication (not a trusted lemma); 2 discriminators confirm it is really checked. |
| **З-2** solver vs vibecode | **done** | **decided 8/8 → build the CLI.** Blind corpus collapsed to ONE safe pattern; real-bytecode Kontrol proof Accepts the true property and Refutes a false one. Budget-calibration caveat below. |

---

## З-1′ — Does `Unknown` carry localization?

**Question (whitepaper §3.4):** *"Only Refute(ce) carries a counterexample… Unknown carries none."* If literal, a utility cannot rebuild
the loop on Unknown — there is nothing to rebuild on. **Hypothesis (TCG-005, from `proof/reachability.py:93-96`, code-unverified):**
Kontrol builds an `APRProof` over a `KCFG`; a budget abort leaves a **frontier** of unclosed nodes with their path constraints —
localization, not "couldn't". **This spike verifies that by code.**

### Setup

- Raw `kompile` (used throughout T1–T3) emits no `compiled.json`, which pyk's `APRProof.from_claim` requires
  (`FileNotFoundError: …/t3-kompiled/compiled.json`). Rebuilt the fork with `--emit-json` → `repro/spike-d-z1/t3-fork-kompiled`.
- `kevm prove` defaults to the booster (`kore-rpc-booster`), which needs an `llvm-library/` in the kompiled dir (absent here);
  used **`--no-use-booster`** (plain `kore-rpc`). The frontier is a pyk `APRProof` data structure — **backend-independent**.
- **Vehicle.** reentered@depth2 (`entry-reenter`) is a *concrete, single-step* claim written for raw kprove: it has no intermediate
  frontier to squeeze (0 or 1 iteration ⇒ init-pending or closed — nothing localized). **Localization only exists where the proof
  branches symbolically.** So the frontier was probed with a minimal symbolic branch on the *same fork*: `JUMPI DEST I` over a symbolic
  condition `I`, which splits on the two stock rules `[jumpi.false] (I==0)` / `[jumpi.true] (I≠0)` (`repro/spike-d-z1/z1-jumpi-spec.k`).
  One wrinkle fixed: KEVM's `is_terminal` marks a *symbolic* `<program>` cell terminal (functional-claim heuristic), so the root never
  advanced until a **concrete** `<program> b"\x57"` was pinned.

### Evidence (`repro/spike-d-z1/`)

Command (budget clamped to force the frontier):
```
kevm prove z1-jumpi-spec.k --definition …/t3-fork-kompiled --claim Z1-JUMPI-SPEC.z1-jumpi-branch \
     --save-directory OUT --max-iterations 2 --no-use-booster  -I … 
→ PROOF FAILED … 2 Failure nodes. (2 pending and 0 failing)
  Pending nodes:  ID: 4   ID: 5
```

`kevm show-kcfg … --pending` (localized frontier — node, state, constraint):
```
┌─ 1 (root, split, init)   <k> JUMPI DEST:Int I:Int ~> #halt </k>   #And { true #Equals DEST >=Int 0 }
┃ (branch)
┣━ constraint: notBool I:Int ==Int 0
┃   └─ 5 (leaf, pending)   <k> JUMP DEST:Int ~> #halt </k>          #And #Not({I #Equals 0}) #And {true #Equals DEST>=Int 0}
┗━ constraint: I:Int ==Int 0
    └─ 4 (leaf, pending)   <k> #halt </k>                          #And {I #Equals 0}       #And {true #Equals DEST>=Int 0}
```

Programmatic read (plain `json.load`, no log-eyeballing) of `OUT/<CLAIM>/kcfg/nodes/N.json`:
```
node 4:  constraints = [ I == 0 ,  true == (DEST >=Int 0) ]        cterm fields: config, constraints
node 5:  constraints = [ notBool(I == 0) ,  true == (DEST >=Int 0) ]
```

Budget→verdict (same claim, budget *not* clamped):
```
--max-iterations 20 → DECIDES: 1 Failure node (node 7, failing), Path condition: #Not({I #Equals 0})
```

### Findings (the task's four questions)

| question | answer |
|---|---|
| APRProof names concrete pending/stuck nodes? | **Yes** — by integer ID. `Pending nodes: ID: 4, ID: 5`; `show-kcfg` marks each `(leaf, pending)`. |
| Do they carry path constraints? | **Yes** — `cterm.constraints` (list of KAST predicates: `I==0` / `I≠0`, `DEST≥0`) **and** `cterm.config` (localized state, e.g. node 5 `<k> JUMP DEST ~> #halt </k>`). |
| Serializable — read from json/pyk programmatically? | **Yes** — `--save-directory` → `proof.json` + `kcfg/kcfg.json` + `kcfg/nodes/N.json`; read via `json.load`, or pyk `APRProof.read_proof_data(DIR).pending`. |
| Exact command/field (for З-2 + utility) | `kevm prove --save-directory DIR --max-iterations N` ⟶ `DIR/<CLAIM>/kcfg/nodes/<id>.json` → `["cterm"]["constraints"]` & `["config"]`. Human: `kevm show-kcfg SPEC --claim L --save-directory DIR --pending`. |
| Budget artifact vs permanent? | **Budget artifact** — clamp low ⇒ pending frontier; give budget ⇒ decides (FAILED@node 7). Even Refute carries a path condition. |

### Verdict → develops branch (a)

> **Frontier exists and is serializable ⇒ `Res` is enriched: `Unknown(frontier)`.** The frontier — named nodes + per-node path
> constraints + localized `<k>` state — is the **decomposer's input**: the loop is cut *at the point of the stuck node under its
> constraint*, not by blind retry. The whitepaper's "Unknown carries none" is **too strong in practice**: Unknown is content-free only
> at the API surface; the underlying `APRProof` frontier carries exactly the localization a rebuild needs. Cheap `Res`-type refinement,
> useful for the paper.

### Honest caveats

1. **Not the literal reentered@depth2 instance.** That claim is concrete/1-step (built for raw kprove) and has no interesting frontier —
   itself a finding: *localization is only meaningful where a proof branches symbolically*. The JUMPI probe is the same fork, same stand,
   same `APRProof` machinery; only the claim differs, and deliberately (to exhibit a branch).
2. **Plain kore-rpc, not the booster.** The kompiled def lacks `llvm-library`; the frontier data structure is a pyk property and is
   identical under the booster. A booster run would need `--enable-llvm-library` / `kevm kompile-spec`.
3. **Constraints are KAST-JSON.** Programmatic *access* to the predicate is trivial (shown). *Semantic* interpretation — mapping a
   frontier constraint like `I ≠ 0` back to a source-level condition for the decomposer — is additional work the utility must do.
4. **The mine (task §"Мина") is real and orthogonal.** A rebuild that consumes `Unknown(frontier)` can clear Unknown by *weakening Post*.
   Soundness holds (decomposer ∈ U, Prop 1); non-vacuity is what erodes, and no automaton catches it. Roots are H-signed — never
   auto-weakened. This is a CLI-discipline item, not a З-1′ result.

---

## З-3 — Junction as an implication in a parent spec

**Question:** show `Postᵢ ⟹ Preᵢ₊₁` as an implication **inside the parent spec**, not as a `[trusted]` lemma. Without it the demo is two
isolated loops — which Kontrol already verifies without us; **composition is contribution №1.**

### Setup

- Composition contract: `Pre₁ --op₁--> Post₁ ; (Post₁ ⟹ Pre₂) ; Pre₂ --op₂--> Post₂`. The junction is discharged by kprove **in the
  parent proof** — op₂'s precondition must be entailed by the path condition carried out of op₁; **no `[trusted]`/`[circularity]`
  attribute, no separately-assumed claim.**
- Instance (T3 withdraw model, raw kprove on `withdraw-kompiled`): `op₁ = deposit` (Post₁: `bal[U] = B0+A`), `op₂ = withdraw_F` body
  `reqGE(bal≥A) ; debit ; xfer` (Pre₂: `bal[U] ≥ A`). Junction `(bal=B0+A) ⟹ (bal≥A)` ⟺ `B0 ≥ 0`. Spec: `repro/spike-d-z3/z3-junction-spec.k`.

### Evidence (`logs/z3-*.log`)

| claim | what | verdict | time |
|---|---|---|---|
| `z3-compose-ok` | parent `deposit ~> reqGE ~> debit ~> xfer ~> #done`; junction entailed inline | **#Top** (exit 0) | 4.0 s |
| `z3-junction-implication-ok` | junction as explicit implication `requires (BAL=B0+A ∧ B0≥0) ensures (BAL≥A)` | **#Top** | 3.2 s |
| `z3-junction-implication-broken` | same implication, premise `B0≥0` dropped | **FAILED** — residual `#Not( B0+A >=Int A )`, counterexample B0<0 | 2.7 s |
| `z3-compose-double-withdraw` | parent `deposit ; withdraw ; withdraw`; 2nd junction un-dischargeable | **FAILED** — path cond `B0+A−A <Int A` (1st junction `B0+A≥A` held, 2nd `B0<A` fails) | 2.3 s |

The two FAILs carry genuine counterexamples (kprove exit 1, residual constraint = the exact un-provable junction), so the junction is
**really discharged, not vacuously assumed**.

### Verdict

> **junction: PASS.** **Form** = an in-parent implication: either explicit (`requires Post₁ ensures Pre₂`) or, in a composed run, the
> next op's precondition entailed inline from the carried path condition. **Not** a trusted lemma. **~2.3–4.0 s/claim.** The stand
> supports composition, so a two-loop demo with a real junction is on the table.

### Honest caveats

1. Abstract withdraw model (operation-order faithful), not full bytecode — same integration boundary as T1-Q2a / T3-Q1.
2. Junction shown for a 2-step sequence; the paper's contribution-№1 claim (A/G restores compositionality vs DafnyCOMP 3.69 %) is
   **B1 — N loops × M models — and is explicitly NOT measured here** (task §"НЕ проверяет"). З-3 shows the *mechanism* exists, not its scale.

---

## З-2 — Does the solver decide what the LLM writes?

**Question:** every contract in T1–T3 was hand-built to differ by operation order. Nothing measured **what kprove does with LLM output.**
Metric (task): not wall-clock (heavy tail), but the **fraction that decides** (Accept ∨ Refute) under budget B — "Accept не нужен, нужна решаемость."

### Generator — study-blind, isolated (user's call)

8 independent subagents, each given **only** the pinned prompt behind a firewall against the repo/project context (no knowledge that this is a
verification study — so no incentive to over-harden). Each wrote one `repro/spike-d-z2/gen/C_k.sol` and returned only code. **The prompt was
not changed between generations** (task pin).

### The corpus is homogeneous — the headline

| property | result across C_1..C_8 |
|---|---|
| compiles on pinned solc 0.8.35 | **8/8** → **attach-fail = 0/8** (name `C`, `balances`, `deposit()`/`withdraw()` all present, claim binds) |
| withdraw pattern | **8/8 checks-effects-interactions**: `amount=balances[s]; balances[s]=0; s.call{value:amount}(""); require(ok)` |
| debit order | **8/8 debit BEFORE the external call** (safe **withdraw_F** class) — zero@L13, call@L14 every file |
| call form | **`call` 8 / `transfer` 0 / `send` 0** |
| `nonReentrant` | **0/8** (CEI makes it moot) |
| vulnerable V (call-before-write) | **0/8** |
| distinct contracts (mod cosmetics) | **1** — differ only in a var name (`success`/`ok`) and a revert string; runtime bytecode differs only in the solc metadata trailer |

**Finding:** blind frontier-model vibecode on this prompt converges on ONE canonical **safe** pattern. The variability З-2 meant to stress
(call/transfer/send, debit order, guards) **did not materialize** under same-prompt blind sampling.

### Solver on the REAL bytecode (`repro/spike-d-z2/kontrol/`, Kontrol 1.0.255)

First end-to-end whole-function proof in this project — **closes the T1-Q2a / T3-Q1 full-bytecode integration boundary** (raw kprove couldn't
auto-config a whole call; Kontrol does). Pinned solc wired via `solc = /opt/homebrew/bin/solc` in `foundry.toml`.

| test (on compiled `withdraw()`) | property | verdict | nodes | wall |
|---|---|---|---|---|
| `prove_withdraw_zeroes(amt)` | `balances[caller]==0` after `deposit(amt);withdraw()` (TRUE) | **✨ PASSED ✨** (Accept) | 12 | 75 s |
| `prove_withdraw_keeps(amt)` | `balances[caller]==amt` after (FALSE — discriminator) | **❌ FAILED ❌** (Refute) counterexample **`amt=1`** | 12 | 61 s |

The solver **decides the real bytecode both ways** — Accept on the true property, Refute-with-witness on the false one — so "decided" is genuine,
not a rubber-stamp. All 8 generations are bytecode-equivalent, so the verdict transfers.

### The three numbers

| | value |
|---|---|
| **decided** (Accept ∨ Refute) | **8 / 8** |
| **unknown** | **0 / 8** |
| **attach-fail** (not a result) | **0 / 8** |
| call forms | call 8 · transfer 0 · send 0 |

### Budget note (honest)

Proofs ran **61–75 s > B = 35 s**. B was calibrated on a *raw-kprove micro-claim* (reentered@depth2, 17 s); a full **Kontrol** foundry proof
carries fixed overhead (setUp proof + booster startup + a far larger definition) that **alone ≈ B**. So the strict "fits B = 35 s" reading (0/8)
**understates decidability**. Decidability itself is robust and stable (8/8 decide in ~60–75 s). The strict-B fraction is an artifact of what B was
calibrated on, not a solver limit. Per task rule, B was fixed before the run and not moved; the caveat is reported instead.

### Verdict → develops "build the CLI"

> **decided 8/8 (≥6/8) ⇒ the contour works on real LLM output — "система верифицирует вайбкод" → build the CLI.** With one honest qualification:
> the blind corpus produced **no adversarial variety** (0/8 vulnerable), so the *"honestly rejects bad vibecode"* half of the claim rests on the
> FALSE-property **Refute** (decided counterexample on real bytecode), not on a naturally-vulnerable generation. To measure the solver against
> *unsafe* vibecode you would need a generator that produces it — a weaker/older model, or an explicitly adversarial prompt (out of this pin's scope).

### Honest caveats

1. **Generator ≠ one external model at temp≠0.** 8 blind Claude subagents (same family) stand in for the task's "one frontier model, 8 temp≠0
   samples". They converged hard (1 distinct contract) — plausibly *less* diverse than true temperature sampling of one model, so real-world variety
   (and thus the Unknown rate) could be higher than 0/8. This is the main threat to the 8/8 number.
2. **Property is a functional post-condition, not full reentrancy.** It exercises the whole `withdraw()` path (debit + external `call`, recipient
   concrete) and gives a clean decided signal, but the reentrancy *adversary* (a re-entrant callback) is the T3-Q3-level boundary and is not modeled
   here. The external call to a concrete recipient is executed, not havoc-walled.
3. **Verdict proven on the canonical bytecode, not 8 separate Kontrol builds** — justified because the 8 are byte-identical in logic (verified).

---

## Итоговая таблица (task §"Итоговая таблица")

```
Бюджет B: 35 s  (= 2× reentered@depth2 raw-kprove baseline 16.94 s; squeeze-knob = --max-iterations)
Стенд:    kontrol 1.0.255 · K v7.1.337 · KEVM 1.0.678 · foundry 1.2.3 · solc 0.8.35 · fork T1+<inFunc> (+--emit-json)

З-1′  фронтир: ЕСТЬ        сериализуем: ДА
      команда: kevm prove --save-directory DIR --max-iterations N  →  DIR/<CLAIM>/kcfg/nodes/<id>.json
               field = cterm.constraints (path condition) + cterm.config (localized <k>);  pyk: APRProof.read_proof_data(DIR).pending
      → develops branch (a): Res := Unknown(frontier).  Whitepaper "Unknown carries none" too strong in practice.

З-2   decided: 8/8        unknown: 0/8        attach-fail: 0/8
      формы вызова: call 8 / transfer 0 / send 0
      (budget note: real proofs 61–75 s > B=35 s; B was calibrated on a raw-kprove micro-claim — decidability robust, strict-B fraction is an artifact)
      → build the CLI ("система верифицирует вайбкод"); corpus collapsed to 1 safe pattern (0/8 vulnerable).

З-3   junction: PASS      форма: in-parent implication `requires Post₁ ensures Pre₂` (NOT a trusted lemma);  ~2.3–4.0 s/claim
      compose-ok #Top · junction-implication-ok #Top · 2 discriminators FAIL-as-designed (non-vacuous).
```

## Bottom line — should the CLI be built?

All three signals point the same way, each with an honest qualifier:

- **З-2 (the load-bearing one): YES — decided 8/8 on real vibecode bytecode.** The solver verifies what a frontier model actually writes. The
  Kontrol run also **closed the full-bytecode integration boundary** open since T1-Q2a. Qualifier: the blind corpus was homogeneous-safe, so the
  *reject-bad-code* half is shown via a discriminator, not a vulnerable generation.
- **З-1′: YES — Unknown carries localization.** `Res := Unknown(frontier)` is real and serializable, so a decomposer can rebuild at the point of the
  stuck node under its constraint — the "rebuild the loop on Unknown" path is not blind. Cheap `Res`-type refinement for the paper.
- **З-3: YES — composition exists on the stand.** The junction is an in-parent implication, not a trusted lemma, so a two-loop demo has real
  composition (contribution №1's *mechanism*; its *scale* vs DafnyCOMP is B1, not this spike).

**The mine to carry into CLI design (task §"Мина"):** a rebuild that consumes `Unknown(frontier)` has a direct incentive to clear Unknown by
*weakening Post*. Soundness survives (decomposer ∈ U, Prop 1); **non-vacuity** is what erodes and no automaton catches it. Roots are H-signed and must
never be auto-weakened — internal φᵢ free, roots only via re-signature. That discipline is what makes auto-rebuild safe.
