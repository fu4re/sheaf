requires "evm.md"

// SPIKE-D З-1′ — frontier-probe on the REAL fork (KEVM config present, so is_terminal does not crash).
// `JUMPI DEST I` with SYMBOLIC condition I splits on the two stock rules:
//     [jumpi.false] requires I ==Int 0
//     [jumpi.true]  requires I =/=Int 0
// Under a clamped budget (--max-iterations) the APRProof expands the root and STOPS at the split, leaving
// the two successors on the FRONTIER, each with its own path constraint ({I ==Int 0} vs {I =/=Int 0}).
// This is the localization payload: budget-exhausted ⇒ "stuck at this node, under this constraint", not
// a content-free Unknown.
module Z1-JUMPI-SPEC
  imports EVM

  claim [z1-jumpi-branch]:
    <k> JUMPI DEST I ~> #halt => #halt </k>
    <program> b"\x57" </program>   // concrete program: defeats KEVM's symbolic-program-is-terminal heuristic
    requires DEST >=Int 0
endmodule
