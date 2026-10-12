requires "evm.md"

// SPIKE-T3 Q0 — <inFunc> stack-like reentrancy monitor on the T1 fork.
// Three depth-1 claims, each driving exactly one instrumented junction, with every
// cell the rule touches given explicitly and the <k> target = the exact one-step residual.
//   C (monitored contract) = account 43 ; selector SEL = #asWord(b"\x12\x34\x56\x78") = 305419896.
//
//   [entry-base]      #mkCall into C, <inFunc> .Map        -> (SEL |-> 1)   (increment, key from ARGS)
//   [entry-reenter]   #mkCall into C, <inFunc> (SEL |-> 1) -> (SEL |-> 2)   (reentered(SEL) := >=2 fires)
//   [exit-before-pop] #return.success, <inFunc> (SEL |-> 2) -> (SEL |-> 1)  (DECREMENT reads SEL from
//                     <callData> of the finishing frame, since #return.* fires BEFORE #popCallStack;
//                     had the read happened post-pop, <callData> would be the parent's and the key
//                     would differ.  Proving 2->1 on key SEL is the selector-readable-before-pop proof.)
module Q0-INFUNC-SPEC
  imports EVM

  // ---- ENTRY: increment on #mkCall, keyed by the new frame's selector, guarded callee==C ----
  claim [entry-base]:
    <k> #mkCall 42 43 43 .Bytes 0 b"\x12\x34\x56\x78" false
     => #touchAccounts 42 43
     ~> #accessAccounts 42 43
     ~> #loadProgram .Bytes
     ~> #initVM
     ~> #precompiled?(43, SHANGHAI)
     ~> #execute ... </k>
    <useGas>        false               </useGas>
    <schedule>      SHANGHAI            </schedule>
    <monitoredAddr> 43                  </monitoredAddr>
    <inFunc>        .Map => (305419896 |-> 1) </inFunc>
    <callCounter>   CC => CC +Int 1     </callCounter>
    <callDepth>     CD => CD +Int 1     </callDepth>
    <callData>      _  => b"\x12\x34\x56\x78" </callData>
    <callValue>     _  => 0             </callValue>
    <id>            _  => 43            </id>
    <codeAddr>      _  => 43            </codeAddr>
    <gas>           1000:Gas            </gas>
    <callGas>       500:Gas             </callGas>
    <caller>        _  => 42            </caller>
    <static>        false => false orBool false </static>
    requires CC >=Int 0

  // ---- REENTER: a second active frame of the SAME selector -> <inFunc>[SEL] = 2 = reentered ----
  claim [entry-reenter]:
    <k> #mkCall 42 43 43 .Bytes 0 b"\x12\x34\x56\x78" false
     => #touchAccounts 42 43
     ~> #accessAccounts 42 43
     ~> #loadProgram .Bytes
     ~> #initVM
     ~> #precompiled?(43, SHANGHAI)
     ~> #execute ... </k>
    <useGas>        false               </useGas>
    <schedule>      SHANGHAI            </schedule>
    <monitoredAddr> 43                  </monitoredAddr>
    <inFunc>        (305419896 |-> 1) => (305419896 |-> 2) </inFunc>
    <callCounter>   CC => CC +Int 1     </callCounter>
    <callDepth>     CD => CD +Int 1     </callDepth>
    <callData>      _  => b"\x12\x34\x56\x78" </callData>
    <callValue>     _  => 0             </callValue>
    <id>            _  => 43            </id>
    <codeAddr>      _  => 43            </codeAddr>
    <gas>           1000:Gas            </gas>
    <callGas>       500:Gas             </callGas>
    <caller>        _  => 42            </caller>
    <static>        false => false orBool false </static>
    requires CC >=Int 0

  // ---- EXIT: decrement at #return.success, key read from <callData> BEFORE #popCallStack ----
  claim [exit-before-pop]:
    <k> #halt ~> #return 0 0
     => #popCallStack ~> #dropWorldState ~> 1 ~> #push ~> #refund 1000:Gas ~> #setLocalMem 0 0 .Bytes ... </k>
    <statusCode>    EVMC_SUCCESS        </statusCode>
    <monitoredAddr> 43                  </monitoredAddr>
    <id>            43                  </id>
    <callData>      b"\x12\x34\x56\x78" </callData>
    <inFunc>        (305419896 |-> 2) => (305419896 |-> 1) </inFunc>
    <output>        .Bytes              </output>
    <gas>           1000:Gas            </gas>
endmodule
