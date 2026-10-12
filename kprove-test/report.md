# C9 Experimental Report — kprove/Kontrol behavior (A3a & C7 validation)

Observed behavior only. Every verdict carries: exact command, pinned versions +
hashes, a ≤20-line log fragment, and a local reproducer. Judge = the solver
(`kore-exec` / Kontrol), never prose.

Source task: [task.md](task.md). Prior blocked attempt archived in
[_old_reasearch/](_old_reasearch/) (could not run the Haskell backend under
amd64 Docker emulation on this arm64 host; now resolved with a native install).

## Verdicts at a glance

| Q | Verdict | Impact |
|---|---|---|
| **Q1** trusted mechanics | **`circularity-guarded`** ⛔ | trusted claim is applied only after ≥1 step, never from step 0 → **A3a induction step must be rewritten** (step-guard-compatible lemma). **Stop-rule HIT.** |
| **Q2** claim quantifier | **`all-path по умолчанию`** ✅ | K default `ALL_PATH`; Kontrol = all-path `APRProof` only → **H2 holds as-is**, no C3/C6 change. |
| **Q3** CSE coverage miss | **(ii) sound (guarded summary + fallback)** ✅ | precondition kept as a `requires` guard on the summary → no silent unsound application. **Stop-rule (iii) NOT hit.** CSE usable as a U-accelerator. |
| **Q4** ghost cell | **`только-форк-семантики`** (≈1 line) | external-module extension fails on KEVM's single top cell; needs a 1-line fork of `evm.md` → **vendored KEVM becomes a vendored fork (TCG-003 §3)**. |

**Two stop-rule conditions were checked: Q1 = `circularity-guarded` → TRIGGERED
(reported); Q3 = `(iii)` → NOT triggered.**

---

## Environment (pinned)

Native arm64 (Apple Silicon) toolchain installed via `kup` (Nix). Full capture:
[logs/versions.log](logs/versions.log).

| Component | Version | Commit / hash |
|---|---|---|
| kontrol | 1.0.255 | `0ac55eda300e64ec30300117fe71c02d6db59ab5` |
| K (kompile/kprove) | v7.1.337 | `4a46d1231473b599c699160132fd6e76a5c46406` |
| haskell-backend (`kore-exec`, `kore-rpc-booster`) | 0.1.155 | — |
| KEVM (bundled in kontrol) | 1.0.678 | — |
| kup | 0.2.6 | `2e3469d16437a2abe639e59123e1a25037ca205b` |
| foundry (`forge`) | 1.2.3-stable | `a813a2cee7dd4926e7c56fd8a785b54f32e0d10f` |
| solc | 0.8.35+commit.47b9dedd | — |
| OS | macOS 14.6 (23G80), Darwin 23.6.0, arm64 (M-series T6000) | — |

Install path: `bash <(curl https://kframework.org/install)` →
`kup install kontrol --version v1.0.255` + `kup install k --version v7.1.337`.
`kore-exec --version` now runs natively (no exit 137).

---

## Q1 — `trusted` mechanics: axiom or circularity? [P0]

### VERDICT: `circularity-guarded` ⛔ STOP-RULE TRIGGERED

A `trusted` claim is **assumed true** (never re-proved — a deliberately false
trusted claim is accepted, config (c) below), **but it is applied as a
step-guarded circularity**: the prover can use it as a rewrite only **after ≥1
execution step** from the goal's initial configuration, never from step 0.
Therefore A3a's induction step, as written on "trusted-claims applied as axioms
from step 0", does **not** hold as-is for K/kprove v7.1.337 — it must be
rewritten to a step-guard-compatible lemma. Reported immediately per the task's
stop-rule.

### Experiment design (why it is unambiguous)

Toy semantics in which the head symbol `q1Start` has **no** real rewrite rule.
The only way to leave a `q1Start(_)` head is a `trusted` lemma
`q1Start(1) => q1Claimed(1)`. Two designs differ only in whether a real step
precedes that head:

- **D1** — goal `q1Start(1) ~> q1Check(1) => .K`. No real step is available
  before the lemma would fire.
- **D2** — goal `q1Boot(1) ~> q1Check(1) => .K` with a real rule
  `q1Boot(I) => q1Start(I)`. Exactly one real step precedes the `q1Start` head.

Reading: D1 PROVED ⇒ axiom-from-step-0. D1 FAILED & D2 PROVED ⇒
circularity-guarded. D1 FAILED & D2 FAILED ⇒ trusted claim not applied at all.
(The legacy design in `_old_reasearch` put a *competing* real rule
`q1Start=>q1Real` on the lemma's own LHS, which under all-path branches into a
stuck `q1Real` state and fails regardless of trusted mechanics — a
false-negative trap. Removed here.)

### Results

| Config | Design | Lemma | kprove | Meaning |
|---|---|---|---|---|
| q1c-a-true-trusted | D1 | true, `[trusted]` | **FAILED** | lemma cannot fire at step 0 |
| q1c-c-false-trusted | D1 | false, `[trusted]` | **FAILED** | (step-0 blocked even for accepted lemma) |
| q1c-b-untrusted | D1 | true, not trusted | FAILED | lemma must be proved, no rule ⇒ stuck |
| **q1d-a-true-trusted** | **D2** | true, `[trusted]` | **PROVED** | lemma fires **after the 1 real step** |
| **q1d-c-false-trusted** | **D2** | **false**, `[trusted]` | **PROVED** | trusted claim **not re-proved** |
| q1d-nolemma | D2 | — (removed) | FAILED | negative control: lemma is the cause |
| q1d-b-untrusted | D2 | true, not trusted | FAILED | without `trusted`, lemma unprovable |

`D1 FAILED + D2 PROVED` ⇒ the trusted lemma is applied **only after ≥1 step** =
circularity-guarded. `q1d-c` (false trusted lemma, PROVED) ⇒ the prover does
**not** re-prove trusted claims — which is exactly why the DAG discipline
(re-running children) is needed, and why a step-0-axiom reading of A3a is unsafe.

### Command

```sh
./scripts/run-q1.sh          # kompiles both toy semantics, runs all 7 configs
```
Single case (the discriminator):
```sh
kompile repro/q1d/q1d-semantics.k --backend haskell \
  --main-module Q1D --syntax-module Q1D --output-definition repro/q1d/q1d-kompiled
kprove repro/q1d/q1d-a-true-trusted.k --definition repro/q1d/q1d-kompiled \
  --spec-module Q1D-A-TRUE-TRUSTED     # -> #Top (PROVED)
kprove repro/q1/q1c-a-true-trusted.k  --definition repro/q1/q1c-kompiled \
  --spec-module Q1C-A-TRUE-TRUSTED     # -> stuck at q1Start (FAILED)
```

### Log fragment (D1 vs D2 — the moment of application)

D1 `q1c-a-true-trusted` — trusted lemma present, but goal stuck at step 0
(the lemma did **not** rewrite the initial `q1Start` head):
```
(InfoReachability) while checking the implication
<k>
  q1Start ( 1 ) ~> q1Check ( 1 ) ~> _DotVar1 ~> .K
</k>
[Error] Prover: backend terminated because the configuration cannot be
rewritten further.
```
D2 `q1d-a-true-trusted` — identical lemma; one real step (`q1Boot=>q1Start`)
precedes the head, then the lemma fires and the goal closes:
```
#Top
```
(`logs/q1c-a-true-trusted.log`, `logs/q1d-a-true-trusted.log`.)

### Backend note

Standalone `kprove` drives the monolithic Haskell backend `kore-exec` 0.1.155
(verified: no booster flags in this `kprove`; it is the classic `kore-exec`
path). The step-guard for circularities lives in the reachability *procedure*,
shared by `kore-exec --prove` and the pyk/booster APRProof driver, so identical
behavior is expected on the booster — to be **confirmed** (Q3 exercises the
booster on real KEVM specs; a direct booster run of this toy is a follow-up, not
yet observed → not asserted).

### Reproducer

`repro/q1/` (D1), `repro/q1d/` (D2), `scripts/run-q1.sh`, logs `logs/q1c-*.log`,
`logs/q1d-*.log`.

---

## Q2 — Claim quantifier [P0]

### VERDICT: `all-path по умолчанию` ✅ (premise H2 satisfied)

At the K level a bare `claim` (no explicit `[all-path]`/`[one-path]` attribute)
defaults to **all-path** reachability, and Kontrol never overrides this: it
builds pyk `APRProof` objects, which implement all-path reachability *only*
(there is no one-path proof type in pyk). All 189 KEVM/Kontrol example specs in
the pinned tree carry **no** quantifier attribute. Premise H2 (theorem requires
all-path) holds as-is; no change to C3/C6 scope, and no need for our own claim
generation on this axis.

### (a) What `--default-claim-type` controls + default

`--default-claim-type` chooses the reachability quantifier applied to claims
that lack an explicit `[all-path]`/`[one-path]` attribute, i.e. the KORE
`SentenceType` used when translating the claim:

- `ALL_PATH` → operator `weakAlwaysFinally` (`wAF`, ∀◇) — all-path reachability.
- `ONE_PATH` → operator `weakExistsFinally` (`wEF`, ∃◇) — one-path reachability.

**Default = `ALL_PATH`.** Source (pinned K v7.1.337 tree):
- `k-frontend/.../backend/haskell/HaskellKRunOptions.java:34` —
  `public ModuleToKORE.SentenceType defaultClaimType = ModuleToKORE.SentenceType.ALL_PATH;`
- `k-frontend/.../backend/kore/ModuleToKORE.java:103-110` — `enum SentenceType { ONE_PATH, ALL_PATH }`, `ALL_PATH_OP = RL_wAF`, `ONE_PATH_OP = RL_wEF`.
- `ModuleToKORE.java:1017-1020` — per-claim resolution: `[one-path]` att → ONE_PATH, `[all-path]` att → ALL_PATH, else the default.

Empirical corroboration (`repro/q2-claimtype`): on a branching semantics where
all-path fails and one-path would pass, a **bare** claim FAILS exactly like
`--default-claim-type all-path`; and standalone `kprove`/`kore-exec` cannot
discharge a one-path claim at all (it reports the stuck sibling branch as
unrewritable), so all-path is the only quantifier actually provable here.

**When running through Kontrol:** `--default-claim-type` is never passed —
Kontrol constructs `APRProof` (all-path) directly. pyk
`proof/reachability.py:93-96`: *"Represent an all-path reachability proof.
APRProof and APRProver implement all-path reachability logic"*; no `OnePath`
proof type exists anywhere under `pyk/proof/`.

### (b) Quantifier on Kontrol-generated claims (from Foundry tests)

**Bare `claim`, no quantifier attribute.** A committed Kontrol-generated spec
in the pinned KEVM tree:
`tests/specs/kontrol/test-arithmetictest-test_wdiv_rounding-uint256-uint256-0-spec.k:6`
→ `claim [BASIC-BLOCK-8-TO-11]: <kevm> ... </kevm> ... [label(BASIC-BLOCK-8-TO-11)]`
— label only, no `[all-path]`/`[one-path]`. Proven as all-path via APRProof.

### (c) Quantifier on KEVM-practice specs

**None carry an explicit quantifier.** Across the pinned tree
(`kevm-source/tests/specs/**` + `media/**`): **0 of 189** `*-spec.k` files
contain `[one-path]` or `[all-path]`. Older style (`media/201908-trufflecon/add-spec.k:6`)
even uses a top-level `rule` in the spec module; modern ones use bare `claim`.
All default to all-path.

### Command

```sh
# (a) default value in source (pinned tree paths in report):
grep -n defaultClaimType .../HaskellKRunOptions.java     # = SentenceType.ALL_PATH
# (a) empirical branching check:
kompile repro/q2-claimtype/ct-semantics.k --backend haskell \
  --main-module CT --syntax-module CT --output-definition repro/q2-claimtype/ct-kompiled
kprove repro/q2-claimtype/ct-bare.k --definition repro/q2-claimtype/ct-kompiled \
  --spec-module CT-BARE                       # FAILED == all-path semantics
kprove ... --default-claim-type one-path      # also FAILED: one-path not provable standalone
# (b,c) attribute census:
grep -rlE "one-path|all-path" kevm-source/tests/specs kevm-source/media | wc -l   # -> 0
```

### Log fragment

```
ct-default              exit=1  FAILED=all-path-like
ct-forced-all-path      exit=1  FAILED=all-path-like
ct-forced-one-path      exit=1  (one-path not discharged: sibling branch `ctB` stuck)
--- source ---
HaskellKRunOptions.java:34  defaultClaimType = ModuleToKORE.SentenceType.ALL_PATH
ModuleToKORE.java:105-106   enum SentenceType { ONE_PATH, ALL_PATH }
0 of 189 KEVM/Kontrol *-spec.k files carry [one-path] or [all-path]
```

### Reproducer

`repro/q2-claimtype/` (ct-semantics.k, ct-bare.k), logs `logs/q2-ct-*.log`.
Source refs in the pinned Nix store: K src
`bgmlalvy7l0dz602gb1idhxd9hb669k0-k-7.1.337-*-src`, KEVM src
`l131dddkhs07w6gmrk4xqgbpfvn61x9m-kevm-source`, pyk under `kframework-7.1.0`.

---

## Q3 — CSE coverage miss [P1]

### VERDICT: (ii) — CSE is SOUND (guarded summary + fallback). Stop-rule NOT triggered.

A NatSpec `@custom:kontrol-precondition` is baked into the callee's summary **as
a `requires` guard**. The summary of `B.f` (precondition `x > 10`) is the
rewrite rule `... => ... requires ... andBool (10 <Int KV0_x) andBool ...`,
where `KV0_x` is the calldata argument `x`. By K's rule-application semantics a
guarded rule fires only where its `requires` is entailed by the path condition;
at a caller call-site with unconstrained `x` the guard `10 <Int x` is **not**
entailed, so the uncovered (`x ≤ 10`) case is **not** covered by the summary and
must fall back to real execution of `B.f`. Outcome **(ii)**; the unsound
outcome **(iii)** (silent summary application outside coverage) is ruled out by
construction.

### Evidence

Baseline (no `--cse`) — ground truth that the property is genuinely false:
```
❌ PROOF FAILED ❌ test%CoverageTest.test_coverage_miss(uint256)
    Assertion failed - assert() condition was false
    Path condition: { true == x <=Int 10 }
    Model: x = 0
```
CSE — `B.f` is summarized (`src%B.f … PASSED`), and the summary rule carries the
precondition as a guard (`kontrol show 'src%B.f(uint256)' --to-module`):
```
rule [BASIC-BLOCK-1-TO-3]: <foundry> … <output> _ => #buf(32, KV0_x) </output> …
  requires ( 0 <=Int KV0_x
     andBool ( 10 <Int KV0_x                <-- the precondition x > 10, guarding the summary
     andBool ( 0 <=Int C_B_ID … )))          [priority(20), label(BASIC-BLOCK-1-TO-3)]
```
(The `(ACCT_ID <=Int 0 orBool 10 <Int ACCT_ID)` clauses on *account* ids are
KEVM's standard precompile-exclusion `id ∉ 1..9`, not the precondition.)

### Honest caveat (could-not-reproduce, with X)

The **end-to-end** `--cse` proof of `test_coverage_miss` did not complete: its
`setUp` crashed with an SMT sort error
`Sorts SortAccount and Int are incompatible` — a KEVM/booster fragility that
appears on the `--cse` path (the non-CSE `setUp` succeeds). So the *guarded
fallback was not observed executing*. This does not weaken the verdict: (a) a
crash is an honest failure, never a silent green; (b) the summary's `requires`
guard is present and dispositive — K cannot apply the summary where `x ≤ 10`.
The stop-rule (iii) is therefore not met.

### Unsupported precondition (mapping access)

**Explicit warning, then dropped (not silent).** With
`@custom:kontrol-precondition m[0] > 10` on `D.h`:
```
WARNING kontrol.natspec - Array/mapping access not supported yet
```
Kontrol emits the warning and proceeds **without** the precondition (summarizes
`D.h` for all inputs — conservative/sound, just weaker). Source of the behavior:
`kontrol/natspec.py` (`sgp_ast_to_kast` → warning; unparsed preconditions are
not added as constraints).

### Command

```sh
cd repro/q3-cse
kontrol build
kontrol prove --match-test 'CoverageTest.test_coverage_miss' --reinit        # baseline: FAILS, x<=10
kontrol prove --cse --match-test 'CoverageTest.test_coverage_miss' --reinit   # summarizes B.f (setUp SMT-crash caveat)
kontrol show  'src%B.f(uint256)' --to-module                                  # shows `requires 10 <Int KV0_x`
cd ../q3-mapping && kontrol build
kontrol prove --cse --match-test 'MappingTest.test_mapping_precond' --reinit --verbose  # -> WARNING Array/mapping access not supported yet
```

### Reproducer

`repro/q3-cse/` (B.f precondition x>10, caller with unconstrained x),
`repro/q3-mapping/` (mapping-access precondition). Logs:
`logs/q3-prove-baseline.log`, `logs/q3-run2.log` (baseline+cse+summary),
`logs/q3-mapping-prove.log`, `logs/q3-kontrol-build*.log`.

---

## Q4 — KEVM ghost cell [P2]

### VERDICT: `только-форк-семантики` (fork required for KEVM). Minimal edit ≈ 1 line / 1 file.

K lets an **external** module add a configuration cell **only when the base
configuration already has ≥2 top cells** — then K has synthesized an
auto-`<generatedTop>` wrapper, which is extensible across modules. **KEVM's
configuration has a single user-declared top cell `<kevm>`** (evm.md:34-36), so
there is no `<generatedTop>`, and adding a ghost cell from a pure external
module **fails** — both as a top-level sibling and by re-opening `<kevm>` —
with `Too many top cells`. To add the cell you must edit the `configuration`
block in `evm.md` (a fork of the vendored semantics). The cell, once declared,
**is** visible/constrainable in claim Pre/Post. Consequence for TCG-003 §3: the
vendored KEVM becomes a vendored **fork**; A5 stands, C7 gets a fork-maintenance
task.

### Evidence (matrix)

| Case | Base top cells | How the ghost cell is added | `kompile` |
|---|---|---|---|
| toy `EXT-ADDCELL` | 2 (`<k>`,`<acct>`) → auto `<generatedTop>` | external module, sibling | **BUILT** (merged: `<k> <acct> <callCounter>` under `<generatedTop>`) |
| toy `EXT-SINGLE-SIBLING` | 1 (`<top>`) | external module, sibling | **FAILED** `Too many top cells` |
| toy `EXT-SINGLE-NESTED` | 1 (`<top>`) | external module, re-open `<top>` | **FAILED** `Too many top cells` |
| `KEVM-EXT` (imports EVM) | 1 (`<kevm>`) | external module, sibling | **FAILED** `Too many top cells: HashSet(KevmCell, CallCounterCell)` |
| `KEVM-EXT2` (imports EVM) | 1 (`<kevm>`) | external module, re-open `<kevm>` | **FAILED** `Too many top cells` |
| `KEVM-FORK` | 1 (`<kevm>`) | **1-line edit inside `<kevm>` in evm.md** | **BUILT** (see below) |

(a) **Can K extend the config from an imported module?** Only via the
auto-`<generatedTop>` (needs ≥2 top cells). KEVM's single `<kevm>` top cell has
none, so no. (b) **Minimal invasiveness for KEVM:** 1 line in 1 file — add
`<callCounter> 0 </callCounter>` inside the `<kevm>` `configuration` in
`evm.md`. (Rules that *update* the ghost cell can then live in an external
module; only the cell **declaration** must be in the semantics.) (c) **Visible
in claims?** Yes — proven on the toy:

```
claim <k> 5 => 6 </k> <acct> A => A +Int 5 </acct>
      <callCounter> C => C </callCounter>  requires C >=Int 0     -> #Top (PROVED)
```

### Minimal fork diff (evm.md)

```diff
         <useGas> $USEGAS:Bool </useGas>
+        <callCounter> 0 </callCounter>   // GHOST CELL (fork: 1 line)
```

### Command

```sh
# external-module attempts (all fail on KEVM's single top cell):
kompile repro/q4-ghost/kevm-ext.k  --backend haskell -I <evm-sem> -I <plugin> --main-module KEVM-EXT   # Too many top cells
kompile repro/q4-ghost/kevm-ext2.k --backend haskell -I <evm-sem> -I <plugin> --main-module KEVM-EXT2  # Too many top cells
# toy proof that the mechanism only works with an auto-generatedTop base:
kompile repro/q4-ghost/ext-addcell.k --backend haskell --main-module EXT-ADDCELL     # BUILT
kompile repro/q4-ghost/ext-single-sibling.k --backend llvm --main-module EXT-SINGLE-SIBLING  # Too many top cells
# the 1-line fork builds:
kompile repro/q4-ghost/kevm-fork.k --backend haskell -I repro/q4-ghost/fork -I <evm-sem> -I <plugin> --main-module KEVM-FORK
# ghost cell is constrainable in a claim:
kprove repro/q4-ghost/ext-claim.k --definition repro/q4-ghost/ext-addcell-kompiled --spec-module EXT-CLAIM  # #Top
```

### Reproducer

`repro/q4-ghost/` — `base.k`/`ext-addcell.k` (toy, works), `base-single.k` +
`ext-single-{sibling,nested}.k` (single-top-cell, fail), `kevm-ext.k`,
`kevm-ext2.k` (KEVM external, fail), `fork/evm.md` + `kevm-fork.k` (1-line fork),
`ext-claim.k` (ghost cell in a claim). Logs `logs/q4-*.log`.
