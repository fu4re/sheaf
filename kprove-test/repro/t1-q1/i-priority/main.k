requires "evm.md"

// Q1 variant (i): NON-invasive attempt. Increment <callCounter> from an EXTERNAL module
// with a higher-priority rule, WITHOUT editing the standard [call] rule. The naive form
// (rewrite CALL back to CALL so the stock rule can "still fire") self-applies forever:
// priority 40 < stock 50, so this rule always wins and the stock [call] is never reached.
module Q1I-PRIORITY
  imports EVM

  rule [ghost-call-selfloop]:
       <k> CALL GCAP ACCTTO VALUE ARGSTART ARGWIDTH RETSTART RETWIDTH
        => CALL GCAP ACCTTO VALUE ARGSTART ARGWIDTH RETSTART RETWIDTH ... </k>
       <callCounter> C => C +Int 1 </callCounter>
       [priority(40)]
endmodule
