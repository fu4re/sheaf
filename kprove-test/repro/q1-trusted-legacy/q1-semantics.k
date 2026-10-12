requires "domains.md"

module Q1-TRUSTED
  imports INT

  configuration <k> $PGM:K </k>

  syntax KItem ::= "q1Start" "(" Int ")"   [klabel(q1Start)]
                 | "q1Real" "(" Int ")"    [klabel(q1Real)]
                 | "q1Claimed" "(" Int ")" [klabel(q1Claimed)]
                 | "q1Check" "(" Int ")"   [klabel(q1Check)]

  rule <k> q1Start(I) => q1Real(I) ... </k>
  rule <k> q1Claimed(I) ~> q1Check(I) => .K ... </k>
endmodule
