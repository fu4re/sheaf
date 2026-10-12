// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// THE FIX (review points #1/#2): discharge the actual mined caller guarantee, in its
/// callee-side form. The mined weakest interface clause is `vaultBal_post >= vaultBal +
/// assets` (the vault's balance rises by at least `assets`). Its callee-side meaning is:
/// a transfer credits the recipient by >= `amount`. This 2-state harness snapshots the
/// recipient balance before/after and asserts the delta — the property the caller
/// RELIES ON, not (only) conservation. Honest token: PROVEN.
///
/// Uses the allowance-free `transfer(from, to, amount)` + `mint` so the body is
/// REACHABLE (a transferFrom gated on an unset allowance would prove VACUOUSLY — the
/// dead-code trap; its non-vacuity is confirmed by BurnFeeERC20Delta refuting).
contract MiniERC20Delta {
    mapping(address => uint256) public balanceOf;

    function mint(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[to] += amount;
    }

    function transfer(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(amount <= type(uint128).max, "amt cap");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        uint256 beforeTo = balanceOf[to];
        balanceOf[from] -= amount;
        balanceOf[to]   += amount;
        assert(balanceOf[to] >= beforeTo + amount); // __INVARIANT__ delta >= amount (== mined G_B)
    }
}
