// Q4 — TCG-005 §6.2: consequence-mechanics of a junction.
// One real step  seg1 -> post  (n := n+1). There is deliberately NO rule from `post`.
// Two ways to reach the parent's target are contrasted by the two specs:
//   q4c (consequence): the junction Post_i -> Pre_j is an IMPLICATION (subsumption), no rule.
//   q4t (trusted):     the junction is a TRUSTED RULE application (a rewrite of `post`).
module Q4
  imports INT
  configuration <k> $PGM:K </k> <n> 0:Int </n>
  syntax KItem ::= "seg1" | "post" | "done"
  rule <k> seg1 => post ... </k> <n> X => X +Int 1 </n>
endmodule
