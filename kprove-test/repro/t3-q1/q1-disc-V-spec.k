requires "withdraw.k"

// Robust discriminators #6 / #8 for the VULNERABLE variant V.  Both MUST FAIL (T2 §6.2, K1).
// Encoding = the R/G reduction of T2 §4.1: self-compat / env-compat = `Guar ⟹ Rely` as a relation on
// transitions.  A transition is ⟨pre, post⟩ over the suspension interval; free Ints B_PRE/B_POST/APRIME are
// universally quantified.  Rely_w^V pins bal[U] = B0 (grounded: a debit is pending after suspension — see
// q1-ground-spec).  A reentrant frame allowed by Guar decrements bal[U] by APRIME ≥ 1.  So Guar admits a
// transition Rely forbids ⇒ the implication is FALSE ⇒ kprove refutes with a concrete counterexample.
module Q1-DISC-V-SPEC
  imports WITHDRAW

  // #6 self-compat-withdraw (V):  Guar_w^V ⟹ Rely_w^V
  claim [c6-self-compat-withdraw-V]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE -Int APRIME       // Guar_w^V: a completed reentrant withdraw_V debited bal[U]
     andBool APRIME >=Int 1                        //          by APRIME ≥ 1 (its own V4)
     andBool B_PRE  >=Int APRIME
    ensures  B_POST ==Int B_PRE                    // Rely_w^V @ V2: bal[U] must stay = B0  -> VIOLATED

  // #8 env-compat-withdraw (V):  Guar_env ⟹ Rely_w^V
  // Guar_env may invoke ANY public entry point of C (T2 §5.2 row 1/3), incl. withdraw_V while withdraw_V is
  // active (no nonReentrant).  So Guar_env ⊇ the same bal[U]-decrement transition as #6 ⇒ same refutation.
  claim [c8-env-compat-withdraw-V]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE -Int APRIME       // Guar_env: env reentered withdraw_V, which debited bal[U]
     andBool APRIME >=Int 1
     andBool B_PRE  >=Int APRIME
    ensures  B_POST ==Int B_PRE                    // Rely_w^V -> VIOLATED
endmodule
