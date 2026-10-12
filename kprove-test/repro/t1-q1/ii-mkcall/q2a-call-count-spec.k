requires "evm.md"

// Q2a — a REAL message-call opcode (STATICCALL from A=1 to B=100) drives the counter.
// Starting at the opcode (post stack-pop form), execution dispatches
//   STATICCALL -> #accessAccounts -> #checkCall -> #call -> #callWithCode -> #mkCall
// and #mkCall (the fork's instrumented junction) increments <callCounter> exactly once.
// Target counter = 1 with <k> free: the proof closes at the node where the single call
// frame has been entered, i.e. one external call => Post has callCounter = pre + 1.
module Q2A-CALL-COUNT-SPEC
  imports EVM

  claim [staticcall-counts-once]:
    <k> STATICCALL 0 100 0 0 0 0 ~> #halt => ?_REST:K ... </k>
    <id>          1          </id>
    <caller>      0          </caller>
    <localMem>    .Bytes     </localMem>
    <wordStack>   .WordStack </wordStack>
    <callDepth>   0          </callDepth>
    <static>      false      </static>
    <schedule>    SHANGHAI   </schedule>
    <useGas>      false      </useGas>
    <gas>         1000000:Gas </gas>
    <callGas>     1000000:Gas </callGas>
    <accessedAccounts> .Set => ?_AA </accessedAccounts>
    <callCounter> 0 => 1 </callCounter>
    <accounts>
      <account>
        <acctID> 1 </acctID> <balance> 100 </balance> <code> .Bytes:AccountCode </code>
        <storage> .Map </storage> <origStorage> .Map </origStorage>
        <transientStorage> .Map </transientStorage> <nonce> 0 </nonce>
      </account>
      <account>
        <acctID> 100 </acctID> <balance> 0 </balance> <code> .Bytes:AccountCode </code>
        <storage> .Map </storage> <origStorage> .Map </origStorage>
        <transientStorage> .Map </transientStorage> <nonce> 0 </nonce>
      </account>
    </accounts>
endmodule
