requires "evm.md"

// Q1 regression: a STOCK KEVM spec (adapted verbatim from the KEVM tree,
// media/201908-trufflecon/add-spec.k) must still prove on the fork.
// This exercises standard arithmetic + the #next[_] opcode dispatcher.
// It does NOT mention <callCounter>, so if the fork changed nothing for
// standard behaviour it proves exactly as on stock.  (Doubles as a negative
// control: ADD is not a call, so <callCounter> stays put.)
module REGRESSION-ADD-SPEC
    imports EVM

    claim [add]:
         <k> #next [ ADD ] => .K ... </k>
         <schedule> SCHEDULE </schedule>
         <useGas> true </useGas>
         <wordStack> W0 : W1 : WS => chop(W0 +Int W1) : WS </wordStack>
         <pc> PCOUNT => PCOUNT +Int 1 </pc>
         <gas> G => G -Int Gverylow < SCHEDULE > </gas>
      requires G >=Int Gverylow < SCHEDULE >
       andBool notBool ( #stackUnderflow ( W0 : W1 : WS , ADD )
                  orBool #stackOverflow  ( W0 : W1 : WS , ADD )
                       )
endmodule
