requires "evm.md"

// Q1 negative control: the ghost increment fires ONLY at call frames.
// A non-call opcode (ADD, via #next) must leave <callCounter> untouched.
module Q1-NEGCTL-SPEC
  imports EVM

  claim [add-does-not-count]:
    <k> #next [ ADD ] => .K ... </k>
    <schedule>  SHANGHAI </schedule>
    <useGas>    true     </useGas>
    <wordStack> W0 : W1 : WS => chop(W0 +Int W1) : WS </wordStack>
    <pc>        PCOUNT => PCOUNT +Int 1 </pc>
    <gas>       G  => G -Int Gverylow < SHANGHAI > </gas>
    <callCounter> CC => CC </callCounter>
   requires G >=Int Gverylow < SHANGHAI >
    andBool notBool ( #stackUnderflow ( W0 : W1 : WS , ADD )
               orBool #stackOverflow  ( W0 : W1 : WS , ADD ) )
endmodule
