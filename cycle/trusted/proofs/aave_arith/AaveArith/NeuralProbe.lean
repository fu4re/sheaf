import Mathlib
import AaveArith.Basic

/-!
# Neural-prover probe (Task 0013) — kernel-checked discharge on OUR domain.

Each theorem below is a candidate proof emitted by a NEURAL MODEL (here: Claude,
acting as the untrusted generator) and ADMITTED ONLY BY THE LEAN KERNEL via
`lake build` against the pinned toolchain (Lean 4.31.0 + Mathlib v4.31.0). A wrong
term is rejected by the kernel — zero added trust, exactly the ADR-0003 trust model
(untrusted generator + trusted checker), applied recursively to ghost-axiom discharge.

Tiers:
  B  REPRODUCTION of already-discharged anchors (L1 mulDiv_le_left, L2 ar_delta,
     L3 transfer_sum_preserved over a Finset) — fresh proofs, judged by the kernel.
  C  NEW DISCHARGE of OPEN-frontier axioms (axiom_registry.json `not_yet_discharged`):
     mulDiv tightness, rayMul bounds, rayDiv bounds. A success here is a genuine new
     theorem narrowing the trusted base.
-/

namespace NeuralProbe
open AaveArith

-- =====================================================================================
-- Tier B — reproduction across difficulty tiers (the kernel is the judge)
-- =====================================================================================

/-- L1 (easy, Mathlib-shaped): `y ≤ d → mulDiv x y d ≤ x`. Fresh proof. -/
theorem mulDiv_le_left' (x y d : ℕ) (h : y ≤ d) : mulDiv x y d ≤ x := by
  unfold mulDiv
  rcases Nat.eq_zero_or_pos d with hd | hd
  · simp [hd]
  · calc x * y / d ≤ x * d / d := by gcongr
      _ = x := Nat.mul_div_left x hd

/-- L2 (trivial): the product-delta distributivity, by `ring`. -/
theorem ar_delta' (Art dart rate : ℤ) :
    (Art + dart) * rate = Art * rate + dart * rate := by ring

/-- L3 (hard, project-specific): Σ over a Finset preserved under a double
    `Function.update` (debit `src`, credit `dst` by the same `amt`). The real stress
    test: definition-heavy, references our own statement, not a self-contained miniF2F
    string. Fresh attempt. -/
theorem transfer_sum_preserved' {α : Type*} [DecidableEq α] (s : Finset α) (f : α → ℕ)
    (src dst : α) (amt : ℕ) (hne : src ≠ dst) (hsrc : src ∈ s) (hdst : dst ∈ s)
    (h : amt ≤ f src) :
    (∑ x ∈ s, Function.update (Function.update f src (f src - amt)) dst (f dst + amt) x)
      = ∑ x ∈ s, f x := by
  have hsrc' : src ∈ s.erase dst := Finset.mem_erase.mpr ⟨hne, hsrc⟩
  rw [Finset.sum_update_of_mem hdst, ← Finset.erase_eq,
      Finset.sum_update_of_mem hsrc', ← Finset.erase_eq,
      ← Finset.add_sum_erase _ f hdst, ← Finset.add_sum_erase _ f hsrc']
  omega

-- =====================================================================================
-- Tier C — NEW discharge of OPEN-frontier axioms (not_yet_discharged)
-- =====================================================================================

/-- **OPEN-FRONTIER #1 — mulDiv tightness / no-slack.** `0 < d → x*y < (mulDiv x y d + 1)*d`.
    Together with the discharged `mulDiv_mul_le` this brackets `mulDiv` exactly:
    `mulDiv x y d * d ≤ x*y < (mulDiv x y d + 1)*d`. -/
theorem mulDiv_tightness (x y d : ℕ) (hd : 0 < d) :
    x * y < (mulDiv x y d + 1) * d := by
  unfold mulDiv
  have h1 := Nat.div_add_mod (x * y) d          -- d * (x*y/d) + (x*y)%d = x*y
  have h2 := Nat.mod_lt (x * y) hd              -- (x*y)%d < d
  have hexp : (x * y / d + 1) * d = d * (x * y / d) + d := by ring
  omega

-- Aave fixed-point scale. Only `RAY > 0` is load-bearing for the bounds below.
def RAY : ℕ := 10 ^ 27

theorem RAY_pos : 0 < RAY := by unfold RAY; positivity

/-- `rayMul x index = ⌊x·index / RAY⌋` (Aave ray-multiplication, rounding down). -/
def rayMul (x index : ℕ) : ℕ := x * index / RAY

/-- **OPEN-FRONTIER #2a — rayMul lower bound.** `RAY ≤ index → x ≤ rayMul x index`. -/
theorem rayMul_lower (x index : ℕ) (h : RAY ≤ index) : x ≤ rayMul x index := by
  unfold rayMul
  calc x = x * RAY / RAY := (Nat.mul_div_left x RAY_pos).symm
    _ ≤ x * index / RAY := by gcongr

/-- **OPEN-FRONTIER #2b — rayMul upper bound.** `index ≤ 2*RAY → rayMul x index ≤ 2*x`. -/
theorem rayMul_upper (x index : ℕ) (h : index ≤ 2 * RAY) : rayMul x index ≤ 2 * x := by
  unfold rayMul
  calc x * index / RAY ≤ x * (2 * RAY) / RAY := by gcongr
    _ = 2 * x := by
        rw [show x * (2 * RAY) = (2 * x) * RAY by ring]
        exact Nat.mul_div_left (2 * x) RAY_pos

/-- `rayDiv x index = ⌊x·RAY / index⌋` (Aave ray-division, rounding down). -/
def rayDiv (x index : ℕ) : ℕ := x * RAY / index

/-- **OPEN-FRONTIER #3a — rayDiv upper bound.** `RAY ≤ index → rayDiv x index ≤ x`. -/
theorem rayDiv_upper (x index : ℕ) (h : RAY ≤ index) : rayDiv x index ≤ x := by
  unfold rayDiv
  calc x * RAY / index ≤ x * RAY / RAY := by
        apply Nat.div_le_div_left h RAY_pos
    _ = x := Nat.mul_div_left x RAY_pos

/-- **OPEN-FRONTIER #3b — rayDiv lower bound.**
    `0 < index → index ≤ 2*RAY → x/2 ≤ rayDiv x index`. -/
theorem rayDiv_lower (x index : ℕ) (h0 : 0 < index) (h : index ≤ 2 * RAY) :
    x / 2 ≤ rayDiv x index := by
  unfold rayDiv
  have hRAY : 0 < 2 * RAY := by have := RAY_pos; omega
  calc x / 2 = x * RAY / (2 * RAY) := by
        rw [Nat.mul_div_mul_right x 2 RAY_pos]
    _ ≤ x * RAY / index := by apply Nat.div_le_div_left h h0

end NeuralProbe
