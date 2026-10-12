// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import {Test} from "forge-std/Test.sol";
import {C} from "src/C.sol";

// Attach the reentrancy-relevant post-condition to the REAL compiled withdraw() bytecode:
// after withdraw(), the caller's ledger balance is zeroed (the CEI "effect" happened), and withdraw()
// does not revert when the recipient accepts ETH.  Symbolic deposit amount `amt`.
contract CProof is Test {
    C c;
    function setUp() public { c = new C(); }
    receive() external payable {}

    function prove_withdraw_zeroes(uint256 amt) public {
        vm.assume(amt < (1 << 128));
        vm.deal(address(this), amt);
        c.deposit{value: amt}();
        c.withdraw();
        assert(c.balances(address(this)) == 0);
    }

    // Discriminator: a deliberately FALSE post-condition.  A solver that actually decides the bytecode must
    // REFUTE this with a counterexample (amt > 0 ⇒ post-balance is 0, not amt) — proving Accept above is not a
    // vacuous rubber-stamp.
    function prove_withdraw_keeps(uint256 amt) public {
        vm.assume(amt > 0);
        vm.assume(amt < (1 << 128));
        vm.deal(address(this), amt);
        c.deposit{value: amt}();
        c.withdraw();
        assert(c.balances(address(this)) == amt);
    }
}
