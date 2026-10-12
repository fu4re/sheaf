requires "guarenv.k"

// Feed the concrete DAO attack trace (Q3a) through the decomposed Guar_env admissibility checker.
module GUARENV-CHECK-SPEC
  imports GUARENV

  // The real trace: attacker -> C.deposit ; attacker -> C.withdraw_V(outer) ; receive()outer(env) ;
  //                 attacker -> C.withdraw_V(inner reentry) ; receive()inner(env).
  // Every callIntoC is a public-entry / reentry (rows 1,3).  Every envCode segment touches NONE of the
  // Guar_env "cannot" rows (attacker's receive only READS bank.balance and issues a CALL — no direct SSTORE
  // into C, no forged sender, no direct native drain, no block-ctx write, no direct <inFunc> write).
  claim [dao-trace-all-admissible]:
    <k> allAdmissible( step(callIntoC, false, false, false, false, false)    // E1  attacker -> C.deposit
                     ; step(callIntoC, false, false, false, false, false)    // E2  attacker -> C.withdraw_V (outer)
                     ; step(envCode,   false, false, false, false, false)    // E3  receive() outer: read bal, reenter
                     ; step(callIntoC, false, false, false, false, false)    // E4  attacker -> C.withdraw_V (reentry)
                     ; step(envCode,   false, false, false, false, false)    // E5  receive() inner: read bal, stop
                     ; .Steps ) => true </k>

  // STOP-RULE-2 discriminator: had ANY step required env to do a forbidden thing (here: a direct SSTORE into C's
  // storage, WSC=true), the checker returns false — that would be "a step is inadmissible by Guar_env" (unsound).
  // Real EVM never emits such a step, so the real trace above stays all-admissible.  This proves the checker
  // actually DISCRIMINATES (it is not a vacuous `=> true`).
  claim [fabricated-inadmissible-caught]:
    <k> allAdmissible( step(callIntoC, false, false, false, false, false)
                     ; step(envCode,  true,  false, false, false, false)     // env SSTOREs into C directly -> forbidden
                     ; .Steps ) => false </k>
endmodule
