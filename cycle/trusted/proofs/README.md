# Discharged ghost-arithmetic axioms (Task 0002, Goal C)

Machine-checked proofs that turn Aave's **assumed** Certora ghost axioms into
**theorems** — shrinking the trusted base (bridge level 1, see
[`axiom_registry.json`](axiom_registry.json)).

- **Prover:** Lean 4.31.0 + Mathlib v4.31.0 (chosen over Isabelle for momentum +
  EF/EVM-in-Lean ecosystem; D1 fork resolved).
- **Project:** [`aave_arith/`](aave_arith/) — proofs in [`aave_arith/AaveArith/Basic.lean`](aave_arith/AaveArith/Basic.lean).

## What's proven (all kernel-verified, `#print axioms` = only `propext`/`Quot.sound`)

| Lean theorem | Statement (ℕ) | CVL axiom it discharges |
|---|---|---|
| `mulDiv_mul_le` | `mulDiv x y d * d ≤ x*y` | `mulDiv4_g(x,y,denom)*denom <= x*y` |
| `mulDiv_le_left` | `y ≤ d → mulDiv x y d ≤ x` | `y<=denom => mulDiv4_g(x,y,denom)<=x` |
| `mulDiv_eq_zero` | `(x=0 ∨ y=0) → mulDiv x y d = 0` | `(x==0\|\|y==0) => mulDiv4_g==0` |

`mulDiv_le_left` is **exactly** the frozen axiom our Slice-2 ghost harness
(`trusted/harness/ProportionalVaultGhost.sol`) assumed on faith — now a theorem.

**Honest caveat:** proven over ℕ floor division, not 256-bit words. Transfers to
uint256 only under the non-overflow guard (`x*y < 2^256`) — the gap and next steps
are recorded in `axiom_registry.json`.

## Reproduce / verify

```bash
export PATH="$HOME/.elan/bin:$PATH"
cd aave_arith
lake exe cache get      # prebuilt Mathlib oleans (~5.7GB, not committed)
lake build              # kernel-checks the theorems (exit 0 = verified)
```
