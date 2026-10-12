# SPIKE-T3 Q0 — `<inFunc>` implementation (precondition) · VERDICT

**Stand:** kontrol 1.0.255 · K v7.1.337 (kprove/kore-exec) · KEVM 1.0.678 · macOS arm64.
Fork = T1 fork (`<callCounter>` on `#mkCall`/`#mkCreate`) + `<inFunc>` stack-like monitor.

## Verdict (task format)

`реализовано (путь: #mkCall) · diff = 44 additive lines (~22 semantic K) · PROVED reentered@depth2 · JUMPDEST fallback NOT needed`

**Selector IS readable on exit before pop** — the discovery question is answered YES.
The three `#return.*` rules rewrite *to* `#popCallStack`, and `<callData>` is a child of the
not-yet-popped `<callState>` (evm.md `#popCallStack` restores the whole `<callState>`), so the
finishing frame's selector is in scope at the decrement. No `JUMPDEST` entry-instrumentation needed.

## Mechanism (K4)

- Cell `<inFunc> : Map(FuncSig4 -> active frames in C)`, sibling of `<callCounter>` (outside `<ethereum>`).
- `<monitoredAddr>` holds C; set by the claim — makes the `callee == C` guard general (no hard-coded address).
- **Increment** at `#mkCall` (evm.md:1678): `<inFunc> IF => #bump(IF, ACCTTO, MADDR, #selKey(ARGS), 1)`.
  `#bump` is identity when `ACCTTO =/= MADDR`, so the `callee==C` guard needs no `requires` on the stock rule.
  Key = `#selKey(ARGS) = #asWord(#range(ARGS,0,4))` — selector of the NEW frame's calldata.
- **Decrement** at the 3 exit junctions `#return.exception` / `#return.revert` / `#return.success`
  (evm.md:1826/1834/1844): `<inFunc> IF => #bump(IF, CID, MADDR, #selKey(CALLDATA), -1)`, reading
  `<id> CID` and `<callData> CALLDATA` of the finishing frame BEFORE `#popCallStack`.
  Revert exit decrements explicitly (unlike `<callCounter>`, which is cumulative and does not roll back):
  `<inFunc>` is stack-tied, so a reverted frame is no longer active and MUST be removed.
- `reentered(sig) := <inFunc>[sig] >=Int 2`.

## Evidence (repro/t3-q0)

| claim | what | result |
|---|---|---|
| `entry-base` | `#mkCall` into C, `<inFunc> .Map -> (SEL\|->1)` | **#Top** (increment, key from ARGS, guard callee==C) |
| `entry-reenter` | `#mkCall` into C, `<inFunc> (SEL\|->1) -> (SEL\|->2)` | **#Top** (reentered(SEL) fires at 2) |
| `exit-before-pop` | `#return.success`, `<inFunc> (SEL\|->2) -> (SEL\|->1)` | **#Top** (decrement reads SEL from `<callData>` pre-pop) |
| `neg-no-decrement` | asserts `<inFunc>` unchanged (2=>2) across exit | **FAILED** — real post `(SEL\|->1)` in log ⇒ decrement is real, not vacuous |
| `neg-foreign-guard` | `#mkCall` into 44≠C, asserts `.Map=>(SEL\|->1)` | **FAILED** — real post `.Map` ⇒ callee==C guard actually gates |

- Build: `scripts/t3-build.sh` → `logs/t3-q0-kompile.log` (exit=0).
- Proofs: `scripts/t3-q0-prove.sh` → `logs/t3-q0-infunc.log` (`#Top`).
- Negatives: `logs/t3-q0-negctl.log` (FAILED, discriminating).
- Diff: `diff repro/t1-q1/ii-mkcall/evm.md repro/t3-q0/evm.md` — fully additive; no stock LHS changed.

## Honest scope / caveats (Q4-journal candidates)

1. **Phantom-return over-count (out-of-spec for the mini-instance).** The pre-frame checks
   `#checkBalanceUnderflow`/`#checkDepthExceeded`/`#checkNonceExceeded` (evm.md:1587/1605/1615)
   do `#pushCallStack ~> #pushWorldState ~> #end` WITHOUT running `#mkCall`, then return via
   `#return.exception`. If C itself issues a sub-call that trips such a check while C's frame is
   active (`<id>==C` at that phantom return), the decrement over-fires. In the withdraw mini-instance
   these are excluded by Pre (`EC₀ >= A` ⇒ no balance underflow; depth 2 << 1024; CALL doesn't bump
   nonce), so `INV_inFunc` holds in-spec. A fully general fix = a per-frame "entered-C" marker set by
   `#mkCall` and consumed at `#return` (a 4th additive hook). Deferred; noted.
2. **`entry-reenter` is driven step-controlled** (a `#mkCall` from an already-active state), same
   methodology as T1 Q1b — not a full bytecode nested self-call (that is Q1/Q3-level: needs the
   withdraw bytecode + full CALL machinery + gas). It demonstrates the counter reaching 2 (reentered)
   at the instrumented junction, which is exactly the `INV_inFunc`/`reentered` claim Q1 relies on.
