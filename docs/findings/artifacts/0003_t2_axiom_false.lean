/-
Artifact for Finding 0003 — proof that evm-smith's axiom T2
`precompile_preserves_accountMap`, AS DECLARED (∀ arbitrary f), is a FALSE
proposition, hence the trusted base is inconsistent as written.

In practice the inconsistency is LATENT: the axiom is only ever applied to the
10 concrete precompiles Ξ_*, where the statement is genuinely true. No false
theorem is actually derived in the repo. But the AXIOMS.md claim "true by
inspection" does not hold for the *declared* (fully general) form.

HOW TO RUN (needs the evm-smith clone, NOT this repo):
  - repo: github.com/leonardoalt/evm-smith ; EVMYulLean submodule @ 56253eb
  - lean-toolchain leanprover/lean4:v4.22.0
  - place at evm-smith root and: lake env lean <thisfile>
  - elaborates with NO errors and NO `sorry` ⇒ `False` is derived.

Honest fix (PARKED — evm-smith is research, not prod, see Finding 0003):
replace the axiom with 10 per-precompile lemmas Ξ_*_preserves_accountMap
((Ξ_X σ g A I).2.1 = σ ∨ = ∅), rewire ~21 call sites in
EvmYul/Frame/MutualFrame.lean, delete the axiom. The 10 lemmas were verified to
prove via: unfold; repeat' first | exact Or.inl rfl | exact Or.inr rfl
                                  | split | simp only [dbgTrace]
-/
import EvmYul.Frame.MutualFrame
open EvmYul EvmYul.Frame

example : False := by
  let m : AccountMap .EVM := (∅ : AccountMap .EVM).insert default default
  have h := precompile_preserves_accountMap (∅ : AccountMap .EVM) ⟨0⟩ default default
              (fun _ _ _ _ => (true, m, (⟨0⟩ : UInt256), default, ByteArray.empty))
  simp only [or_self] at h
  have h1 : (m.find? default).isSome = true := by native_decide
  have h2 : (((∅ : AccountMap .EVM)).find? default).isSome = false := by native_decide
  rw [h] at h1
  exact Bool.noConfusion (h1.symm.trans h2)
