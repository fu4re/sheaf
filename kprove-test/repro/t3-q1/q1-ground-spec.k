requires "withdraw.k"

// Operation-order grounding: execute each withdraw body to the suspension point (#atSusp) and read off the
// continuation + bal[U].  This EARNS the Rely distinction used by #3/#6/#8 (it is not asserted):
//   V halts at `#atSusp ~> debit`  with bal[U] = B0        -> a bal-write is PENDING after suspension,
//                                                             and bal[U] is still the pre-CALL B0
//                                                             => Rely_w^V MUST pin bal[U] = B0.
//   F halts at `#atSusp`           with bal[U] = B0 -Int A  -> NO pending bal-write; the debit is committed
//                                                             => Rely_w^F over bal[U] = T (unconstrained).
module Q1-GROUND-SPEC
  imports WITHDRAW

  claim [ground-V-pending-debit]:
    <k> reqGE ~> susp ~> debit => #atSusp ~> debit </k>   // continuation still has `debit` : pending write
    <balU> B0 </balU>                                     // bal[U] UNCHANGED at suspension (= pre-CALL B0)
    <ethC> EC => EC -Int A </ethC>
    <ethU> EU => EU +Int A </ethU>
    <amt>  A </amt>
    requires B0 >=Int A

  claim [ground-F-no-pending]:
    <k> reqGE ~> debit ~> susp => #atSusp </k>            // continuation EMPTY : no pending write
    <balU> B0 => B0 -Int A </balU>                        // bal[U] already debited before suspension
    <ethC> EC => EC -Int A </ethC>
    <ethU> EU => EU +Int A </ethU>
    <amt>  A </amt>
    requires B0 >=Int A
endmodule
