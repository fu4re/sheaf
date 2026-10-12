// Q1 discriminator D2: a real FIRST step (q1Boot => q1Start) exists, but
// still NO rule rewrites q1Start. So after >=1 real step the head is q1Start,
// and only a trusted/circularity lemma can move further.
//   axiom-from-step-0 -> passes (lemma usable anytime)
//   circularity-guarded -> passes ONLY here (lemma usable after the 1 step)
//   trusted-not-applied -> fails (lemma never fires)
// Compare with D1 (no leading step): D1 fail + D2 pass == circularity-guarded.
module Q1D
  imports INT
  configuration <k> $PGM:K </k>
  syntax KItem ::= q1Boot(Int)    [symbol(q1Boot)]
                 | q1Start(Int)   [symbol(q1Start)]
                 | q1Claimed(Int) [symbol(q1Claimed)]
                 | q1Check(Int)   [symbol(q1Check)]
  rule <k> q1Boot(I) => q1Start(I) ... </k>
  rule <k> q1Claimed(I) ~> q1Check(I) => .K ... </k>
endmodule
