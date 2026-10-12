# SPIKE-A Tracker

Source: [task.md](../task.md) · Report: `spike_a_report.md` (pending) · Predecessor: [spike_d_report.md](spike_d_report.md).
Env: `source scripts/env.sh`. Stand: **raw kprove + KEVM 1.0.678 + K v7.1.337 + solc 0.8.35** (kontrol-дистрибутив НЕ используется).
Legend: `[ ]` todo · `[~]` in progress · `[x]` done · `[!]` blocked/stop-rule.

## Budgets (fixed BEFORE first prove run, task §0)
- `[x]` **B_byte = 120 s** wall-clock. Basis (recorded): raw-kprove micro-claim = 17 s; spike-D full Kontrol proof = 61–75 s;
  route A drops Kontrol setUp/booster overhead but adds hand-assembled dispatch → 2× the top of the Kontrol band. Fixed, not moved.
  Deterministic squeeze-knob = `--max-iterations N` (per spike-D З-1′).

## П-1 — WETH9: harness + first Accept/Refute on bytecode
### step 0 — object freeze `[x]`  (repro/spike-a/p1/)
- `[x]` **Design decision recorded:** "WETH9 already in hand" was FALSE (repo had only a spec + z2 `withdraw()`-без-арг).
  Authored faithful `WETH9.sol` = `deposit()` payable + `withdraw(uint256)` CEI. Chosen over z2 form because it matches
  П-1 shape AND the `t3-q1` `withdraw_F` class → honest П-2 same-class comparison. ([object-lock.md](repro/spike-a/p1/object-lock.md))
- `[x]` **runtime.bin frozen** 526 B, bit-exact. **sha256** `a4d50a96…8b89` · **keccak256** `0x0b89eb4d…6eb0`.
  Build: solc 0.8.35 · --optimize-runs 200 · --evm-version **shanghai** (PUSH0 `5f` ⇒ fork ≥ Shanghai).
- `[x]` **storage-layout** dumped (`layout: assumed-from-solc`, C2-stub): `balanceOf` slot 0, mapping(addr→u256).
- `[x]` **selectors:** withdraw=`2e1a7d4d` · deposit=`d0e30db0` · balanceOf=`70a08231`.
- `[x]` **toolchain.lock** written. DEVIATION recorded: z3 **4.12.6** (KEVM-bundled) vs CLAUDE.md 4.16.0.
- `[x]` **KEVM def decision (user):** build a FRESH WETH9 fork with `--emit-json` (closer to what the CLI harness-gen would do).

### step 2 — assemble claim config by SCRIPT (harness-generator prototype)  `[ ]`  ← NEXT, under stop-rule
Recipe (turnkey):
1. `[ ]` kompile fresh fork: `kompile <fork>/evm.md-based main` `--backend haskell --emit-json -I <fork> -I $KEVMSRC -I $PLUGIN`
   (idiom = `scripts/t3-build.sh`; KEVMSRC=`/nix/store/53c9hz1bs88a067spgbrbbs1j3nkjlvx-source/src/kevm_pyk/kproj/evm-semantics`,
   PLUGIN=`/nix/store/p06w45wanmvpw181g53c9lgdqd90azbj-source`). Decide: stock EVM vs t3-fork minus `<inFunc>` (functional prop → likely stock).
2. `[ ]` Python `gen_harness.py` emits `weth-withdraw-spec.k`: full `<ethereum>…<evm>…<callState>` tree —
   `<program> runtime.bin`, `<jumpDests>` computed, symbolic `<callData>` constrained head=`2e1a7d4d`+`#buf(32,WAD)`,
   `<callValue> 0`, `<caller>`/`<id>` set, `<gas>` high-cap, `<storage>` symbolic per layout
   (`balanceOf[caller] = keccak(pad(CALLER)++pad(0)) ↦ B`, wf `0≤B<2^256`), `<k> #execute`.
   **cell-completeness:** walk K-gotcha checklist, missing cells named explicitly (not by abstraction).
3. `[ ]` claim ensures: `<storage>` slot for `balanceOf[caller]` = `B -Int WAD` (decreases by exactly WAD) under `requires B >=Int WAD`. Explicit `[all-path]`.
4. `[ ]` run `kevm prove … --save-directory OUT --no-use-booster`. Record: verdict · wall-clock · kore-exec/SMT split · #SMT calls.

### step 3 — mandatory controls (без них зелёное не доказано) `[ ]`
- `[ ]` **Refute-control:** mutate bytecode (recompile WETH9 with debit-order defect / swapped const) → SAME harness must Refute + counterexample. Record CE.
- `[ ]` **Vacuity-control:** claim with unsatisfiable Pre → run must NOT give meaningful Accept. Record behavior. (cf. Finding 0005)
- `[ ]` **Attach-control:** wrong selector in constraint → claim must NOT pass past the code.

### stop-rule П-1  `[ ]`
- `[!]` If config does not assemble at all (kprove won't start `#execute` to dispatch) after **1 day** → STOP, report exact stuck point.
  This re-scores route A (raises priority D: refinement lemma). NOTE: spike-D flagged exactly this ("raw kprove can't auto-config a whole call").

## П-2 — bytecode vs model cost  `[ ]`  (baseline (i) = repro/t3-q1 model; (ii) = П-1 harness; 3× run (ii))
## П-3 — Morpho transfer  `[ ]`  (30-min pre-check: grep Morpho src for loops in mutating fns; pilot setAuthorization/createMarket)
## П-4 — hevm as U-refuter  `[ ]`  (parallel; mutated WETH9 from П-1 Refute-control)
## П-5 — hevm conformance search  `[ ]`  (parallel; argotorg/hevm CI vs ethereum/tests)

## Итоговые развилки — pending П-1..П-3 results.
