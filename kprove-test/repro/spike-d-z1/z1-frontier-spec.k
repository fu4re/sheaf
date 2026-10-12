requires "withdraw.k"

// SPIKE-D З-1′ — "does Unknown carry localization?"  Frontier-probe on the withdraw model.
//
// The claim runs the withdraw_V body (reqGE ~> susp ~> debit) from a FULLY SYMBOLIC ledger state
// (balU = B, amt = A free) with NO `requires`.  The very first k-item, `reqGE`, has two rules that
// split on B >=Int A vs B <Int A.  Under a clamped budget (--max-iterations 1) the APRProof expands the
// root exactly once and STOPS, leaving the two successors on the FRONTIER (pending, unexplored).
// If the З-1′ hypothesis holds, each pending node is NAMED and carries its own path constraint
// (B >=Int A on one branch, B <Int A on the other) — i.e. Unknown localizes "stuck here, under this
// constraint", not a content-free "couldn't".
//
// The claim is deliberately not a theorem (the storage cells are pinned unchanged while the body writes
// them) — we are probing the interrupted proof's data structure, not trying to close it.
module Z1-FRONTIER-SPEC
  imports WITHDRAW

  claim [z1-withdraw-V-symbolic]:
    <k> reqGE ~> susp ~> debit ~> #done => #done </k>
    <balU>   B </balU>
    <amt>    A </amt>
    <ethC>   C </ethC>
    <ethU>   UE </ethU>
    <sumOth> S </sumOth>
endmodule
