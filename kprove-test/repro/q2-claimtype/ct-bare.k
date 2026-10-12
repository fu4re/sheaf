requires "ct-semantics.k"
module CT-BARE
  imports CT
  claim <k> ctStart => ctDone ... </k>   [label(ct-bare)]
endmodule
