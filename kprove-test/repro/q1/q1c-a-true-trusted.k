requires "q1c-semantics.k"
module Q1C-A-TRUE-TRUSTED
  imports Q1C
  // Lemma L, TRUSTED (assumed). Real semantics has no q1Start rule.
  claim <k> q1Start(1) => q1Claimed(1) ... </k>   [trusted, label(lemma-true)]
  // Goal G: can only close if L is applicable from step 0.
  claim <k> q1Start(1) ~> q1Check(1) => .K ... </k> [label(goal-a)]
endmodule
