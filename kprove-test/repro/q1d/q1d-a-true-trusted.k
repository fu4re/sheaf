requires "q1d-semantics.k"
module Q1D-A-TRUE-TRUSTED
  imports Q1D
  claim <k> q1Start(1) => q1Claimed(1) ... </k>        [trusted, label(lemma-true)]
  claim <k> q1Boot(1) ~> q1Check(1) => .K ... </k>     [label(goal-a2)]
endmodule
