requires "withdraw.k"

// #3 compat-dep→with: Guar_d ⟹ Rely_w on the footprint intersection {bal[U], balances[C]}.
// Attack window: env calls deposit(U) DURING our withdraw's suspension -> bal[U] INCREASES by V ≥ 1 (Guar_d).
// K1 directive: run BOTH editions of Rely_w^V.  #3 is the SECONDARY discriminator (edition-dependent);
// the robust ones are #6/#8.
module Q1-C3-SPEC
  imports WITHDRAW

  // V, STRICT Rely_w^V (bal[U] = B0 frozen): env-deposit raising bal[U] breaks equality -> FAIL.
  claim [c3-V-strict]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE +Int V andBool V >=Int 1 andBool B_PRE >=Int 0   // Guar_d
    ensures  B_POST ==Int B_PRE                                                   // Rely_w^V strict -> VIOLATED

  // V, WEAKENED Rely_w^V (bal[U] ≥ B0, "no DECREASE on the suspension interval"): deposit only raises -> PASS.
  claim [c3-V-weak]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE +Int V andBool V >=Int 1 andBool B_PRE >=Int 0   // Guar_d
    ensures  B_POST >=Int B_PRE                                                   // Rely_w^V weakened -> holds

  // F (Rely_w^F over bal[U] = ⊤): PASS under either edition.
  claim [c3-F]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE +Int V andBool V >=Int 1 andBool B_PRE >=Int 0   // Guar_d
    ensures  B_POST >=Int B_PRE                                                   // Rely_w^F does not constrain bal[U]
endmodule
