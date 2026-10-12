# Vat 0.6.12 → 0.8 port — equivalence audit

The SUT for this cycle is a port of MakerDAO DSS `Vat` (self-contained CDP core)
from `^0.6.12` to `^0.8`. Because a broken port would make the agent-vs-expert
comparison incomplete or wrong, equivalence is verified two independent ways.

## 1. Surgical diff (only version-forced, individually-equivalent changes)

`diff legacy/Vat_0_6.sol src/Vat.sol` (code lines) shows EXACTLY four change classes;
all CDP logic (frob/fork/grab/heal/suck/fold/move/flux/slip) is byte-identical:

| Change | Why forced by 0.8 | Why semantics-preserving |
|---|---|---|
| `pragma ^0.6.12` → `^0.8` | new compiler | — |
| `constructor() public` → `constructor()` | 0.8 forbids ctor visibility | no behavioural effect |
| `_add/_sub/_mul` bodies wrapped in `unchecked { }` | 0.8 auto-reverts on overflow BEFORE the explicit checks | `unchecked` restores the 0.6 wrap-then-`require` semantics exactly; the explicit overflow `require`s are preserved verbatim |
| `either/both`: `assembly{or/and}` → `\|\|`/`&&` | 0.8 assembly bool handling | kept as FUNCTIONS, so call-site args stay eagerly evaluated (no new short-circuit); `\|\|`/`&&` on two already-evaluated bools == `or`/`and` |

## 2. Differential fuzz (legacy 0.6.12 bytecode vs 0.8 port)

`test/VatDiff.t.sol`: the SAME fuzzed call sequence is applied to BOTH the legacy
(deployed from bytecode precompiled by its own solc 0.6.12, optimizer off = dss's
`DAPP_BUILD_OPTIMIZE=0`) and the 0.8 port. After EVERY call it asserts:
- **revert parity** — both revert or both succeed (low-level `call`, compare success);
- **full state parity** — `debt/vice/Line/live` + every `ilks/urns/gem/dai/sin` over
  the {GOLD,SILVER}×{3 addrs} keyspace are identical.

Ops covered: `init, file(Line), file(ilk), slip, frob, fold, move, grab, suck`.

**Result: `[PASS] testFuzz_equivalence (runs: 300)` — 300 × 16 = 4800 fuzzed ops, ZERO
divergence.** Port is behaviourally equivalent to the original.

```bash
cd cycle/ground_truth/dss_vat && forge test -vvv   # reproduces the 300-run pass
```

## Note on the toolchain detour
`forge`'s own 0.6.12 sub-compile spuriously hit "stack too deep" on `frob` (the same
file compiles cleanly when 0.6.12 solc is invoked directly). So the legacy is
precompiled to `test/vat_0_6.bin` and deployed via raw `create`. The 0.8 port is
compiled by forge with the optimizer (needed for `frob`'s locals at 0.8.20).
Optimizer settings differ between the two sides but optimization preserves semantics,
so the equivalence conclusion is unaffected.
