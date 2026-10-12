// SPDX-License-Identifier: UNLICENSED
pragma solidity ^0.8.13;

import {B} from "src/Coverage.sol";

contract CoverageTest {
    B b;
    function setUp() public { b = new B(); }

    // Caller does NOT establish B.f's precondition (x > 10). r == x, so r > 10
    // holds iff the precondition is enforced at THIS call site.
    function test_coverage_miss(uint256 x) public view {
        uint256 r = b.f(x);
        assert(r > 10);
    }
}
