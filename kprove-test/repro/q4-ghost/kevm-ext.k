// Q4 KEVM-specific: add a ghost <callCounter> cell to the KEVM configuration
// from an EXTERNAL module that imports EVM, WITHOUT editing any evm-semantics file.
requires "evm.md"
module KEVM-EXT
  imports EVM
  configuration <callCounter> 0 </callCounter>
endmodule
