# П-1 object lock — WETH9 fragment (frozen before first prove run)

## Design decision (recorded, honesty discipline)
Task says "WETH9-фрагмент (уже в наличии)". **It was not present** — repo had only
`evm-smith/weth_spec.md` (a spec) and `repro/spike-d-z2/gen/C_*.sol` (a `withdraw()`
**without argument**, property `balance==0`). That object does NOT match П-1's required
shape `withdraw(uint)` / property "balance decreases by exactly amt".

**Decision:** author a faithful minimal WETH9 fragment — `deposit()` payable +
`withdraw(uint256 wad)` with checks-effects-interactions (`require ≥ ; debit ; call`).
Rationale: (1) matches П-1 shape and property class; (2) it is exactly the `withdraw_F`
class of the `repro/t3-q1` abstract model → the П-2 "same property class on two carriers"
comparison stays honest, not apples-to-oranges.

Source: [WETH9.sol](WETH9.sol).

## Frozen artifacts
| item | value |
|---|---|
| runtime.bin | [runtime.bin](runtime.bin) — 526 bytes, hex, bit-exact (no 0x, no newline) |
| **sha256(runtime.bin)** | `a4d50a9613c404ad5670216a90a2ccbe02220d84c819f34c9b83b3dd04598b89` |
| **keccak256(runtime)** | `0x0b89eb4d477e7f16933b1c32c3f2aeee6f94d32d99af47edc29789855f4c6eb0` |
| build | solc 0.8.35 · --optimize --optimize-runs 200 · --evm-version shanghai |
| storage layout | [storage-layout.json](storage-layout.json) — `layout: assumed-from-solc` (C2-stub) |

## Selectors (constrain `<callData>` head in harness)
| function | selector |
|---|---|
| `withdraw(uint256)` | `2e1a7d4d` |
| `deposit()`         | `d0e30db0` |
| `balanceOf(address)`| `70a08231` |

## Storage layout (for symbolic `<storage>` cell — assumed-from-solc)
- `balanceOf` at **slot 0**, `mapping(address => uint256)`.
- `balanceOf[a] = storage[ keccak256(abi.encode(a, uint256(0))) ]`.
- Harness: `balanceOf[msg.sender]` = symbolic B with wf-constraint `0 ≤ B < 2^256`;
  key = `keccak256(pad32(CALLER) ++ pad32(0))`.

## Claim (П-1 step 3) — property class
After `withdraw(wad)` from state where `balanceOf[caller] = B ≥ wad`:
`balanceOf[caller]' == B - wad` (decreases by exactly wad) AND `wad` wei leaves to caller.
Explicit `[all-path]`. Same class proved on the `t3-q1` model in mini-instances.

## Toolchain
See [toolchain.lock](toolchain.lock). Stand matches task (KEVM 1.0.678 / K 7.1.337 / solc 0.8.35);
**deviation:** z3 4.12.6 (KEVM-bundled) vs CLAUDE.md canonical 4.16.0 — recorded.
