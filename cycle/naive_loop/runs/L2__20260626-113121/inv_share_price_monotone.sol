// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Share-price monotone harness: no dilution via rounding
/// @notice Proves that shares minted per deposit never exceed the proportional
///         share — i.e., floor-division rounding ensures no dilution.
///         Formally: sharesToMint / netDeposit <= totalShares / totalAssets
///         which is equivalent to: sharesToMint * totalAssets <= netDeposit * totalShares
contract SharePriceMonotone {

    /// @dev mulDiv floor
    function mulDivDown(uint256 a, uint256 b, uint256 c) internal pure returns (uint256) {
        require(c > 0);
        return (a * b) / c;
    }

    /// @notice Stateless check: the shares minted for a deposit are at most
    ///         the proportional entitlement (no dilution via rounding).
    ///         sharesToMint = floor(netDeposit * totalShares / totalAssets)
    ///         ⟹  sharesToMint * totalAssets <= netDeposit * totalShares
    function check_no_dilution(
        uint256 totalAssets,
        uint256 totalShares,
        uint256 depositAmount,
        uint256 feeBps
    ) external pure {
        // --- Preconditions ---
        require(totalShares > 0);
        require(totalAssets >= totalShares);
        require(totalAssets > 0);

        require(depositAmount > 0);
        require(depositAmount <= 1e30);
        require(totalAssets <= 1e30);
        require(totalShares <= 1e30);

        require(feeBps < 10000);

        // --- Fee & net deposit ---
        uint256 fee = mulDivDown(depositAmount, feeBps, 10000);
        uint256 netDeposit = depositAmount - fee;

        // --- Shares minted (floor division) ---
        uint256 sharesToMint = mulDivDown(netDeposit, totalShares, totalAssets);

        // --- No-dilution invariant ---
        // sharesToMint = floor(netDeposit * totalShares / totalAssets)
        // By definition of floor division: floor(x/y) * y <= x
        // So: sharesToMint * totalAssets <= netDeposit * totalShares
        assert(sharesToMint * totalAssets <= netDeposit * totalShares);
    }
}
