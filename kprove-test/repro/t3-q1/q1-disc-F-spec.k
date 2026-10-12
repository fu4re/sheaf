requires "withdraw.k"

// Robust discriminators #6 / #8 for the FIXED variant F.  Both MUST PASS (T2 §6.2).
// F's debit is committed BEFORE the suspension (grounded: no pending bal-write — see q1-ground-spec), so
// Rely_w^F over bal[U] = ⊤.  The one thing F still relies on is that the environment does not reduce our
// NATIVE balance balances[U] under us — which holds because env can move native ETH only via a standard
// CALL to us (T2 §3.3 / §5.2 row C).  Non-vacuity: the antecedent STILL contains the reentrant bal[U]
// decrement (APRIME ≥ 1) exactly as in V; F passes anyway because its Rely does not constrain bal[U].
module Q1-DISC-F-SPEC
  imports WITHDRAW

  // #6 self-compat-withdraw (F):  Guar_w^F ⟹ Rely_w^F
  claim [c6-self-compat-withdraw-F]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE -Int APRIME       // Guar_w^F: reentrant frame STILL decrements bal[U] (same as V)
     andBool APRIME >=Int 1
     andBool ETHU_POST >=Int ETHU_PRE             // Guar_w^F: env only ADDS to our native balance (via calls to us)
    ensures  ETHU_POST >=Int ETHU_PRE             // Rely_w^F: native balances[U] not reduced under us  (bal[U] unconstrained)

  // #8 env-compat-withdraw (F):  Guar_env ⟹ Rely_w^F
  claim [c8-env-compat-withdraw-F]:
    <k> #check => #done </k>
    requires B_POST ==Int B_PRE -Int APRIME       // Guar_env: env reentered withdraw_F -> bal[U] decrement
     andBool APRIME >=Int 1
     andBool ETHU_POST >=Int ETHU_PRE             // Guar_env row C: env cannot drain our native balance under us
    ensures  ETHU_POST >=Int ETHU_PRE             // Rely_w^F -> holds
endmodule
