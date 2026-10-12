requires "main.k"

// Q1 variant (i) — demonstrate the self-application anti-pattern.
// The external priority-40 rule rewrites CALL back to CALL while incrementing the ghost
// cell. Because 40 < 50 (stock [call]) it always wins, so:
//   * <callCounter> grows once PER STEP, not once per call (over-counts), and
//   * the stock [call] rule NEVER fires -> CALL is never consumed -> the call never executes.
// Run bounded (kprove --max-depth 8): the frontier shows <callCounter> = 8 with CALL still
// at the <k> head, i.e. the proof cannot progress to #end -> non-terminating & unsound.
module Q1I-SELFLOOP-SPEC
  imports Q1I-PRIORITY

  claim [selfloop]:
    <k> CALL 0 43 0 0 0 0 0 => #end EVMC_SUCCESS ... </k>
    <callCounter> 0 => ?_FINAL:Int </callCounter>
endmodule
