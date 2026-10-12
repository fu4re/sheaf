requires "q1-semantics.k"

module Q1-TRUE-TRUSTED-SPEC
  imports Q1-TRUSTED

  claim <k> q1Start(1) => q1Claimed(1) ... </k>
    [trusted, label(q1-lemma-true-trusted)]

  claim <k> q1Start(1) ~> q1Check(1) => .K ... </k>
    [label(q1-goal-needs-true-lemma)]
endmodule
