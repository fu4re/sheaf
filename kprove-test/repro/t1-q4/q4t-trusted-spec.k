requires "q4-semantics.k"

// Contrast: the SAME parent target, but the junction post -> done is a TRUSTED RULE
// (a rewrite), not a subsumption. In the log this shows up as an extra rewrite EDGE that
// applies the trusted claim (with its label/id), whereas q4c has no such edge — its
// junction is an implication check. This is the step-4 discriminator.
module Q4T-TRUSTED-SPEC
  imports Q4
  claim [trusted-step]:
    <k> post => done ... </k>
    <n> X => X </n>
    [trusted, label(trusted-junction)]

  claim [parent-via-trusted]:
    <k> seg1 => done ... </k>
    <n> X => ?Y:Int </n>
    ensures ?Y >=Int X
endmodule
