// SPIKE-T3 Q3(b) — mechanical Guar_env admissibility checker (DECOMPOSED form, K3).
//
// Each step of the concrete DAO attack trace (Q3a) is one of:
//   callIntoC : the attacker calls a PUBLIC entry point of C (deposit / withdraw_V).  In the decomposed form
//               (TCG-006 K3) this is NOT an env-step — it is a loop-claim / entry-claim instantiation, and is
//               admissible by construction (Guar_env §5.2 rows 1,3: env may call any public entry, incl. an
//               unprotected reentry).
//   envCode   : the attacker's OWN code between calls (its receive()).  Admissible under the DECOMPOSED env-step
//               iff it does NONE of the Guar_env "cannot" things (T2 §5.2 rows A,B,C,E,F): it must not directly
//               write C's storage, forge msg.sender, drain C's native balance except via a CALL to C, write the
//               block context, or write <inFunc> directly.  These are LOCAL, checkable properties of the step —
//               NOT the temporal "provenance" clause (K3), which the decomposition avoids needing.
//
// Verdict:
//   allAdmissible(trace) => true   ==> every attack step is admitted by Guar_env on this corpus
//                                       (lower bound of adequacy: the enemy model is NOT narrower than reality).
//   any step => false              ==> Guar_env is narrower than reality (STOP-RULE 2, unsoundness class).

module GUARENV
  imports INT
  imports BOOL

  syntax Kind ::= "callIntoC" | "envCode"

  // step(kind, writesStorageC, forgesSender, drainsNativeDirect, writesBlockCtx, writesInFuncDirect)
  syntax Step  ::= step(Kind, Bool, Bool, Bool, Bool, Bool)
  syntax Steps ::= ".Steps" | Step ";" Steps

  syntax Bool ::= admissible(Step) [function, total]
  // A call into C's public entry is admissible (rows 1/3) — a C-claim instantiation, not an env-step.
  rule admissible(step(callIntoC, _, _, _, _, _)) => true
  // An env-code segment is admissible iff it violates none of the Guar_env "cannot" rows (A,B,C,E,F).
  rule admissible(step(envCode, WSC, FS, DND, WBC, WIF)) =>
         notBool WSC andBool notBool FS andBool notBool DND andBool notBool WBC andBool notBool WIF

  syntax Bool ::= allAdmissible(Steps) [function, total]
  rule allAdmissible(.Steps)   => true
  rule allAdmissible(S ; REST) => admissible(S) andBool allAdmissible(REST)

  // carrier for the reachability claims
  syntax KItem ::= "#run"
  configuration <T> <k> $PGM:K </k> </T>
endmodule
