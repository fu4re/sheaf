// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// BUGGY variant — `mintUnbacked` credits a user's balance (and the shadow sum)
/// WITHOUT increasing totalSupply. The conservation law `sum(balances) ==
/// totalSupply` then breaks: the solver must REFUTE `ghostSum == totalSupply`,
/// proving the tracked-sum ghost is not vacuous.
contract SumVaultGhostBuggy {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    uint256 public ghostSum;

    function deposit(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(totalSupply <= type(uint128).max, "supply cap");
        require(balances[to] <= type(uint128).max, "bal cap");
        balances[to] += amount;
        totalSupply += amount;
        ghostSum += amount;
    }

    function mintUnbacked(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(balances[to] <= type(uint128).max, "bal cap");
        balances[to] += amount;
        ghostSum += amount; // BUG: sum grows but totalSupply does NOT
    }

    function __check() public view {
        assert(ghostSum == totalSupply); // __INVARIANT__
    }
}
