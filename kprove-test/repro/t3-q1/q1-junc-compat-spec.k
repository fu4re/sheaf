requires "withdraw.k"

// #4,#5,#7 compat (implication, same for V and F) + #9,#10 junction (consequence).  Pure R/G implications
// discharged as one-step subsumption claims (T1-Q4 mechanic): body #check=>#done, content in requires (Guar)
// / ensures (Rely or INV).  All expected PASS for both variants.
module Q1-JUNC-COMPAT-SPEC
  imports WITHDRAW

  // #4 compat-with→dep: Guar_w ⟹ Rely_d.  Rely_d = tx-boundary well-formedness (deposit has NO internal
  //    suspension point).  Guar_w keeps bal[U] well-formed (debit underflow-checked, so 0 ≤ bal < pow256).
  claim [c4-compat-with-dep]:
    <k> #check => #done </k>
    requires B_POST >=Int 0 andBool B_POST <Int (2 ^Int 256)     // Guar_w: writes keep bal well-formed
    ensures  B_POST >=Int 0 andBool B_POST <Int (2 ^Int 256)     // Rely_d: well-formed

  // #5 self-compat-deposit: Guar_d ⟹ Rely_d.  deposit has NO suspension point -> Rely_d @ suspension is empty
  //    (vacuously ⊤); only tx-boundary well-formedness remains, preserved by Guar_d.  Trivial PASS by structure.
  claim [c5-self-compat-deposit]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE +Int V                          // Guar_d: bal[U] += V
     andBool V >=Int 0 andBool B_PRE >=Int 0
     andBool B_POST <Int (2 ^Int 256)
    ensures  B_POST >=Int 0 andBool B_POST <Int (2 ^Int 256)    // Rely_d well-formed

  // #7 env-compat-deposit: Guar_env ⟹ Rely_d.  Guar_env explicitly preserves 0 ≤ bal < pow256 (T2 §5.2).
  claim [c7-env-compat-deposit]:
    <k> #check => #done </k>
    requires B_POST >=Int 0 andBool B_POST <Int (2 ^Int 256)    // Guar_env preserves ledger well-formedness
    ensures  B_POST >=Int 0 andBool B_POST <Int (2 ^Int 256)    // Rely_d

  // #9 Post_d ⟹ INV (junction, consequence): deposit does bal[U] += V and balances[C] += V equally
  //    -> solvency INV (balances[C] ≥ bal[U] + Σ_oth) preserved.
  claim [c9-postd-inv]:
    <k> #check => #done </k>
    requires EC_PRE  >=Int B_PRE +Int SO                        // INV before
     andBool EC_POST ==Int EC_PRE +Int V                        // Post_d: balances[C] += V
     andBool B_POST  ==Int B_PRE +Int V                         // Post_d: bal[U]      += V
    ensures  EC_POST >=Int B_POST +Int SO                       // INV after

  // #10 Post_w ⟹ INV (junction, consequence), LOCAL frame: withdraw does bal[U] -= A and balances[C] -= A
  //    equally -> LOCAL solvency INV preserved (holds for BOTH V and F).  The GLOBAL break for V is NOT local:
  //    it arises via reentrancy through the compat chain (#6/#8) and surfaces only at #11 (root).
  claim [c10-postw-inv-local]:
    <k> #check => #done </k>
    requires EC_PRE  >=Int B_PRE +Int SO
     andBool EC_POST ==Int EC_PRE -Int A
     andBool B_POST  ==Int B_PRE -Int A
    ensures  EC_POST >=Int B_POST +Int SO
endmodule
