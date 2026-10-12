import AaveArith.NeuralProbe

/-! Axiom audit (Task 0013): a build pass is NOT enough — a `sorry` proof also builds.
    `#print axioms` must show ONLY [propext, Classical.choice, Quot.sound] and NO `sorryAx`
    for every theorem, or the discharge is vacuous. The judge is the kernel, not the build rc. -/

open NeuralProbe
open AaveArith  -- `mulDiv` (used bare in sorry_demo below) lives in namespace AaveArith

-- Tier B (reproduction)
#print axioms mulDiv_le_left'
#print axioms ar_delta'
#print axioms transfer_sum_preserved'
-- Tier C (new discharge)
#print axioms mulDiv_tightness
#print axioms rayMul_lower
#print axioms rayMul_upper
#print axioms rayDiv_upper
#print axioms rayDiv_lower

-- Contrast: a `sorry` proof builds but the audit MUST expose sorryAx.
theorem sorry_demo (x y d : ℕ) : x ≤ mulDiv x y d := by sorry
#print axioms sorry_demo
