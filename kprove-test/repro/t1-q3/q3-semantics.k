// Q3 — TCG-005 §6.1: goal-as-own-circularity.
// A countdown loop: `loop` steps while <count> > 0, decrementing; base case at 0.
// Proving  loop / count(N) => count(0)  for SYMBOLIC N >= 0 needs induction: after one
// step the residual (loop, count(N-1)) must be discharged by the GOAL ITSELF used as a
// circularity (coinductive hypothesis), which K registers only after >= 1 execution step.
// If the goal proves for symbolic N, the goal was applicable as its own circularity.
module Q3
  imports INT
  configuration <k> $PGM:K </k> <count> 0:Int </count>
  syntax KItem ::= "loop"
  rule <k> loop => loop ... </k> <count> N => N -Int 1 </count> requires N >Int 0
  rule <k> loop => .K   ... </k> <count> 0 </count>
endmodule
