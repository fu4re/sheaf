requires "q1c-semantics.k"
module Q1C-B-UNTRUSTED
  imports Q1C
  // Same lemma L, but NOT trusted -> it becomes a goal / circularity.
  claim <k> q1Start(1) => q1Claimed(1) ... </k>   [label(lemma-untrusted)]
  claim <k> q1Start(1) ~> q1Check(1) => .K ... </k> [label(goal-b)]
endmodule
