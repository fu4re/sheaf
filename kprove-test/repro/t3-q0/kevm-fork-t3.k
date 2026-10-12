requires "evm.md"

// T3 fork = T1 fork (<callCounter> on #mkCall/#mkCreate) + <inFunc> stack-like monitor.
// <inFunc> : Map(FuncSig4 -> active frames in the monitored contract C).
//   increment: existing junction #mkCall, guarded callee == <monitoredAddr> (K4), key = selector of the new frame's calldata (ARGS[0..4]).
//   decrement: three frame-exit junctions #return.exception / #return.revert / #return.success,
//              each fires BEFORE #popCallStack, so <callData> is still the finishing frame's -> selector readable pre-pop.
//   reentered(sig) := <inFunc>[sig] >=Int 2.
module KEVM-FORK-T3
  imports EVM
endmodule
