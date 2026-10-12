module BASE
  imports INT
  configuration <k> $PGM:K </k>
                <acct> 0 </acct>
  rule <k> X:Int => X +Int 1 ... </k>
       <acct> N => N +Int X </acct>
endmodule
