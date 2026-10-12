requires "evm.md"

// Q1 variant (ii): instrumentation lives INSIDE the semantics (forked evm.md).
// <callCounter> is incremented at the two shared internal junctions
//   #mkCall   -> every message-call frame (CALL/CALLCODE/DELEGATECALL/STATICCALL)
//   #mkCreate -> every create frame (CREATE/CREATE2)
// i.e. N = 2 edited rules cover all 6 opcodes (vs 6 if edited per-opcode).
module KEVM-FORK-MKCALL
  imports EVM
endmodule
