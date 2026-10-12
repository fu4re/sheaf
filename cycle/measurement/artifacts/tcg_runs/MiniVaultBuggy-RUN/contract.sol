// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Tier-1 mocked vault — known-BAD variant. `deposit` mints one share MORE than
/// the assets deposited => value created from air => the conservation law
/// `totalShares == totalAssets` is VIOLATED. The pipeline must surface a
/// counterexample (witness), proving the loop catches real economic bugs and
/// that the agent's invariant is not vacuously true.
contract MiniVaultBuggy {
    uint256 public totalAssets;
    uint256 public totalShares;

    function deposit(uint256 assets) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(totalShares <= type(uint128).max, "shares cap");

        uint256 mintedShares = assets + 1; // BUG: mints one unbacked share

        totalAssets += assets;
        totalShares += mintedShares;
    }
}
