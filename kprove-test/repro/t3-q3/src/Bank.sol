// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// The withdraw mini-instance C (T2 §0), canonical drainable form so the concrete reentrancy actually nets a
// drain under Solidity-0.8 checked arithmetic (a plain `bal -= amt` would underflow-revert and self-defeat;
// the classic DAO drain is the "read full balance, external call, THEN zero" shape — same operation-ORDER
// defect the R/G discipline flags in Q1).
contract Bank {
    mapping(address => uint256) public balances;

    function deposit() external payable {
        balances[msg.sender] += msg.value;
    }

    // VULNERABLE: external call BEFORE the ledger write (V2 before V4).
    function withdraw_V() external {
        uint256 amt = balances[msg.sender];
        require(amt > 0, "zero");
        (bool ok, ) = msg.sender.call{value: amt}("");   // V2 SUSPENSION (reentry vector)
        require(ok, "call");
        balances[msg.sender] = 0;                         // V4 ledger write AFTER the call
    }

    // FIXED (checks-effects-interactions): ledger write BEFORE the external call (F2 before F3).
    function withdraw_F() external {
        uint256 amt = balances[msg.sender];
        require(amt > 0, "zero");
        balances[msg.sender] = 0;                         // F2 ledger write BEFORE the call
        (bool ok, ) = msg.sender.call{value: amt}("");    // F3 SUSPENSION
        require(ok, "call");
    }
}
