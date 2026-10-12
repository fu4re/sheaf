requires "q3-semantics.k"

// Positive: the goal is applicable as its OWN circularity.
// For symbolic N >= 0 this cannot close by bounded unrolling; it closes only because after
// the first `loop` step K discharges the residual (loop, count(N-1)) against this very goal
// (the circularity). PROVED  =>  goal in C (self-applicable after >= 1 step).
module Q3-LOOP-SPEC
  imports Q3
  claim [countdown]:
    <k> loop => .K ... </k>
    <count> N => 0 </count>
    requires N >=Int 0
endmodule
