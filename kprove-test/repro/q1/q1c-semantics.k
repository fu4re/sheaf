// Q1 clean design: NO semantic rule rewrites q1Start.
// The ONLY way to leave a q1Start(_) head is a trusted lemma.
// => if a trusted claim is an axiom usable from step 0, the goal closes;
//    if it is a circularity (usable only after >=1 real step), the goal
//    is stuck at step 0 (no real rule enables a first step) and FAILS.
module Q1C
  imports INT

  configuration <k> $PGM:K </k>

  syntax KItem ::= q1Start(Int)   [symbol(q1Start)]
                 | q1Claimed(Int) [symbol(q1Claimed)]
                 | q1Check(Int)   [symbol(q1Check)]

  // The only real rule: consume a matching claimed/check pair.
  // There is deliberately NO rule with q1Start on the left-hand side.
  rule <k> q1Claimed(I) ~> q1Check(I) => .K ... </k>
endmodule
