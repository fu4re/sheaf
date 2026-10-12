// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {D} from "src/Mapping.sol";

contract MappingTest {
    D d;
    function setUp() public { d = new D(); }
    // Prove D.h directly (as a summary target) so the precondition is parsed/applied.
    // We watch the log for a warning vs silent ignore of the mapping-access precondition.
    function test_mapping_precond(uint256 x) public view {
        uint256 r = d.h(x);
        assert(r >= x);
    }
}
