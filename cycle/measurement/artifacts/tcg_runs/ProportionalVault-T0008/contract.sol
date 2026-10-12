// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Tier-1.5 SUT — proportional vault with REAL nonlinear share arithmetic.
/// `deposit` mints shares = floor(assets * totalShares / totalAssets) — the
/// product of two state variables is NONLINEAR, the wall the SMT solver chokes
/// on. This is the bridge toward Tier-2 (Aave rayMul/rayDiv).
///
/// Economic invariant of interest (solvency / no dilution): every share stays
/// backed by >= 1 asset unit, i.e. `totalShares <= totalAssets` (share price >= 1).
contract ProportionalVault {
    uint256 public totalAssets;
    uint256 public totalShares;

    function deposit(uint256 assets) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(totalShares <= type(uint128).max, "shares cap");

        uint256 mintedShares;
        if (totalShares == 0) {
            mintedShares = assets; // bootstrap 1:1
        } else {
            require(totalAssets > 0, "no assets to price against");
            mintedShares = assets * totalShares / totalAssets; // NONLINEAR
        }

        totalAssets += assets;
        totalShares += mintedShares;
    }
}
