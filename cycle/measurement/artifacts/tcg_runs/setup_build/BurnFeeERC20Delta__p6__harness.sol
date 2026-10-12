// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// THE FIX catching THE GAP: the SAME burning-fee token that PASSES conservation
/// (BurnFeeERC20Conservation.sol → proved) is REFUTED by the delta discharge — it
/// credits the recipient by `amount - 1`, violating the mined caller guarantee
/// `vault balance += >= assets`. This is the per-clause callee discharge of the actual
/// relied-upon property; it closes the gap conservation-only obligation 2 left open.
/// Refuting here also proves the `transfer` body is REACHABLE, so MiniERC20Delta's
/// `proved` is non-vacuous (same structure).
contract BurnFeeERC20Delta {
    mapping(address => uint256) public balanceOf;

    function mint(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[to] += amount;
    }

    function transfer(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(amount > 0, "zero");
        require(amount <= type(uint128).max, "amt cap");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        uint256 beforeTo = balanceOf[to];
        balanceOf[from] -= amount;
        balanceOf[to]   += amount - 1; // under-credit (fee)
        assert(balanceOf[to] >= beforeTo + amount); // __INVARIANT__ (gateway-injected)
    }
}
