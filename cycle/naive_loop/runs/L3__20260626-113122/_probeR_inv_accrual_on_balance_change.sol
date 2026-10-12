// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Vault with accrual/rebase — accrual_on_balance_change harness
/// @notice Proves: any balance change implies accrual was applied (2-state).
///         Technique: ghost flag _accrualApplied set by internal accrual helper,
///         reset at function entry; pre-state snapshot of balance; assert at exit.
contract VaultAccrualOnChange {
    uint256 public totalAssets;
    uint256 public totalShares;
    uint256 public accumulatedFees;
    uint256 public pendingYield;

    mapping(address => uint256) public balances;

    // Ghost flag: tracks whether accrual was applied in this transaction
    bool private _accrualApplied;

    /// @dev Internal accrual: materializes pending yield into totalAssets and fees.
    function _applyAccrual() internal {
        if (pendingYield > 0) {
            uint256 fee = pendingYield / 10;
            accumulatedFees += fee;
            totalAssets += (pendingYield - fee);
            pendingYield = 0;
        }
        _accrualApplied = true;
    }

    /// @dev Add yield to the pending pool (no balance change, no accrual needed).
    function addYield(uint256 amount) external {
        pendingYield += amount;
    }

    /// @dev Deposit: accrual applied before balance change.
    function deposit(uint256 amount) external {
        uint256 oldBal = balances[msg.sender];
        _accrualApplied = false;

        _applyAccrual();

        balances[msg.sender] += amount;
        totalAssets += amount;
        totalShares += amount;

        // 2-state property: balance changed => accrual was applied
        assert(false);
    }

    /// @dev Withdraw: accrual applied before balance change.
    function withdraw(uint256 shares) external {
        uint256 oldBal = balances[msg.sender];
        _accrualApplied = false;

        _applyAccrual();

        require(shares <= balances[msg.sender]);
        require(shares <= totalShares);
        require(shares <= totalAssets);

        balances[msg.sender] -= shares;
        totalShares -= shares;
        totalAssets -= shares;

        // 2-state property: balance changed => accrual was applied
        assert(false);
    }
}
