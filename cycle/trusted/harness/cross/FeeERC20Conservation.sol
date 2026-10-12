// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Callee-discharge harness for FeeERC20 (TRUSTED). Obligation 2 on the fee-on-
/// transfer token: the tracked-sum shadow `ghostSum` faithfully follows Σ balanceOf,
/// which DROPS by 1 on every transfer (the skimmed fee is lost, totalSupply
/// unchanged). So `ghostSum == totalSupply` becomes FALSE after the first transfer →
/// the solver REFUTES the conservation guarantee. This is obligation 2 catching the
/// canonical fee-on-transfer vault bug: a callee that does not satisfy the guarantee
/// the caller summary assumed (`transferFrom credits exactly amount`).
///
/// The fee op is the harness-style `transfer(from, to, amount)` (no allowance, so it
/// is REACHABLE after a mint — a fee buried in an unreachable transferFrom would prove
/// vacuously, the dead-code trap).
contract FeeERC20Conservation {
    mapping(address => uint256) public balanceOf;
    uint256 public totalSupply;
    uint256 public ghostSum; // shadow of Σ balanceOf

    function mint(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(totalSupply <= type(uint128).max, "supply cap");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[to] += amount;
        totalSupply   += amount;
        ghostSum      += amount;
    }

    function transfer(address from, address to, uint256 amount) public {
        require(from != to, "self");
        require(amount > 0, "zero");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[from] -= amount;
        balanceOf[to]   += amount - 1; // fee of 1 LOST
        ghostSum        -= 1;          // Σ dropped by the skimmed fee
    }

    function __check() public view {
        assert(ghostSum == totalSupply); // __INVARIANT__ (gateway overwrites the expr)
    }
}
