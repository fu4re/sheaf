// SPIKE-T3 Q1 — abstract model of the withdraw mini-instance (state-level, operation-order faithful).
//
// This models the DISCRIMINATING structure of the T2 mini-instance: the ORDER of the ledger write
// (debit bal[U]) relative to the external-call suspension point.  The R/G obligations that decide V vs F
// (#3,#6,#8) turn on this order (T2 §4.5), so an order-faithful abstract semantics is enough to EARN the
// V/F split — it is not baked in.  Full-bytecode closure on the fork is the same integration boundary as
// T1-Q2a (raw kprove can't auto-config a whole call); the concrete on-fork drain is Q3.
//
//   bal[U]      = ledger balance of the caller U in C      -> <balU>
//   Σ_{u≠U}bal  = other users' ledger (frame-disjoint)     -> <sumOth>
//   balances[C] = native ETH of the contract               -> <ethC>
//   balances[U] = native ETH of the caller                 -> <ethU>
//   A           = withdraw amount                           -> <amt>
//
//   deposit    = credit                       (bal[U] += A)
//   withdraw_V = reqGE ~> susp ~> debit        (check ; CALL/transfer=SUSPENSION ; debit AFTER)   <-- vulnerable
//   withdraw_F = reqGE ~> debit ~> susp        (check ; debit BEFORE ; CALL/transfer=SUSPENSION)  <-- fixed
//
// `susp` performs the ETH transfer (ethC-=A, ethU+=A) and halts at `#atSusp` (the suspension point), so the
// CONTINUATION left in <k> reveals whether a bal-write is still pending: V leaves `#atSusp ~> debit`
// (pending debit => Rely must pin bal[U]=B0), F leaves `#atSusp` (no pending write => Rely over bal[U] = T).

module WITHDRAW
  imports INT
  imports BOOL

  syntax KItem ::= "reqGE" | "debit" | "credit" | "susp" | "xfer" | "deposit"
                 | "#atSusp" | "#revert" | "#check" | "#done"

  configuration
    <T>
      <k>      $PGM:K       </k>
      <balU>   $BALU:Int    </balU>
      <sumOth> $SUMOTH:Int  </sumOth>
      <ethC>   $ETHC:Int    </ethC>
      <ethU>   $ETHU:Int    </ethU>
      <amt>    $AMT:Int     </amt>
    </T>

  // require(bal[U] >= amt) : pass or revert
  rule <k> reqGE => .K     ... </k> <balU> B </balU> <amt> A </amt> requires B >=Int A
  rule <k> reqGE => #revert ... </k> <balU> B </balU> <amt> A </amt> requires B  <Int A

  // bal[U] -= amt  (Solidity 0.8 underflow-check: revert if it would go negative)
  rule <k> debit => .K      ... </k> <balU> B => B -Int A </balU> <amt> A </amt> requires B >=Int A
  rule <k> debit => #revert ... </k> <balU> B </balU>            <amt> A </amt> requires B  <Int A

  // bal[U] += amt
  rule <k> credit => .K ... </k> <balU> B => B +Int A </balU> <amt> A </amt>

  // external CALL: transfer A native ETH out to U, then HALT at the suspension point (#atSusp has no rule).
  rule <k> susp => #atSusp ... </k>
       <ethC> C => C -Int A </ethC>
       <ethU> U => U +Int A </ethU>
       <amt>  A </amt>

  // same transfer viewed as COMPLETING (call returned ok) — used by frame/junction claims that run the
  // whole body; identical write-set to `susp`, but does not halt.
  rule <k> xfer => .K ... </k>
       <ethC> C => C -Int A </ethC>
       <ethU> U => U +Int A </ethU>
       <amt>  A </amt>

  // deposit(): depositor sends A native ETH (ethU -= A), gets ledger credit (bal[U] += A), contract native grows.
  rule <k> deposit => .K ... </k>
       <balU> B => B +Int A </balU>
       <ethC> C => C +Int A </ethC>
       <ethU> U => U -Int A </ethU>
       <amt>  A </amt>

  // trivial one-step carrier for pure R/G implication claims (#3–#8): body is a no-op, the content is in
  // requires (Guar characteristic) / ensures (Rely).  The step guarantees >=1 real transition.
  rule <k> #check => #done ... </k>
endmodule
