requires "evm.md"

// SPIKE-T3 Q0 negative controls — both claims are DELIBERATELY FALSE and MUST FAIL.
// They prove the two positive claims are not vacuous / not false-greens:
//   [neg-no-decrement]  asserts <inFunc> is UNCHANGED across #return.success (2 => 2).
//                       The fork decrements, so the real post is (SEL |-> 1) != (SEL |-> 2)  -> FAIL.
//                       => the decrement genuinely fires (the [exit-before-pop] pass is real).
//   [neg-foreign-guard] #mkCall into a NON-monitored callee (44 != <monitoredAddr> 43) and asserts
//                       <inFunc> .Map => (SEL |-> 1).  #bump is identity when callee != C, so the
//                       real post is .Map  -> FAIL.  => the callee==C guard actually gates counting.
module Q0-NEGCTL-SPEC
  imports EVM

  claim [neg-no-decrement]:
    <k> #halt ~> #return 0 0
     => #popCallStack ~> #dropWorldState ~> 1 ~> #push ~> #refund 1000:Gas ~> #setLocalMem 0 0 .Bytes ... </k>
    <statusCode>    EVMC_SUCCESS        </statusCode>
    <monitoredAddr> 43                  </monitoredAddr>
    <id>            43                  </id>
    <callData>      b"\x12\x34\x56\x78" </callData>
    <inFunc>        (305419896 |-> 2) => (305419896 |-> 2) </inFunc>   // WRONG: fork decrements to (|-> 1)
    <output>        .Bytes              </output>
    <gas>           1000:Gas            </gas>

  claim [neg-foreign-guard]:
    <k> #mkCall 42 44 44 .Bytes 0 b"\x12\x34\x56\x78" false
     => #touchAccounts 42 44
     ~> #accessAccounts 42 44
     ~> #loadProgram .Bytes
     ~> #initVM
     ~> #precompiled?(44, SHANGHAI)
     ~> #execute ... </k>
    <useGas>        false               </useGas>
    <schedule>      SHANGHAI            </schedule>
    <monitoredAddr> 43                  </monitoredAddr>
    <inFunc>        .Map => (305419896 |-> 1) </inFunc>   // WRONG: callee 44 != C 43, so #bump is identity (.Map)
    <callCounter>   CC => CC +Int 1     </callCounter>
    <callDepth>     CD => CD +Int 1     </callDepth>
    <callData>      _  => b"\x12\x34\x56\x78" </callData>
    <callValue>     _  => 0             </callValue>
    <id>            _  => 44            </id>
    <codeAddr>      _  => 44            </codeAddr>
    <gas>           1000:Gas            </gas>
    <callGas>       500:Gas             </callGas>
    <caller>        _  => 42            </caller>
    <static>        false => false orBool false </static>
    requires CC >=Int 0
endmodule
