// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @notice Minimal 1:1 linear vault — harness for solvency_price_geq_1
/// totalAssets >= totalShares (every share backed by >= 1 asset unit)
contract SolvencyVault {
    uint256 public totalAssets;
    uint256 public totalShares;
    mapping(address => uint256) public shares;

    function deposit(uint256 amount) external {
        require(amount > 0);
        totalAssets += amount;
        totalShares += amount;
        shares[msg.sender] += amount;
        assert(totalAssets >= totalShares);
    }

    function withdraw(uint256 amount) external {
        require(amount > 0);
        require(shares[msg.sender] >= amount);
        shares[msg.sender] -= amount;
        totalShares -= amount;
        totalAssets -= amount;
        assert(totalAssets >= totalShares);
    }

    /// Invariant check callable at any reachable state
    function check_solvency() external view {
        assert(totalAssets >= totalShares);
    }
}
