requires "q3-neg-semantics.k"

// Negative control: same goal, but self-application is unreachable (step goes to `gone`).
// N=0 closes by the base rule; the N>0 branch reaches (gone, count(N-1)) and is stuck —
// the goal-circularity needs <k> loop </k>, which never recurs. Expect FAILED.
module Q3-NEG-SPEC
  imports Q3NEG
  claim [countdown-neg]:
    <k> loop => .K ... </k>
    <count> N => 0 </count>
    requires N >=Int 0
endmodule
