// Q3 negative control. Identical to Q3 EXCEPT the recursive step goes to `gone`, not
// `loop`. So after >= 1 step the head is `gone` and the goal pattern <k> loop </k> is
// never reachable again -> the goal cannot be applied as its own circularity. The only
// difference from Q3 is reachability of self-application; this isolates the mechanism.
module Q3NEG
  imports INT
  configuration <k> $PGM:K </k> <count> 0:Int </count>
  syntax KItem ::= "loop" | "gone"
  rule <k> loop => gone ... </k> <count> N => N -Int 1 </count> requires N >Int 0
  rule <k> loop => .K   ... </k> <count> 0 </count>
endmodule
