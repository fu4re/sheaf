// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// BUGGY ghost harness — the frozen axiom is deliberately too weak: it allows
/// `mintedShares <= assets + 1`, modelling a vault that over-mints one share
/// (dilution). The solvency invariant `totalShares <= totalAssets` must then be
/// REFUTED with a counterexample — proving the ghost abstraction does not make
/// the proof vacuous (a wrong axiom still gets caught).
contract ProportionalVaultGhostBuggy {
    uint256 public totalAssets;
    uint256 public totalShares;

    function deposit(uint256 assets, uint256 mintedShares) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(totalShares <= type(uint128).max, "shares cap");

        if (totalShares == 0) {
            require(mintedShares == assets, "axiom: bootstrap 1:1");
        } else {
            require(mintedShares <= assets + 1, "BUGGY axiom: over-mints one share");
        }

        totalAssets += assets;
        totalShares += mintedShares;

        assert(totalShares <= totalAssets); // solvency — must be violated
    }
}
