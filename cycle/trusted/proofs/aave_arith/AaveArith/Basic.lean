import Mathlib

/-!
# Discharged ghost-arithmetic axioms (Task 0002, Goal C)

Aave's Certora specs ASSUME the `mulDiv` ghost axioms (unproven postulates, in
`fees_LEQ_ATokenBal.spec` / `positiveSupply_imply_positiveAssets.spec`):

    (mulDiv x y d) * d ≤ x * y                 -- round-down lower bound
    y ≤ d → (mulDiv x y d) ≤ x                 -- the bound our Slice-2 ghost assumes
    (x = 0 ∨ y = 0) → (mulDiv x y d) = 0       -- zero preservation

We model `mulDiv x y d = ⌊x·y / d⌋` as ℕ floor division and turn each AXIOM into a
machine-checked THEOREM, shrinking the trusted base to "the CVL statement = the
statement proven here" (bridge level 1, see ../axiom_registry.json).
-/

namespace AaveArith

/-- `mulDiv x y d` models Aave's `mulDiv(x, y, d)` rounding down = ⌊x·y / d⌋. -/
def mulDiv (x y d : ℕ) : ℕ := x * y / d

/-- **Axiom 1 — round-down lower bound.** `mulDiv(x,y,d) * d ≤ x*y`.
    Matches CVL `mulDiv4_g(x,y,denom)*denom <= x*y`. -/
theorem mulDiv_mul_le (x y d : ℕ) : mulDiv x y d * d ≤ x * y :=
  Nat.div_mul_le_self (x * y) d

/-- **Axiom 2 — the bound our ghost harness assumes.** `y ≤ d → mulDiv(x,y,d) ≤ x`.
    Matches CVL `y <= denominator => mulDiv4_g(x,y,denom) <= x`. This is exactly the
    frozen axiom `mintedShares <= assets` in `trusted/harness/ProportionalVaultGhost.sol`. -/
theorem mulDiv_le_left (x y d : ℕ) (h : y ≤ d) : mulDiv x y d ≤ x := by
  unfold mulDiv
  rcases Nat.eq_zero_or_pos d with hd | hd
  · simp [hd]
  · calc x * y / d ≤ x * d / d := by gcongr
      _ = x := Nat.mul_div_left x hd

/-- **Axiom 3 — zero preservation.** `(x = 0 ∨ y = 0) → mulDiv(x,y,d) = 0`.
    Matches CVL `(x==0 || y==0) => mulDiv4_g(x,y,denom)==0`. -/
theorem mulDiv_eq_zero (x y d : ℕ) (h : x = 0 ∨ y = 0) : mulDiv x y d = 0 := by
  unfold mulDiv
  rcases h with hx | hy <;> subst_vars <;> simp

/-- **Product-delta identity (distributivity).** Justifies the ghost shadow
    `ghostAR == Σ Art·rate` in `trusted/harness/VatSolvency.sol`: when `Art` changes
    by `dart`, the product `Art·rate` changes by exactly `dart·rate` (= Vat's `dtab`).
    Signed (`ℤ`) because `dart` is a signed delta. This is what makes the ghost
    faithful rather than assumed. -/
theorem ar_delta (Art dart rate : ℤ) : (Art + dart) * rate = Art * rate + dart * rate :=
  add_mul Art dart rate

/-! ### Open-frontier bounds (promoted from `NeuralProbe.lean`, Finding 0008)

Five kernel-checked theorems that were `not_yet_discharged` in `axiom_registry.json`.
Each was emitted by a neural generator and admitted only by the Lean kernel (F0008);
promoted here into the trusted base. `mulDiv_tightness` + `mulDiv_mul_le` give the exact
two-sided bracket `mulDiv x y d * d ≤ x*y < (mulDiv x y d + 1)*d`. The `rayMul`/`rayDiv`
bounds are exactly the fixed-point bounds Aave's Certora specs postulate — now theorems.
(ℕ floor model; the uint256 non-overflow side-condition mirrors the registry caveat.) -/

/-- **Open-frontier #1 — mulDiv tightness / no-slack.** `0 < d → x*y < (mulDiv x y d + 1)*d`. -/
theorem mulDiv_tightness (x y d : ℕ) (hd : 0 < d) :
    x * y < (mulDiv x y d + 1) * d := by
  unfold mulDiv
  have h1 := Nat.div_add_mod (x * y) d
  have h2 := Nat.mod_lt (x * y) hd
  have hexp : (x * y / d + 1) * d = d * (x * y / d) + d := by ring
  omega

/-- Aave fixed-point scale. Only `RAY > 0` is load-bearing for the bounds below. -/
def RAY : ℕ := 10 ^ 27

theorem RAY_pos : 0 < RAY := by unfold RAY; positivity

/-- `rayMul x index = ⌊x·index / RAY⌋` (Aave ray-multiplication, rounding down). -/
def rayMul (x index : ℕ) : ℕ := x * index / RAY

/-- **Open-frontier #2a — rayMul lower bound.** `RAY ≤ index → x ≤ rayMul x index`. -/
theorem rayMul_lower (x index : ℕ) (h : RAY ≤ index) : x ≤ rayMul x index := by
  unfold rayMul
  calc x = x * RAY / RAY := (Nat.mul_div_left x RAY_pos).symm
    _ ≤ x * index / RAY := by gcongr

/-- **Open-frontier #2b — rayMul upper bound.** `index ≤ 2*RAY → rayMul x index ≤ 2*x`. -/
theorem rayMul_upper (x index : ℕ) (h : index ≤ 2 * RAY) : rayMul x index ≤ 2 * x := by
  unfold rayMul
  calc x * index / RAY ≤ x * (2 * RAY) / RAY := by gcongr
    _ = 2 * x := by
        rw [show x * (2 * RAY) = (2 * x) * RAY by ring]
        exact Nat.mul_div_left (2 * x) RAY_pos

/-- `rayDiv x index = ⌊x·RAY / index⌋` (Aave ray-division, rounding down). -/
def rayDiv (x index : ℕ) : ℕ := x * RAY / index

/-- **Open-frontier #3a — rayDiv upper bound.** `RAY ≤ index → rayDiv x index ≤ x`. -/
theorem rayDiv_upper (x index : ℕ) (h : RAY ≤ index) : rayDiv x index ≤ x := by
  unfold rayDiv
  calc x * RAY / index ≤ x * RAY / RAY := by
        apply Nat.div_le_div_left h RAY_pos
    _ = x := Nat.mul_div_left x RAY_pos

/-- **Open-frontier #3b — rayDiv lower bound.** `0 < index → index ≤ 2*RAY → x/2 ≤ rayDiv x index`. -/
theorem rayDiv_lower (x index : ℕ) (h0 : 0 < index) (h : index ≤ 2 * RAY) :
    x / 2 ≤ rayDiv x index := by
  unfold rayDiv
  have hRAY : 0 < 2 * RAY := by have := RAY_pos; omega
  calc x / 2 = x * RAY / (2 * RAY) := by
        rw [Nat.mul_div_mul_right x 2 RAY_pos]
    _ ≤ x * RAY / index := by apply Nat.div_le_div_left h h0

end AaveArith

/-!
## Cross-contract callee guarantee (Task 0003) — ERC20 conservation

The cross-contract A/G cycle assumes a callee guarantee `G_B` for the ERC20: a transfer
moves balances by exactly `amount` and preserves `Σ balanceOf == totalSupply`. The
tracked-sum shadow `ghostSum` in `trusted/harness/cross/MiniERC20Conservation.sol` leaves
itself UNTOUCHED on transfer — sound only because the two affected balances' sum is
preserved. That faithfulness fact is the cross-contract analogue of `ar_delta`, and is
machine-checked here (over ℕ; the uint256 non-overflow caveat mirrors the registry's).
-/
namespace Erc20

/-- **Two-account conservation (the shadow's faithfulness fact).** Moving `amt` from `a`
    to `b` (with `amt ≤ a`) leaves the pair sum `a + b` unchanged — so a transfer that
    debits one balance and credits another by the same `amt` keeps `Σ balanceOf` fixed,
    which is exactly why `ghostSum` is untouched on transfer. The direct analogue of
    `AaveArith.ar_delta` for the cross-contract callee guarantee. -/
theorem transfer_pair_sum_preserved (a b amt : ℕ) (h : amt ≤ a) :
    (a - amt) + (b + amt) = a + b := by omega

/-- **Σ-conservation over a finite balance map.** For balances `f : α → ℕ` and accounts
    `frm ≠ to`, debiting `frm` by `amt` and crediting `to` by `amt` (with `amt ≤ f frm`)
    preserves `Σ` over any finite support `s`. The mapping-level statement the tracked-sum
    ghost over-approximates: `Σ balanceOf` (hence the `ghostSum` shadow == totalSupply) is
    invariant under transfer. -/
theorem transfer_sum_preserved {α : Type*} [DecidableEq α] (s : Finset α) (f : α → ℕ)
    (src dst : α) (amt : ℕ) (hne : src ≠ dst) (hsrc : src ∈ s) (hdst : dst ∈ s) (h : amt ≤ f src) :
    (∑ x ∈ s, Function.update (Function.update f src (f src - amt)) dst (f dst + amt) x)
      = ∑ x ∈ s, f x := by
  have hsrc' : src ∈ s.erase dst := Finset.mem_erase.mpr ⟨hne, hsrc⟩
  rw [Finset.sum_update_of_mem hdst, ← Finset.erase_eq,
      Finset.sum_update_of_mem hsrc', ← Finset.erase_eq,
      ← Finset.add_sum_erase _ f hdst, ← Finset.add_sum_erase _ f hsrc']
  omega

end Erc20
