// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Adversarial callee B'' — fee-on-transfer token. `transferFrom` credits the
/// recipient LESS than `amount` (a fee of 1 is skimmed and lost). This violates the
/// per-transfer delta clause of G_B that the caller summary assumes
/// (vaultBal_post == vaultBal + assets): the vault is credited `amount - 1` while it
/// accounts `amount`, so solvency `balanceOf(vault) >= totalAssets` eventually
/// breaks. Unlike HostileERC20's frame violation, this is a VALUE-clause violation
/// and is a *state* property of B — so obligation 2 catches it directly (discharging
/// the delta clause against FeeERC20 is refuted). The fee token is the canonical
/// real-world callee that silently breaks vault accounting.
contract FeeERC20 {
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    uint256 public totalSupply;

    function approve(address spender, uint256 amount) public returns (bool) {
        allowance[msg.sender][spender] = amount;
        return true;
    }

    function transferFrom(address from, address to, uint256 amount) public returns (bool) {
        require(amount > 0, "zero");
        require(allowance[from][msg.sender] >= amount, "allowance");
        require(balanceOf[from] >= amount, "insufficient");
        require(balanceOf[to] <= type(uint128).max, "bal cap");
        uint256 received = amount - 1; // fee of 1 — skimmed and LOST
        allowance[from][msg.sender] -= amount;
        balanceOf[from]             -= amount;
        balanceOf[to]               += received; // credited LESS than amount
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
