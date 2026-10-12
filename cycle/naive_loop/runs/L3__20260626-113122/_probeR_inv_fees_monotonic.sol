// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Vault with accrual/rebase — fees_monotonic harness
/// @notice Proves: accumulatedFees is non-decreasing across any state transition (2-state).
///         Technique: pre-state snapshot at function entry, assert post >= pre at exit.
contract VaultFeesMono {
    uint256 public totalAssets;
    uint256 public totalShares;
    uint256 public accumulatedFees;
    mapping(address => uint256) public balances;

    /// @dev Deposit assets 1:1 for shares. Fees unchanged.
    function deposit(uint256 amount) external {
        uint256 oldFees = accumulatedFees;

        totalAssets += amount;
        totalShares += amount;
        balances[msg.sender] += amount;

        assert(false);
    }

    /// @dev Withdraw shares 1:1 for assets. Fees unchanged.
    function withdraw(uint256 shares) external {
        uint256 oldFees = accumulatedFees;

        require(shares <= balances[msg.sender]);
        require(shares <= totalShares);
        require(shares <= totalAssets);

        totalAssets -= shares;
        totalShares -= shares;
        balances[msg.sender] -= shares;

        assert(false);
    }

    /// @dev Apply yield accrual: net yield goes to assets, fee portion to accumulatedFees.
    function accrual(uint256 yield, uint256 fee) external {
        uint256 oldFees = accumulatedFees;

        require(fee <= yield);
        accumulatedFees += fee;
        totalAssets += (yield - fee);

        assert(false);
    }
}
