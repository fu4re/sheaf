// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// PRE-FIXED ghost harness for SumVault (TRUSTED) — QUANTIFIED invariant class.
///
/// SMTChecker cannot quantify over a mapping, so `sum(balances)` is shadowed by a
/// scalar `ghostSum` maintained in lockstep with every balance write — mimicking
/// CVL's `ghost sumAllBalance` + SSTORE `hook`. The agent's quantified invariant
/// `sumAllBalance() == totalSupply()` lowers to `ghostSum == totalSupply`.
///
/// Trust model is identical to CVL's: the harness faithfully maintaining
/// `ghostSum == sum(balances)` is the (assumed) modelling step; the solver then
/// proves `ghostSum == totalSupply` inductively over all reachable states.
contract SumVaultGhost {
    mapping(address => uint256) public balances;
    uint256 public totalSupply;
    uint256 public ghostSum; // shadow of sum(balances), maintained by the harness

    function deposit(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(totalSupply <= type(uint128).max, "supply cap");
        require(balances[to] <= type(uint128).max, "bal cap");
        balances[to] += amount;
        totalSupply += amount;
        ghostSum += amount; // hook: balance +amount ⇒ sum +amount
    }

    function transfer(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(balances[from] >= amount, "insufficient");
        require(balances[to] <= type(uint128).max, "bal cap");
        balances[from] -= amount;
        balances[to] += amount;
        // hook: sum unchanged (−amount +amount) ⇒ ghostSum untouched
    }

    /// Invariant checked over ALL reachable states by the solver core [5].
    function __check() public view {
        assert(ghostSum == totalSupply); // __INVARIANT__ (gateway overwrites the expr)
    }
}
