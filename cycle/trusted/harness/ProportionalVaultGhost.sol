// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// PRE-FIXED ghost harness for ProportionalVault (TRUSTED, hand-written).
///
/// The nonlinear `floor(assets * totalShares / totalAssets)` is abstracted: the
/// share amount becomes a GHOST result `mintedShares` — a havoc'd function input
/// (SMTChecker explores all values) pinned ONLY by frozen axioms expressed as
/// `require` (assume). We then prove the economic invariant RELATIVE to those
/// axioms, never touching the intractable product. This is "rely on an
/// already-proven fact from another level of mathematics".
///
/// Frozen axiom (offline-justified, see ghost.md):
///   when solvency holds (totalShares <= totalAssets, i.e. price >= 1),
///   floor(assets * totalShares / totalAssets) <= assets.
/// So the round-down result is bounded ABOVE by `assets` — a LINEAR fact the
/// solver can use directly.
contract ProportionalVaultGhost {
    uint256 public totalAssets;
    uint256 public totalShares;

    /// `mintedShares` is the ghost result (havoc'd input) standing in for
    /// floor(assets * totalShares / totalAssets).
    function deposit(uint256 assets, uint256 mintedShares) public {
        require(assets <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(totalShares <= type(uint128).max, "shares cap");

        if (totalShares == 0) {
            require(mintedShares == assets, "axiom: bootstrap 1:1"); // exact, linear
        } else {
            require(mintedShares <= assets, "axiom: round-down under price>=1"); // FROZEN AXIOM
        }

        totalAssets += assets;
        totalShares += mintedShares;

        assert(totalShares <= totalAssets); // __INVARIANT__ (gateway overwrites the expr)
    }
}
