import AaveArith.Basic

/-! # Canonical axiom audit (Task 0014, blocker Б2) — the kernel-checked trusted-base gate.

A `lake build` pass is NOT a proof: a `sorry` term also builds. Every theorem discharged in
`../../axiom_registry.json` must here `#print axioms` to ONLY `[propext, Classical.choice,
Quot.sound]` with **no** `sorryAx`. `tcg package` and `verify_package --replay` build this
module and parse these `depends on axioms` lines to gate a Lean leaf as `proven` — a build
rc of 0 is necessary but NOT sufficient. The judge is the kernel, not the return code. -/

open AaveArith Erc20

-- mulDiv round-down family
#print axioms mulDiv_mul_le
#print axioms mulDiv_le_left
#print axioms mulDiv_eq_zero
-- mulDiv tightness + ray bounds (promoted from NeuralProbe, Finding 0008 / Task 0014 Step 0)
#print axioms mulDiv_tightness
#print axioms rayMul_lower
#print axioms rayMul_upper
#print axioms rayDiv_upper
#print axioms rayDiv_lower
-- product / Σ conservation
#print axioms ar_delta
#print axioms transfer_pair_sum_preserved
#print axioms transfer_sum_preserved

-- Contrast: a `sorry` proof builds (warning only) but the audit MUST expose sorryAx.
theorem audit_sorry_demo (x y d : ℕ) : x ≤ mulDiv x y d := by sorry
#print axioms audit_sorry_demo
