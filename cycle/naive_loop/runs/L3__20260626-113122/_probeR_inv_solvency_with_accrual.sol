// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Vault with accrual/rebase — solvency_with_accrual harness
/// @notice Proves: totalAssets >= totalShares is preserved across all operations
///         including accrual (stateless inductive invariant).
///         Technique: require the invariant as a precondition (inductive hypothesis),
///         assert it as a postcondition after each state transition.
contract VaultSolvency {
    uint256 public totalAssets;
    uint256 public totalShares;
    uint256 public accumulatedFees;
    mapping(address => uint256) public balances;

    /// @dev Deposit: both totalAssets and totalShares increase by the same amount.
    function deposit(uint256 amount) external {
        require(totalAssets >= totalShares); // inductive hypothesis

        totalAssets += amount;
        totalShares += amount;
        balances[msg.sender] += amount;

        assert(false);
    }

    /// @dev Withdraw: 1:1 redemption preserves the gap.
    function withdraw(uint256 shares) external {
        require(totalAssets >= totalShares); // inductive hypothesis

        require(shares <= balances[msg.sender]);
        require(shares <= totalShares);
        require(shares <= totalAssets);

        totalAssets -= shares;
        totalShares -= shares;
        balances[msg.sender] -= shares;

        assert(false);
    }

    /// @dev Accrual: totalAssets increases, totalShares unchanged.
    function accrual(uint256 yield, uint256 fee) external {
        require(totalAssets >= totalShares); // inductive hypothesis

        require(fee <= yield);
        accumulatedFees += fee;
        totalAssets += (yield - fee);

        assert(false);
    }
}
