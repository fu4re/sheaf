# Provenance — Aave Vault ground truth (T-05)

Vendored expert reference for Tier-2: the real `ATokenVault` + its **proven**
Certora CVL specs. Used by module [6] as ground truth for the spec-generation
realism measurement (ADR §5.4). NOT a compile target here (full transitive deps
for proving are deferred to T-14).

| Field | Value |
|---|---|
| Repo | https://github.com/aave/Aave-Vault |
| Commit | `5ab52d20b07f35a8f34e6702f2fea6797a5787eb` |
| Fetched | 2026-06-22 (HTTP 200, shallow clone) |
| License | All Rights Reserved © Aave Labs (see `LICENSE`) — vendored for research reference only |
| solc pragma | `^0.8.10` → compiles under our pinned 0.8.35 (confirms T-02) |

## Vendored
- `src/ATokenVault.sol` (656 lines) — the SUT; `deposit`/`_handleDeposit`/`previewDeposit`/
  `totalAssets`/`getClaimableFees`/`_accrueYield`.
- `src/ATokenVaultStorage.sol` — storage struct (`fee`, `accumulatedFees`, `lastVaultBalance`).
- `certora_specs/*.spec` — the proven CVL specs (the expert ground truth).

## The expert economic invariants (Certora, all proven)
Signal/noise as predicted by insights: each economic law is ~1 line; the proof
harness around it (ghost `rayMul`/`rayDiv`/`mulDiv` + axioms, `requireInvariant`
chains, `<= maxUint128()` overflow обвязка, forall arithmetic lemmas) is the bulk.

| CVL property | One-line law | File |
|---|---|---|
| `inv_sumAllBalance_eq_totalSupply` | `sumAllBalance() == totalSupply()` | totalSupply_EQ_sumAllBal |
| `inv_balanceOf_leq_totalSupply` | `balanceOf(u) <= totalSupply()` | totalSupply_EQ_sumAllBal |
| `positiveSupply_imply_positiveAssets` | `totalSupply()!=0 => totalAssets()!=0` | positiveSupply_imply_positiveAssets |
| `fees_LEQ_ATokenBal` | `claimableFees <= ATOKEN.balanceOf(vault)` | fees_LEQ_ATokenBal |
| `lastVaultBalance_OK` | `getLastVaultBalance() <= ATOKEN.balanceOf(vault)` | lastVaultBal_LEQ_ATokenBalThis |
| `accrueYieldCheck` | `accumulatedFees` monotonically non-decreasing | accrueYieldCheck |
| `changeInContractBalanceShouldCauseAccrual` | balance change ⇒ accrual | changeInContractBalance… |

Plus `erc4626.spec` — functional/rounding properties (previewDeposit bounds,
no-threshold, must-not-revert) — functional, not economic.

The ghost arithmetic axioms (in `rayMul_rayDiv_mulDiv_properties.spec` and inlined
in the specs above) are the first exhibit of our reusable harness library — and
the Certora axiom `y<=denominator => mulDiv(x,y,denom)<=x` matches the frozen
axiom we derived independently in Slice 2 (`trusted/harness/ghost.md`).
