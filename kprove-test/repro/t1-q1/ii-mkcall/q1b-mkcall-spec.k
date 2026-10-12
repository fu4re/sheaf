requires "evm.md"

// Q1 Tier B — the forked #mkCall rule really increments <callCounter> on execution.
// All four message-call opcodes (CALL/CALLCODE/DELEGATECALL/STATICCALL) funnel through
// #mkCall (recon: evm.md  #call -> #callWithCode -> #mkCall).  We drive ONE step of #mkCall
// (kprove --max-depth 1) with every cell the rule touches given explicitly, and target <k>
// set to the exact one-step residual.  The only interesting cell is <callCounter>: it must
// go CC -> CC+1.  useGas=false keeps <gas>/<callGas> unchanged (no #if branch).
module Q1B-MKCALL-SPEC
  imports EVM

  claim [mkcall-increments]:
    <k> #mkCall 42 43 43 .Bytes 0 .Bytes false
     => #touchAccounts 42 43
     ~> #accessAccounts 42 43
     ~> #loadProgram .Bytes
     ~> #initVM
     ~> #precompiled?(43, SHANGHAI)
     ~> #execute ... </k>
    <useGas>      false      </useGas>
    <schedule>    SHANGHAI   </schedule>
    <callCounter> CC => CC +Int 1 </callCounter>
    <callDepth>   CD => CD +Int 1 </callDepth>
    <callData>    _  => .Bytes    </callData>
    <callValue>   _  => 0         </callValue>
    <id>          _  => 43        </id>
    <codeAddr>    _  => 43        </codeAddr>
    <gas>         1000:Gas        </gas>
    <callGas>     500:Gas         </callGas>
    <caller>      _  => 42        </caller>
    <static>      false => false orBool false </static>
    requires CC >=Int 0
endmodule
