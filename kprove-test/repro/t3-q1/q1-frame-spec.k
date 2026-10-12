requires "withdraw.k"

// #1 frame-deposit, #2 frame-withdraw (V and F).  Edge type = trusted-lemma (target is a ⊨⁺ node: the body
// does >=1 real step).  Frame property: the write-set ⊆ Foot_w, i.e. <sumOth> (Σ other users' ledger, the
// only cell OUTSIDE the footprint) is UNCHANGED while the footprint cells take exactly their declared writes.
// Identical write-set for V and F (order differs, set does not) -> both PASS.
module Q1-FRAME-SPEC
  imports WITHDRAW

  claim [frame-deposit]:
    <k> deposit => .K </k>
    <balU>   B  => B +Int A </balU>     // in Foot_w_d
    <ethC>   C  => C +Int A </ethC>     // in Foot_w_d
    <ethU>   U  => U -Int A </ethU>     // in Foot_w_d
    <sumOth> SO => SO       </sumOth>   // OUT of Foot_w_d -> must be untouched
    <amt>    A </amt>

  claim [frame-withdraw-V]:
    <k> reqGE ~> xfer ~> debit => .K </k>
    <balU>   B  => B -Int A </balU>
    <ethC>   C  => C -Int A </ethC>
    <ethU>   U  => U +Int A </ethU>
    <sumOth> SO => SO       </sumOth>   // OUT of Foot_w_w -> untouched
    <amt>    A </amt>
    requires B >=Int A

  claim [frame-withdraw-F]:
    <k> reqGE ~> debit ~> xfer => .K </k>
    <balU>   B  => B -Int A </balU>
    <ethC>   C  => C -Int A </ethC>
    <ethU>   U  => U +Int A </ethU>
    <sumOth> SO => SO       </sumOth>
    <amt>    A </amt>
    requires B >=Int A
endmodule
