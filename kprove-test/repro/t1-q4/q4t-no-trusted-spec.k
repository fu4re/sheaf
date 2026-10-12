requires "q4-semantics.k"

// Discriminator probe: the SAME parent target as q4t, but WITHOUT the trusted-step claim.
// `done` is reachable only by a rewrite of `post`; with no such rule (and no trusted lemma),
// the proof must FAIL. This is what distinguishes a trusted-RULE junction (a rewrite whose
// removal breaks the proof) from a consequence junction (pure implication; q4c needs no
// rule out of `post` at all and still proves).
module Q4T-NO-TRUSTED-SPEC
  imports Q4
  claim [parent-no-trusted]:
    <k> seg1 => done ... </k>
    <n> X => ?Y:Int </n>
    ensures ?Y >=Int X
endmodule
