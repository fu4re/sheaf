requires "q1-semantics.k"

module Q1-FALSE-TRUSTED-SPEC
  imports Q1-TRUSTED

  claim <k> q1Start(1) => q1Claimed(42) ... </k>
    [trusted, label(q1-lemma-false-trusted)]

  claim <k> q1Start(1) ~> q1Check(42) => .K ... </k>
    [label(q1-goal-needs-false-lemma)]
endmodule
