requires "withdraw.k"

// Anti-vacuity counterfactual for the F discriminators.  F's transition (its antecedent) is IDENTICAL to V's
// on bal[U] — it STILL contains the reentrant decrement (B_POST = B_PRE - APRIME, APRIME ≥ 1).  Here we test
// that SAME F transition against V's STRICT Rely (bal[U] = B0).  It MUST FAIL.  That proves F's PASS on #6/#8
// is NOT because the antecedent is trivial/unsatisfiable — it is specifically because Rely_w^F does not
// constrain bal[U] (a fact EARNED by operation order: F has no pending bal-write at suspension, see grounding).
module Q1-VACUITY-SPEC
  imports WITHDRAW

  claim [c6-F-transition-under-V-rely]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE -Int APRIME    // F's OWN transition (reentrant bal[U] decrement present)
     andBool APRIME >=Int 1
     andBool B_PRE  >=Int APRIME
    ensures  B_POST ==Int B_PRE                 // V's STRICT Rely applied to F's transition -> MUST VIOLATE
endmodule
