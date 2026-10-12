// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @notice Minimal 1:1 linear vault — harness for no_orphan_shares
/// totalShares == 0 <=> totalAssets == 0 (no shares without backing, no assets without shares)
contract OrphanVault {
    uint256 public totalAssets;
    uint256 public totalShares;
    mapping(address => uint256) public shares;

    function deposit(uint256 amount) external {
        require(amount > 0);
        totalAssets += amount;
        totalShares += amount;
        shares[msg.sender] += amount;
        assert((totalShares == 0) == (totalAssets == 0));
    }

    function withdraw(uint256 amount) external {
        require(amount > 0);
        require(shares[msg.sender] >= amount);
        shares[msg.sender] -= amount;
        totalShares -= amount;
        totalAssets -= amount;
        assert((totalShares == 0) == (totalAssets == 0));
    }

    /// Invariant check callable at any reachable state
    function check_no_orphan() external view {
        assert((totalShares == 0) == (totalAssets == 0));
    }
}
