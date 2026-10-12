// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

/// Non-vacuity sibling of VaultAssetAG.sol: the summary is TOO WEAK. Instead of
/// pinning the credit to exactly `+assets`, it only assumes `vaultBal_post >= vaultBal`
/// (the balance did not decrease). The solver is then free to pick vaultBal_post ==
/// vaultBal (no credit at all) while totalAssets still grows by `assets` — so
/// solvency `vaultBal >= totalAssets` is REFUTED with a counterexample. Demonstrates
/// that a too-weak G_B does not vacuously prove I_A (ghost.md: too-weak axiom fails
/// to prove — the safe direction), and motivates why the mined interface must be
/// tight enough.
contract VaultAssetAGBuggy {
    uint256 public totalAssets;
    uint256 public vaultBal;

    function deposit(uint256 assets, uint256 vaultBal_post) public {
        require(assets    <= type(uint128).max, "assets too large");
        require(totalAssets <= type(uint128).max, "assets cap");
        require(vaultBal  <= type(uint128).max, "bal cap");

        require(vaultBal_post >= vaultBal); // __SUMMARY__ TOO WEAK (does not pin +assets)
        vaultBal = vaultBal_post;

        totalAssets += assets;

        assert(vaultBal >= totalAssets); // __INVARIANT__
    }
}
