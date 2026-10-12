requires "q1c-semantics.k"
module Q1C-C-FALSE-TRUSTED
  imports Q1C
  // Deliberately FALSE trusted lemma: real q1Start(1) is NOT q1Claimed(42).
  // Must still be accepted (prover does not re-prove trusted claims).
  claim <k> q1Start(1) => q1Claimed(42) ... </k>  [trusted, label(lemma-false)]
  claim <k> q1Start(1) ~> q1Check(42) => .K ... </k> [label(goal-c)]
endmodule
