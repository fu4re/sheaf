// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

contract CappedToken {
    uint256 public cap = 1000;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    function mint(address to, uint256 amount) public {
        require(totalSupply + amount <= cap, "cap"); // FIX: post-state check
        totalSupply += amount;
        balanceOf[to] += amount;
    }
}

contract __ReachHarness is CappedToken {
    function __check_invariant() public view {
        assert(totalSupply <= cap); // __INVARIANT__ (reachability probe injects false)
    }
}
