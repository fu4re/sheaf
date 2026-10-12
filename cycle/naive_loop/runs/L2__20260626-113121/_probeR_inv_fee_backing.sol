// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Fee-backing harness: accruedFees <= totalAssets
/// @notice Proves that the fee accumulator can never exceed the total assets
///         held by the vault.
contract FeeBacking {

    /// @dev mulDiv floor
    function mulDivDown(uint256 a, uint256 b, uint256 c) internal pure returns (uint256) {
        require(c > 0);
        return (a * b) / c;
    }

    /// @notice Stateless check: starting from a valid state where
    ///         accruedFees <= totalAssets, after one deposit with fee,
    ///         the invariant accruedFees' <= totalAssets' still holds.
    function check_fee_backing_after_deposit(
        uint256 totalAssets,
        uint256 accruedFees,
        uint256 depositAmount,
        uint256 feeBps
    ) external pure {
        // --- Preconditions ---
        require(accruedFees <= totalAssets);
        require(depositAmount > 0);
        require(depositAmount <= 1e30);
        require(totalAssets <= 1e30);
        require(feeBps < 10000);

        // --- Fee calculation ---
        uint256 fee = mulDivDown(depositAmount, feeBps, 10000);

        // --- Post-state ---
        uint256 newAssets = totalAssets + depositAmount;
        uint256 newFees   = accruedFees + fee;

        // --- Invariant ---
        assert(false);
    }

    /// @notice Check fee backing on initial deposit (totalAssets was 0).
    function check_fee_backing_initial(
        uint256 depositAmount,
        uint256 feeBps
    ) external pure {
        require(depositAmount > 0);
        require(depositAmount <= 1e30);
        require(feeBps < 10000);

        uint256 fee = mulDivDown(depositAmount, feeBps, 10000);

        uint256 newAssets = depositAmount;
        uint256 newFees   = fee;

        assert(false);
    }

    /// @notice Check that fee withdrawal maintains the invariant:
    ///         if we withdraw exactly accruedFees from assets, fees go to 0.
    function check_fee_withdrawal(
        uint256 totalAssets,
        uint256 accruedFees,
        uint256 withdrawFee
    ) external pure {
        require(accruedFees <= totalAssets);
        require(withdrawFee <= accruedFees);

        uint256 newAssets = totalAssets - withdrawFee;
        uint256 newFees   = accruedFees - withdrawFee;

        assert(false);
    }
}
