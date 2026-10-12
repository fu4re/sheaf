// Q4 KEVM variant 2: add the ghost cell NESTED inside <kevm> (the single top
// cell), via an external module. K merges configuration cells by name/path.
requires "evm.md"
module KEVM-EXT2
  imports EVM
  configuration <kevm> <callCounter> 0 </callCounter> </kevm>
endmodule
