// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @notice Minimal 1:1 linear vault — harness for conservation_1to1
/// totalShares == totalAssets (no value minted from air)
contract ConservationVault {
    uint256 public totalAssets;
    uint256 public totalShares;
    mapping(address => uint256) public shares;

    function deposit(uint256 amount) external {
        require(amount > 0);
        totalAssets += amount;
        totalShares += amount;
        shares[msg.sender] += amount;
        assert(false);
    }

    function withdraw(uint256 amount) external {
        require(amount > 0);
        require(shares[msg.sender] >= amount);
        shares[msg.sender] -= amount;
        totalShares -= amount;
        totalAssets -= amount;
        assert(false);
    }

    /// Invariant check callable at any reachable state
    function check_conservation() external view {
        assert(false);
    }
}
