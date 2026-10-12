// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Minimal honest ERC20 — the callee B in the cross-contract A/G cycle.
///
/// Its guarantee G_B (what the caller is allowed to ASSUME at the call site):
///   * per-transfer delta: transfer/transferFrom move the receiver's balance up
///     by EXACTLY `amount` and the sender's down by EXACTLY `amount`;
///   * conservation: Σ balanceOf == totalSupply is preserved by every op;
///   * frame: a transfer touches ONLY the two balances involved — no reentrancy,
///     no callback (the property HostileERC20 / FeeERC20 deliberately break).
/// G_B is discharged by the solver in trusted/harness/cross/MiniERC20Conservation.sol
/// (tracked-sum) and the conservation fact is machine-checked in Lean
/// (Erc20.transfer_sum_preserved, axiom_registry.json).
contract MiniERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[msg.sender] -= amount;
        balanceOf[to]         += amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(allowance[from][msg.sender] >= amount, "allowance");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        allowance[from][msg.sender] -= amount;
        balanceOf[from]             -= amount;
        balanceOf[to]               += amount;
        return true;
    }

    function mint(address to, uint256 amount) public {
        require(amount <= type(uint128).max, "amt cap");
        require(totalSupply <= type(uint128).max, "supply cap");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        balanceOf[to] += amount;
        totalSupply   += amount;
    }
}
