// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Reference SUT for the QUANTIFIED invariant class: a mock ERC20-ish vault with
/// per-user `balances`. The economic law `sum(balances) == totalSupply` is NOT
/// expressible as a stateless Solidity expression (no quantifier over a mapping)
/// — exactly the `sumAllBalance() == totalSupply()` Finding-0001 missed.
/// Its trusted lowering is `trusted/harness/SumVaultGhost.sol` (tracked-sum ghost).
contract SumVault {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;

    function deposit(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(totalSupply <= type(uint128).max, "supply cap");
        require(balances[to] <= type(uint128).max, "bal cap");
        balances[to] += amount;
        totalSupply += amount;
    }

    function transfer(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(balances[from] >= amount, "insufficient");
        require(balances[to] <= type(uint128).max, "bal cap");
        balances[from] -= amount;
        balances[to] += amount;
    }
}
