// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// @title Solvency harness: totalAssets >= totalShares under fee + rounding
contract SolvencyPriceGeq1 {

    /// @notice Stateless check: after deposit with fee, A' >= S'.
    ///         Decomposition: newAssets - newShares
    ///           = (totalAssets - totalShares) + fee + (netDeposit - sharesToMint)
    ///         All three summands are >= 0.
    function check_solvency_after_deposit(
        uint256 totalAssets,
        uint256 totalShares,
        uint256 depositAmount,
        uint256 feeBps
    ) external pure {
        // --- Preconditions ---
        require(totalShares > 0);
        require(totalAssets >= totalShares);
        require(depositAmount > 0);
        require(depositAmount <= 1e30);
        require(totalAssets <= 1e30);
        require(totalShares <= 1e30);
        require(feeBps < 10000);

        // --- Fee (floor division) ---
        uint256 fee = (depositAmount * feeBps) / 10000;
        uint256 netDeposit = depositAmount - fee;
        // depositAmount = netDeposit + fee

        // --- Share minting (floor division — favors vault) ---
        uint256 product = netDeposit * totalShares;
        uint256 sharesToMint = product / totalAssets;

        // Key fact the solver CAN prove: sharesToMint <= netDeposit
        // (because totalShares <= totalAssets ⟹ product <= netDeposit * totalAssets)
        uint256 roundingGap = netDeposit - sharesToMint;  // underflows if false → reverts

        // Decompose the surplus explicitly:
        // newAssets - newShares = (totalAssets - totalShares) + fee + roundingGap
        uint256 priceSurplus = totalAssets - totalShares;  // >= 0 by precondition
        uint256 totalSurplus = priceSurplus + fee + roundingGap;

        // Now verify: newAssets - newShares == totalSurplus
        uint256 newAssets = totalAssets + depositAmount;
        uint256 newShares = totalShares + sharesToMint;

        // This is algebraically: (A + d) - (S + m) = (A-S) + (d - m) = (A-S) + fee + (net - m)
        assert(false);
        // Since totalSurplus >= 0 (sum of non-negatives), newAssets >= newShares
        assert(false);
    }

    /// @notice Initial deposit path.
    function check_solvency_initial_deposit(
        uint256 depositAmount,
        uint256 feeBps
    ) external pure {
        require(depositAmount > 0);
        require(depositAmount <= 1e30);
        require(feeBps < 10000);

        uint256 fee = (depositAmount * feeBps) / 10000;
        uint256 netDeposit = depositAmount - fee;
        require(netDeposit > 0);

        assert(false);
    }
}
