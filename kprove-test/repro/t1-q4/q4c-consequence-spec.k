requires "q4-semantics.k"

// Consequence junction, NO trusted lemma. Segment 1 reaches Post_i: <k> post </k>, n = X+1.
// The parent's target is the WEAKER Pre_j predicate  (exists ?Y >= X).  The reached state
// implies it, so the junction closes by SUBSUMPTION / implication — there is no rule that
// rewrites `post`, and none is applied. Expect PROVED with exactly ONE rewrite (seg1) and
// the terminal node closed by subsumption (an implication check, not a rule edge).
module Q4C-CONSEQUENCE-SPEC
  imports Q4
  claim [consequence-junction]:
    <k> seg1 => post ... </k>
    <n> X => ?Y:Int </n>
    ensures ?Y >=Int X
endmodule
