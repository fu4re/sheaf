requires "withdraw.k"

// SPIKE-D З-3 — junction as an IMPLICATION inside a PARENT spec (composition), not a trusted lemma.
//
// Composition contract:  Pre₁ --op₁--> Post₁ ; Post₁ ⟹ Pre₂ (JUNCTION) ; Pre₂ --op₂--> Post₂.
// The junction Post₁ ⟹ Pre₂ is discharged INSIDE the parent proof: op₂'s precondition (reqGE's pass-branch)
// must be entailed by the path condition carried out of op₁.  There is NO `[trusted]` / `[circularity]`
// attribute and NO separately-assumed claim imported — kprove itself discharges the implication in-context.
//
//   op₁ = deposit()      : bal[U] += A , balances[C] += A , balances[U] -= A     (Post₁: bal[U] = B0 + A)
//   op₂ = withdraw_F body: reqGE(bal[U] >= A) ; debit(bal[U] -= A) ; xfer         (Pre₂ : bal[U] >= A)
//   junction: (bal[U] = B0 + A) ⟹ (bal[U] >= A)   holds  ⟺  B0 >= 0.
module Z3-JUNCTION-SPEC
  imports WITHDRAW

  // (1) PARENT composition, junction discharged inline.  Net effect of deposit;withdraw_F is identity
  //     (deposit +A then debit -A on bal[U]; deposit +A then xfer -A on balances[C]), so every cell is
  //     net-unchanged and the whole sequence rewrites to #done — PROVIDED the junction B0>=0 lets reqGE pass.
  claim [z3-compose-ok]:
    <k> deposit ~> reqGE ~> debit ~> xfer ~> #done => #done </k>
    <balU>   B0 </balU>
    <ethC>   EC </ethC>
    <ethU>   EU </ethU>
    <amt>    A  </amt>
    <sumOth> S  </sumOth>
    requires B0 >=Int 0 andBool A >=Int 0

  // (2) The JUNCTION itself, written as an explicit implication (the recordable "form of junction in spec"):
  //     antecedent = Post₁ (requires), consequent = Pre₂ (ensures).  Post_deposit ⟹ Pre_withdraw.
  claim [z3-junction-implication-ok]:
    <k> #check => #done </k>
    requires BAL ==Int B0 +Int A andBool B0 >=Int 0     // Post₁ : bal[U] = B0 + A , and the enabling B0>=0
    ensures  BAL >=Int A                                 // Pre₂  : bal[U] >= A            -> HOLDS

  // (3) NON-VACUITY of the junction: drop the enabling premise B0>=0 and the SAME implication must FAIL
  //     (kprove returns a counterexample B0 < 0).  Proves the junction is genuinely discharged, not assumed.
  claim [z3-junction-implication-broken]:
    <k> #check => #done </k>
    requires BAL ==Int B0 +Int A                        // Post₁ without B0>=0
    ensures  BAL >=Int A                                 // Pre₂  -> FAILS (B0 may be < 0)

  // (4) In-PARENT junction failure: compose deposit ; withdraw_F ; withdraw_F.  The SECOND withdraw's junction
  //     (Post of withdraw#1 = bal[U]=B0 ⟹ Pre of withdraw#2 = bal[U]>=A) does NOT hold in general (B0 may be
  //     < A), so the parent cannot reach #done — the composition FAILS exactly at the un-dischargeable junction.
  claim [z3-compose-double-withdraw]:
    <k> deposit ~> reqGE ~> debit ~> reqGE ~> debit ~> xfer ~> #done => #done </k>
    <balU>   B0 </balU>
    <ethC>   EC </ethC>
    <ethU>   EU </ethU>
    <amt>    A  </amt>
    <sumOth> S  </sumOth>
    requires B0 >=Int 0 andBool A >=Int 1
endmodule
