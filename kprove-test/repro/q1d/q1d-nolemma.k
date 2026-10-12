requires "q1d-semantics.k"
module Q1D-NOLEMMA
  imports Q1D
  claim <k> q1Boot(1) ~> q1Check(1) => .K ... </k> [label(goal-nolemma)]
endmodule
