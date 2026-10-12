requires "q1d-semantics.k"
module Q1D-C-FALSE-TRUSTED
  imports Q1D
  claim <k> q1Start(1) => q1Claimed(42) ... </k>       [trusted, label(lemma-false)]
  claim <k> q1Boot(1) ~> q1Check(42) => .K ... </k>    [label(goal-c2)]
endmodule
