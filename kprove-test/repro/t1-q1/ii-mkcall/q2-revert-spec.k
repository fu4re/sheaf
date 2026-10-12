requires "evm.md"

// Q2b — does the ghost cell survive REVERT?
// KEVM enters a call frame with  #pushCallStack ~> #pushWorldState  and reverts it with
// #popCallStack ~> #popWorldState (see EVM.return.revert, evm.md:1835).
//   #pushCallStack/#popCallStack (evm.md:246/252) save & restore ONLY <callState>.
//   #pushWorldState/#popWorldState (evm.md:276/283) save & restore ONLY <accounts>+<substate>.
// <callCounter> lives directly under <kevm>, outside <ethereum> and outside <callState>,
// so NONE of the four revert ops mentions it.  We execute the whole enter+revert sequence
// and check the counter is transparent to it: it keeps whatever value a call left in it.
module Q2-REVERT-SPEC
  imports EVM

  claim [ghost-survives-revert]:
    <k> #pushCallStack ~> #pushWorldState ~> #popCallStack ~> #popWorldState => .K ... </k>
    <callCounter> 7 => 7 </callCounter>
endmodule
