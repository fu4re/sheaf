// Branching semantics: from ctStart there are TWO successors.
//   ctStart => ctA => ctDone        (reaches target)
//   ctStart => ctB                  (stuck; ctB is a non-target terminal)
// A claim `ctStart => ctDone`:
//   all-path (AF)  -> FAILS  (the ctB branch never reaches ctDone)
//   one-path (EF)  -> PROVES (the ctA branch reaches ctDone)
// So the bare-claim (no attribute) verdict reveals the DEFAULT claim type.
module CT
  imports INT
  configuration <k> $PGM:K </k>
  syntax KItem ::= "ctStart" | "ctA" | "ctB" | "ctDone"
  rule <k> ctStart => ctA ... </k>
  rule <k> ctStart => ctB ... </k>
  rule <k> ctA => ctDone ... </k>
endmodule
