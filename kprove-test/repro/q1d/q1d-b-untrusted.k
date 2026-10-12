requires "q1d-semantics.k"
module Q1D-B-UNTRUSTED
  imports Q1D
  claim <k> q1Start(1) => q1Claimed(1) ... </k>    [label(lemma-untrusted)]
  claim <k> q1Boot(1) ~> q1Check(1) => .K ... </k> [label(goal-b2)]
endmodule
