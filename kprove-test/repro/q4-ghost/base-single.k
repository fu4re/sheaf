module BASE-SINGLE
  imports INT
  configuration <top> <k> $PGM:K </k> <acct> 0 </acct> </top>
  rule <k> X:Int => X +Int 1 ... </k> <acct> N => N +Int X </acct>
endmodule
